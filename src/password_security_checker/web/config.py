"""Configuración pequeña, validada al arrancar y sin secretos."""

from collections.abc import Mapping
from dataclasses import dataclass
from ipaddress import ip_address, ip_network
import math
import os
import re
from urllib.parse import urlsplit


def _number(env, name, default, minimum, maximum, cast=int):
    try:
        value = cast(env.get(name, str(default)))
    except (TypeError, ValueError):
        raise ValueError(f"{name} debe ser un número válido.") from None
    if not math.isfinite(value) or not minimum <= value <= maximum:
        raise ValueError(f"{name} está fuera del intervalo permitido.")
    return value


@dataclass(frozen=True)
class Settings:
    environment: str
    bind_host: str
    port: int
    allowed_hosts: tuple[str, ...]
    public_origin: str | None
    trusted_proxy_ips: tuple[str, ...]
    max_concurrency: int
    body_timeout_seconds: float
    deployment_target: str = "generic"

    @property
    def render_free(self) -> bool:
        return self.deployment_target == "render-free"

    @property
    def production(self) -> bool:
        return self.environment == "production"

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Settings":
        env = os.environ if env is None else env
        environment = env.get("APP_ENV", "development")
        if environment not in {"development", "production"}:
            raise ValueError("APP_ENV debe ser development o production.")
        production = environment == "production"
        target = env.get("DEPLOYMENT_TARGET", "generic")
        if target not in {"generic", "render-free"}:
            raise ValueError("DEPLOYMENT_TARGET debe ser generic o render-free.")
        render_free = target == "render-free"
        render_host = ""
        render_origin = ""
        if render_free:
            # Opt-in a la frontera de red de Render Free, no a sus headers.
            # RENDER no es una prueba criptográfica ni indica el plan contratado.
            if not production or env.get("RENDER") != "true" or env.get("RENDER_SERVICE_TYPE") != "web":
                raise ValueError("render-free requiere production y un Web Service de Render.")
            render_host = env.get("RENDER_EXTERNAL_HOSTNAME", "")
            render_origin = env.get("RENDER_EXTERNAL_URL", "")
            if (
                not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.onrender\.com", render_host)
                or render_origin != f"https://{render_host}"
            ):
                raise ValueError("Render debe proporcionar hostname y URL HTTPS coherentes.")
            if "PORT" not in env:
                raise ValueError("Render debe proporcionar PORT.")
        bind_host = env.get("BIND_HOST", "0.0.0.0" if production else "127.0.0.1")
        try:
            address = ip_address(bind_host)
        except ValueError:
            raise ValueError("BIND_HOST debe ser una dirección IP válida.") from None
        if not production and not address.is_loopback:
            raise ValueError("En development, BIND_HOST debe ser loopback.")
        if render_free and bind_host != "0.0.0.0":
            raise ValueError("En render-free, BIND_HOST debe ser 0.0.0.0.")

        raw_hosts = env.get("ALLOWED_HOSTS", render_host if render_free else ("" if production else "127.0.0.1,localhost"))
        hosts = tuple(host.strip().lower() for host in raw_hosts.split(","))
        label = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?")
        if not all(host and len(host) <= 253 and
                   all(label.fullmatch(part) for part in host.split(".")) for host in hosts):
            raise ValueError("ALLOWED_HOSTS requiere nombres DNS o IPv4 explícitos, sin puertos ni comodines.")
        if render_free and render_host not in hosts:
            raise ValueError("ALLOWED_HOSTS debe incluir RENDER_EXTERNAL_HOSTNAME para el health check.")

        origin = env.get("PUBLIC_ORIGIN", render_origin).strip() or None
        if production and not origin:
            raise ValueError("PUBLIC_ORIGIN es obligatorio en production.")
        if origin:
            try:
                parsed = urlsplit(origin)
                valid = (
                    parsed.scheme == "https" and parsed.hostname in hosts
                    and not parsed.username and not parsed.password
                    and parsed.path in {"", "/"} and not parsed.query and not parsed.fragment
                )
                port = parsed.port
                valid = valid and (port is None or 1 <= port <= 65535)
            except ValueError:
                valid = False
            if not valid:
                raise ValueError("PUBLIC_ORIGIN debe ser un origen HTTPS de ALLOWED_HOSTS, sin ruta ni credenciales.")
            origin = f"https://{parsed.hostname}" + (f":{port}" if port and port != 443 else "")

        raw_proxies = env.get("TRUSTED_PROXY_IPS", "").strip()
        if render_free and raw_proxies:
            raise ValueError("render-free no usa TRUSTED_PROXY_IPS; elimina esa variable.")
        proxies = []
        if raw_proxies:
            for item in raw_proxies.split(","):
                try:
                    network = ip_network(item.strip(), strict=False)
                except ValueError:
                    raise ValueError("TRUSTED_PROXY_IPS solo admite IP o CIDR explícitos.") from None
                if network.prefixlen == 0:
                    raise ValueError("TRUSTED_PROXY_IPS no permite confiar en toda la red.")
                proxies.append(str(network))
        if production and not render_free and not proxies:
            raise ValueError("TRUSTED_PROXY_IPS es obligatorio detrás del proxy HTTPS.")

        return cls(
            environment=environment,
            bind_host=bind_host,
            port=_number(env, "PORT", 8000, 1, 65535),
            allowed_hosts=hosts,
            public_origin=origin,
            trusted_proxy_ips=tuple(proxies),
            max_concurrency=_number(env, "MAX_CONCURRENCY", 64, 2, 1024),
            body_timeout_seconds=_number(env, "BODY_TIMEOUT_SECONDS", 5, 0.1, 30, float),
            deployment_target=target,
        )
