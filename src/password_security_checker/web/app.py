"""Aplicación web sin persistencia ni registro de entradas."""

import asyncio
from dataclasses import asdict
import json
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException
from starlette.middleware.trustedhost import TrustedHostMiddleware

from ..analyzer import analyze_password
from ..recommendations import generate_recommendations
from .config import Settings


STATIC_DIRECTORY = Path(__file__).parent / "static"
MAX_PASSWORD_LENGTH = 1024
MAX_BODY_BYTES = 16 * 1024

def error_response(status: int, message: str) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status)


async def private_responses(request: Request, call_next):
    settings = request.app.state.settings
    # Render Free: HTTPS externo es una propiedad del ingreso de la plataforma;
    # el tramo interno es HTTP. No inferir esquema, host o IP de headers enviados.
    # Este modo NO es válido donde clientes puedan alcanzar directamente el puerto.
    external_https = settings.render_free or request.url.scheme == "https"
    try:
        if request.url.query:
            response = error_response(400, "No se admiten parámetros en la URL.")
        elif settings.production and not external_https and request.url.path != "/healthz":
            # No se redirige un POST sensible ni se refleja la URL recibida.
            response = error_response(400, "Esta aplicación requiere una conexión HTTPS.")
        else:
            response = await call_next(request)
    except Exception:
        # No se propagan excepciones al servidor: podrían incluir la entrada.
        response = error_response(500, "No se pudo completar el análisis. Inténtalo de nuevo.")
    response.headers.update({
        "Cache-Control": "no-store",
        "Pragma": "no-cache",
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer",
        "X-Frame-Options": "DENY",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
        "Content-Security-Policy": (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self'; connect-src 'self'; font-src 'self'; "
            "object-src 'none'; base-uri 'none'; frame-ancestors 'none'; "
            "form-action 'none'"
        ),
    })
    if settings.production and external_https:
        response.headers["Strict-Transport-Security"] = "max-age=86400"
    return response


async def http_error(request: Request, exception: HTTPException):
    messages = {404: "Recurso no encontrado.", 405: "Método no permitido."}
    return error_response(
        exception.status_code, messages.get(exception.status_code, "Solicitud no válida.")
    )


async def index():
    return FileResponse(STATIC_DIRECTORY / "index.html")


async def health():
    return JSONResponse({"status": "ok"})


async def analyze(request: Request):
    settings = request.app.state.settings
    origin = request.headers.get("origin")
    expected_origin = settings.public_origin or str(request.base_url).rstrip("/")
    if (
        origin is not None and origin != expected_origin
    ) or request.headers.get("sec-fetch-site") == "cross-site":
        return error_response(403, "La solicitud debe proceder de esta aplicación.")
    if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() != "application/json":
        return error_response(415, "Se requiere contenido JSON.")
    if request.headers.get("content-encoding", "identity").lower() != "identity":
        return error_response(415, "No se admite contenido comprimido.")
    declared_length = request.headers.get("content-length")
    if declared_length is not None:
        if not declared_length.isascii() or not declared_length.isdecimal() or len(declared_length) > 10:
            return error_response(400, "Longitud de solicitud no válida.")
        if int(declared_length) > MAX_BODY_BYTES:
            return error_response(413, "La solicitud supera el tamaño permitido.")

    body = bytearray()
    payload = None
    password = None
    try:
        # Lectura acotada sin Request.json(): evita su caché y los errores
        # de validación automáticos que pueden devolver datos de entrada.
        try:
            async with asyncio.timeout(settings.body_timeout_seconds):
                async for chunk in request.stream():
                    if len(body) + len(chunk) > MAX_BODY_BYTES:
                        return error_response(413, "La solicitud supera el tamaño permitido.")
                    body.extend(chunk)
        except TimeoutError:
            return error_response(408, "Se agotó el tiempo para recibir la solicitud.")
        try:
            payload = json.loads(body)
        except (ValueError, UnicodeError, RecursionError):
            return error_response(400, "El contenido JSON no es válido.")

        if not isinstance(payload, dict) or set(payload) != {"password"}:
            return error_response(422, "Envía únicamente el campo password como texto.")
        password = payload.pop("password")
        if not isinstance(password, str):
            return error_response(422, "La contraseña debe ser texto.")
        if not password:
            return error_response(422, "Introduce una contraseña para analizarla.")
        if len(password) > MAX_PASSWORD_LENGTH:
            return error_response(422, "La contraseña no puede superar 1024 puntos de código.")

        result = analyze_password(password)
        password = None
        return JSONResponse({
            "analysis": asdict(result),
            "recommendations": list(generate_recommendations(result)),
        })
    finally:
        # Se liberan referencias; Python y el navegador no garantizan borrado seguro.
        body.clear()
        if isinstance(payload, dict):
            payload.clear()
        password = None


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    application = FastAPI(
        title="Password Security Checker", debug=False, redirect_slashes=False,
        docs_url=None, redoc_url=None, openapi_url=None,
    )
    application.state.settings = settings
    application.add_middleware(
        TrustedHostMiddleware, allowed_hosts=list(settings.allowed_hosts), www_redirect=False
    )
    application.middleware("http")(private_responses)
    application.add_exception_handler(HTTPException, http_error)
    application.add_api_route("/", index, methods=["GET"], include_in_schema=False)
    application.add_api_route("/healthz", health, methods=["GET", "HEAD"], include_in_schema=False)
    application.add_api_route("/api/analyze", analyze, methods=["POST"])
    application.mount("/static", StaticFiles(directory=STATIC_DIRECTORY), name="static")
    return application


app = create_app()
