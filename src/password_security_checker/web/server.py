"""Punto de arranque común para desarrollo y producción, sin CLI de análisis."""

import sys

import uvicorn

from .config import Settings


def main() -> None:
    try:
        settings = Settings.from_env()
    except ValueError as error:
        print(f"Configuración no válida: {error}", file=sys.stderr)
        raise SystemExit(1) from None

    uvicorn.run(
        "password_security_checker.web.app:create_app",
        factory=True,
        host=settings.bind_host,
        port=settings.port,
        proxy_headers=bool(settings.trusted_proxy_ips),
        forwarded_allow_ips=",".join(settings.trusted_proxy_ips),
        access_log=False,
        log_level="warning",
        server_header=False,
        reload=False,
        workers=1,
        ws="none",
        limit_concurrency=settings.max_concurrency,
        timeout_keep_alive=5,
        timeout_graceful_shutdown=10,
        h11_max_incomplete_event_size=16 * 1024,
    )


if __name__ == "__main__":
    main()
