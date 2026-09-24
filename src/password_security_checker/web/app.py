"""Aplicación web local sin persistencia ni registro de entradas."""

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


STATIC_DIRECTORY = Path(__file__).parent / "static"
MAX_PASSWORD_LENGTH = 1024
MAX_BODY_BYTES = 16 * 1024

app = FastAPI(
    title="Password Security Checker",
    debug=False,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.add_middleware(
    TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"], www_redirect=False
)


def error_response(status: int, message: str) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status)


@app.middleware("http")
async def private_responses(request: Request, call_next):
    try:
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
    return response


@app.exception_handler(HTTPException)
async def http_error(request: Request, exception: HTTPException):
    messages = {404: "Recurso no encontrado.", 405: "Método no permitido."}
    return error_response(
        exception.status_code, messages.get(exception.status_code, "Solicitud no válida.")
    )


@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(STATIC_DIRECTORY / "index.html")


@app.post("/api/analyze")
async def analyze(request: Request):
    origin = request.headers.get("origin")
    if (
        origin is not None and origin != str(request.base_url).rstrip("/")
    ) or request.headers.get("sec-fetch-site") == "cross-site":
        return error_response(403, "La solicitud debe proceder de esta aplicación.")
    if request.url.query:
        return error_response(400, "Envía los datos únicamente en el cuerpo JSON.")
    if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() != "application/json":
        return error_response(415, "Se requiere contenido JSON.")

    body = bytearray()
    payload = None
    password = None
    try:
        # Lectura acotada sin Request.json(): evita su caché y los errores
        # de validación automáticos que pueden devolver datos de entrada.
        async for chunk in request.stream():
            if len(body) + len(chunk) > MAX_BODY_BYTES:
                return error_response(413, "La solicitud supera el tamaño permitido.")
            body.extend(chunk)
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


app.mount("/static", StaticFiles(directory=STATIC_DIRECTORY), name="static")
