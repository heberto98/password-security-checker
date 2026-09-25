# Password Security Checker

Live Demo: [https://password-security-checker-01d5.onrender.com](https://password-security-checker-01d5.onrender.com)

Aplicación web educativa en Python para explorar la fortaleza de una contraseña.
Presenta una puntuación de 0 a 100, su nivel orientativo, composición, patrones
detectados y recomendaciones, reutilizando un núcleo de análisis independiente.

**Es una heurística educativa, no una medición absoluta de resistencia a ataques.**
Una puntuación alta no garantiza seguridad ni indica ausencia de filtraciones.

## Características

- Interfaz en español, adaptable a escritorio y móvil, con HTML, CSS y JavaScript vanilla.
- Campo oculto con opción mostrar/ocultar, análisis sin recarga y botón para limpiar.
- Estados de entrada vacía, carga, éxito, error del servidor y error de conexión.
- Puntuación visual con descripción textual, longitud, diversidad y observaciones.
- Navegación por teclado, etiquetas, avisos accesibles y respeto a movimiento reducido.
- Procesamiento local al ejecutar el servidor en tu equipo; sin cuentas ni historial.
- Sin bases de datos, analíticas, fuentes remotas, trackers ni servicios de terceros.

## Requisitos e instalación

Necesitas **Python 3.12 o superior** y Git para clonar el repositorio. No necesitas
Node, npm ni herramientas de compilación frontend. La instalación inicial descarga
las dependencias; después, la aplicación no necesita acceso a Internet.

Desde PowerShell en Windows:

```powershell
git clone https://github.com/heberto98/password-security-checker.git
cd password-security-checker
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-test.lock
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
```

Si ya tienes el proyecto, comienza dentro de su carpeta y omite los dos primeros
comandos. Se usa el ejecutable del entorno directamente, sin cambiar la política
de ejecución de PowerShell ni activar scripts. Para instalar solo la aplicación,
usa `requirements.lock` en lugar de `requirements-test.lock`.

En macOS o Linux, los comandos equivalentes son:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-test.lock
.venv/bin/python -m pip install --no-deps -e .
```

## Ejecutar la web localmente

Desde la carpeta del proyecto, en PowerShell:

```powershell
.\.venv\Scripts\python.exe -B -m password_security_checker.web.server
```

En macOS o Linux:

```sh
.venv/bin/python -B -m password_security_checker.web.server
```

Abre **http://127.0.0.1:8000** en el navegador. Detén el servidor con `Ctrl+C`.
Si el puerto está ocupado, define `$env:PORT="8001"` antes de arrancar y abre la dirección correspondiente.
No abras el HTML directamente: necesita el backend Python. JavaScript debe estar
habilitado; sin él, el formulario permanece desactivado y no envía entradas.

Usa ejemplos ficticios para explorar la herramienta. Al pulsar **Analizar
contraseña**, el campo se vacía y el resultado aparece en la misma página.
**Limpiar** borra el resultado y cancela la espera de un análisis en curso.
Puedes introducir otra entrada para empezar de nuevo.

El servidor escucha únicamente en loopback y acepta los hosts `127.0.0.1` y
`localhost`. El modo predeterminado es development. Producción se configura más abajo.

## Arquitectura y tecnologías

```text
Navegador (HTML / CSS / JavaScript)
    ↓ POST /api/analyze, en el mismo origen
FastAPI (validación HTTP, límites y errores genéricos)
    ↓
analyze_password() → AnalysisResult → generate_recommendations()
    ↓
JSON con resultados y consejos, sin la contraseña
```

El frontend presenta resultados; no duplica las reglas ni calcula la puntuación.
El núcleo sigue usando exclusivamente la biblioteca estándar. La web añade:

| Dependencia directa | Uso |
| --- | --- |
| FastAPI `>=0.141.1,<0.142` | Rutas HTTP, middleware y servicio de archivos estáticos |
| Uvicorn `>=0.53,<0.54` | Servidor ASGI |
| HTTPX2 `>=2.13.1,<3` (extra `test`) | Cliente utilizado por el TestClient actual de Starlette |
| setuptools `==84.0.0` (construcción) | Instalación del paquete y empaquetado del frontend |

FastAPI incorpora sus dependencias transitivas, como Starlette y Pydantic.
No se utilizan plantillas de servidor, frameworks frontend ni CDN.

## API

`POST /api/analyze` acepta `Content-Type: application/json` y un objeto con un
único campo: `password`, una cadena de entre 1 y 1024 puntos de código Unicode.
No recorta espacios ni normaliza la entrada. El mínimo educativo es 12 y no se
configura desde la web. El cuerpo HTTP no puede superar 16 KiB, incluso cuando
se envía por fragmentos. El límite pertenece a la capa web, no cambia el núcleo.

La respuesta contiene únicamente:

- `analysis`: `length`, `minimum_length`, `meets_minimum`, `diversity`,
  `has_repetition`, `has_sequence`, `score` y `level`.
- `recommendations`: lista de mensajes del módulo existente.

Los errores devuelven `{"error": "mensaje genérico"}`: JSON mal formado o
parámetros en URL (400), origen ajeno (403), solicitud demasiado grande (413),
contenido no JSON (415), entrada inválida (422) o error interno (500).
No se incluyen el cuerpo recibido, valores inválidos ni trazas de excepciones.
No hay endpoint GET de análisis ni documentación interactiva donde introducir
contraseñas accidentalmente. Las rutas y métodos inexistentes devuelven 404/405.

## Reglas y puntuación

La puntuación conserva la heurística original:

1. Cinco puntos por punto de código, hasta un máximo inicial de 100.
2. Se restan 25 puntos por repetición y 25 por secuencia, una vez por tipo.
3. Con alguno de esos patrones, el máximo es 69.
4. Bajo el mínimo configurado, el máximo es 39.
5. Nunca baja de cero: **baja 0–39**, **media 40–69**, **alta 70–100**.

La diversidad informa de minúsculas, mayúsculas, dígitos decimales y símbolos
Unicode; no añade puntos ni obliga a mezclar tipos. Los símbolos incluyen
puntuación y emojis, pero no espacios, controles ni marcas combinantes. Los
números no decimales, como `²` y `½`, no cuentan como dígitos.

Las repeticiones son tres o más puntos de código idénticos consecutivos,
distinguiendo mayúsculas: `aaa` se detecta, `aAa` no. Las secuencias son tres
o más letras ASCII `a-z` o dígitos `0-9` en ambos sentidos, sin distinguir
mayúsculas: `abc`, `CbA`, `123`, `321`. No se unen extremos como `890` o `zab`.

La longitud usa `len()`: incluye espacios y cuenta puntos de código, que no
siempre coinciden con caracteres visuales. Los mínimos y umbrales son decisiones
educativas, no requisitos de un estándar. Las recomendaciones atienden longitud
y patrones, sugieren ampliar a 16 cuando corresponde y añaden consejos generales.

## Privacidad y seguridad

- La contraseña **sí se transmite del navegador al backend Python** en el cuerpo
  de una solicitud POST. Con el comando local indicado, ambos están en tu equipo.
  No es un análisis ejecutado íntegramente en JavaScript.
- La aplicación no escribe contraseñas en archivos, bases de datos ni logs y no
  las devuelve en resultados, mensajes de error ni recomendaciones.
- No usa cookies, localStorage, sessionStorage, IndexedDB, service workers ni
  historial propio. El campo se vacía al enviar, al limpiar y al salir de la página.
- Solo guarda referencias temporales en memoria para procesar la solicitud.
  Python, el navegador, extensiones y el sistema operativo pueden mantener copias:
  **no se garantiza el borrado seguro o inmediato de la memoria**. La aplicación
  tampoco puede controlar los administradores de contraseñas del navegador.
- Respuestas y archivos estáticos llevan `Cache-Control: no-store`. La política
  de contenido restringe scripts, estilos y conexiones al mismo origen y bloquea
  incrustación en marcos y envío nativo de formularios.
- Se restringen hosts y orígenes; no se habilita CORS. Las solicitudes ajenas se
  rechazan. Los límites de entrada acotan el trabajo del analizador.
- La validación HTTP es explícita para evitar que los errores automáticos de
  validación reflejen entradas. Los errores internos se convierten en mensajes
  genéricos sin registrar trazas que puedan contenerlas.
- El arranque desactiva access logs y, en desarrollo, no confía en proxies.
  No actives modo trace, registradores de cuerpos o depuradores con datos reales.
  No pongas contraseñas reales en URLs, comandos, scripts ni capturas de pantalla.

Al publicarse, la contraseña viajará al servidor mediante HTTPS y se procesará temporalmente. La aplicación no está diseñada para almacenarla. La infraestructura también requiere configuración de privacidad; no basta con cambiar la dirección de escucha.

## Limitaciones conocidas

No consulta filtraciones, contraseñas comunes, datos personales ni reutilización.
Tampoco detecta bloques repetidos, frases conocidas o patrones de teclado como
`qwerty`. Por ejemplo, **`xQ7!xQ7!xQ7!xQ7!xQ7!` obtiene 100** pese a ser un patrón
predecible, porque la detección de bloques repetidos no está implementada.

Un nivel alto solo refleja estas reglas limitadas. No se estima entropía real,
probabilidad de adivinación ni tiempo de descifrado. No uses esta puntuación como
certificación de seguridad o criterio único para aceptar contraseñas reales.

## Pruebas

Con el extra `test` instalado, desde la raíz del proyecto:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m pip check
```

En macOS o Linux sustituye el ejecutable por `.venv/bin/python`. No hace falta
configurar `PYTHONPATH`: la instalación editable permite importar el paquete.

Las pruebas usan exclusivamente datos ficticios. Cubren las reglas originales,
el analizador, recomendaciones, carga de la web, contrato HTTP, equivalencia
con el núcleo, entradas inválidas, errores internos, límites, orígenes, cabeceras
y ausencia de la entrada en respuestas y registros capturados. Los errores del
núcleo se simulan para comprobar que sus detalles no se filtran al cliente.

Para una revisión manual del navegador:

1. Envía una entrada vacía y verifica el aviso accesible.
2. Prueba mostrar/ocultar y analiza `aaa123xQ7!`: puntuación 0, nivel bajo,
   longitud insuficiente, repetición y secuencia; el campo queda vacío.
3. Analiza otra entrada y comprueba que se reemplazan los resultados.
4. Usa Limpiar y prueba a 390 y 320 píxeles de ancho, sin desplazamiento horizontal.
5. Detén el servidor y envía otra entrada: debe aparecer un error recuperable.
6. Comprueba teclado, foco, ausencia de errores en consola en el flujo normal,
   solicitudes solo al servidor local y almacenamiento vacío del navegador.

## Estructura principal

```text
password-security-checker/
├── README.md
├── pyproject.toml
├── .gitignore
├── LICENSE
├── src/password_security_checker/
│   ├── __init__.py
│   ├── models.py
│   ├── rules.py
│   ├── analyzer.py
│   ├── recommendations.py
│   └── web/
│       ├── __init__.py
│       ├── app.py
│       └── static/
│           ├── index.html
│           ├── styles.css
│           ├── app.js
│           └── favicon.svg
└── tests/
    ├── test_rules.py
    ├── test_analyzer.py
    ├── test_recommendations.py
    └── test_web.py
```

El núcleo permanece separado de HTTP y del DOM. Los recursos estáticos se incluyen
en el paquete instalable, no dependen del directorio desde el que arranque Uvicorn.

## Referencias técnicas

- [Manejo de errores y cuerpos de validación en FastAPI](https://fastapi.tiangolo.com/tutorial/handling-errors/).
- [Middleware de Starlette](https://www.starlette.io/middleware/) y [TestClient](https://www.starlette.io/testclient/).
- [Opciones de Uvicorn](https://www.uvicorn.org/settings/).

Licencia [MIT](LICENSE).

## Producción genérica: preparación sin despliegue

No se ha publicado la aplicación. Para Render Free, seguir la sección **Deploy en Render** al final: usa una frontera de confianza específica. Esta sección describe el modo genérico con proxies explícitos. Frontend y API deben compartir origen y servirse desde `/`.

### Instalación reproducible

En un entorno virtual Python 3.12+, instalar `python -m pip install -r requirements.lock`, construir con `python -m pip wheel --no-deps --wheel-dir dist .` e instalar `python -m pip install --no-deps dist/password_security_checker-0.2.0-py3-none-any.whl`. Para desarrollo usar `requirements-test.lock` e instalación editable `python -m pip install --no-deps -e .`. Ejecutar `python -m pip check`.

El arranque común es `python -B -m password_security_checker.web.server`, usando el ejecutable del entorno virtual. Configura primero las variables de producción. Fija un worker, sin reload, debug, access logs, WebSockets ni cabecera Server; nivel warning, keep-alive de 5 s y cierre de 10 s. Los valores explícitos evitan que variables genéricas de Uvicorn relajen los controles.

### Variables de entorno

`.env.example` es una referencia y **no se carga automáticamente**. Define variables en la terminal o panel del proveedor. No se requieren secretos.

| Variable | Finalidad y valores | Predeterminado / producción |
| --- | --- | --- |
| `APP_ENV` | `development` o `production` | `development`; indicar `production` al publicar |
| `DEPLOYMENT_TARGET` | `generic` o `render-free` | `generic`; render-free requiere el contrato de ingreso documentado abajo |
| `BIND_HOST` | IP de escucha | `127.0.0.1` en desarrollo; `0.0.0.0` en producción, solo en red protegida |
| `PORT` | Puerto entero 1–65535 | `8000`; usar el asignado por el proveedor |
| `ALLOWED_HOSTS` | DNS o IPv4 separados por comas, sin URLs, puertos ni comodines | `127.0.0.1,localhost` en desarrollo; obligatorio en producción |
| `PUBLIC_ORIGIN` | Origen HTTPS canónico, host incluido arriba, sin ruta ni credenciales | Vacío en desarrollo; obligatorio en producción |
| `TRUSTED_PROXY_IPS` | IP/CIDR reales de proxies, separados por comas | Obligatorio en producción genérica; prohibido no vacío en render-free; rechaza `*` y redes `/0` |
| `MAX_CONCURRENCY` | Conexiones/tareas simultáneas por proceso, 2–1024 | `64` |
| `BODY_TIMEOUT_SECONDS` | Plazo de recepción del cuerpo, 0.1–30 segundos | `5` |

Ejemplo conceptual: `ALLOWED_HOSTS=checker.example`, `PUBLIC_ORIGIN=https://checker.example`. No son valores de un despliegue real. Obtén del proveedor sus IP/CIDR concretos; no copies redes de ejemplo. Escucha y proxies admiten IPv4/IPv6; hosts públicos, DNS/IPv4. Configuración incompleta o inválida impide arrancar sin volcar sus valores. Development solo permite loopback.

### Controles a cargo del proveedor

- HTTPS con certificado válido y renovación automática. No guardar claves en Git. Proteger el salto proxy-backend con red privada o transporte seguro apropiado; nunca transmitir contraseñas por una red intermedia no confiable.
- Conservar `Host` y sobrescribir `X-Forwarded-Proto` con el esquema real. Solo se interpretan forwarded headers de peers confiables. `X-Forwarded-Host` no reemplaza el Host. Restringir acceso al backend al proxy y probes autorizados.
- Deshabilitar registro de cuerpos, query strings y datos sensibles en proxy, CDN, WAF, APM, trazas, volcados y reportes. Evitar búferes de cuerpos en disco. La aplicación no controla estas políticas. Una entrada en una URL puede llegar a infraestructura antes de ser rechazada.
- No cachear `/api/*`, incluidos errores de infraestructura. Uvicorn puede emitir 503 antes del middleware, sin sus cabeceras. No almacenar cuerpos de solicitudes.
- Límites de frecuencia por IP y globales, tamaño/cabeceras, tiempos de conexión y lectura, y protección DDoS. Medir carga y ajustar concurrencia/instancias: concurrencia no equivale a rate limiting.
- Usuario sin privilegios, permisos mínimos, actualizaciones controladas y supervisión de salud sin capturar entradas.

Producción genérica rechaza HTTP sin redirigir POST sensibles. Solo `/healthz` permite HTTP para probes internos con Host autorizado. En render-free, HTTPS público se exige en el ingreso de Render, como se explica abajo. El formulario también se bloquea en HTTP fuera de loopback; esto no sustituye HTTPS ni protege una página HTTP manipulada.

### Decisiones adicionales

- Health: `GET/HEAD /healthz` devuelve `{"status":"ok"}`, sin versiones ni análisis; HEAD sin cuerpo. Comprueba vida, no TLS ni capacidad.
- Abuso: máximo 16 KiB, 1024 puntos de código, plazo de recepción y concurrencia acotada. Tamaño real comprobado por fragmentos y sin Content-Length; compresión rechazada. Rate limiting queda en el proveedor, sin introducir Redis.
- Errores: HTTP de producción y query strings se rechazan con 400, recepción lenta con 408 y saturación con 503. No se redirige automáticamente la API con barra final ni se reflejan entradas.
- Caché: se conserva `no-store` también en estáticos, pequeños y sin nombres versionados. No se introduce CDN.
- HSTS: un día, solo en producción con HTTPS reconocido. Sin preload ni includeSubDomains para no afectar otros servicios. HTTPS y primera conexión dependen del proveedor.
- Cabeceras: CSP del mismo origen sin `unsafe-inline`; bloqueo de framing/objetos, nosniff contra reinterpretación MIME y no-referrer para reducir fugas. Permissions-Policy deshabilita cámara, micrófono y ubicación.
- CORS/CSRF: CORS cerrado; Origin debe coincidir si existe, y se rechaza Sec-Fetch-Site cross-site. Clientes sin Origin pueden usar la API: no es autenticación ni defensa contra bots. No hay tokens CSRF porque no existen sesiones, cookies autenticadas ni cambios persistentes. Reevaluar si cambia la arquitectura.
- API mínima: docs, redoc y openapi.json siguen deshabilitados en ambos entornos. El contrato del README y los tests permiten desarrollar sin otro formulario sensible ni recursos remotos.
- Docker: evaluado, no añadido. El wheel/proceso Python ya es portable; Render usa su runtime Python nativo.

### Reproducibilidad y verificación

No se añaden, eliminan ni actualizan dependencias de ejecución. Los locks fijan las versiones directas/transitivas ya usadas y separan testing. Se fija setuptools 84.0.0, constructor verificado. No se fijan hashes: no se prometen builds idénticos entre plataformas. Se comprobó Python 3.12 en Windows; probar otro runtime/SO y revisar avisos de seguridad antes de publicar.

Evaluación inicial: 64 pruebas aprobadas, sin persistencia, pero configuración y mensajes locales, sin plazo de recepción ni configuración de producción. Se conservan las 48 pruebas del núcleo y las 16 web originales intactas. Resultado: **94 pruebas aprobadas**, también con el wheel instalado en un entorno limpio usando los locks; **pip check sin incompatibilidades**.

Cinco pruebas inician Uvicorn real, hacen HTTP por sockets y capturan stdout/stderr para detectar entradas ficticias y trazas. Cubren análisis, errores, confianza del proxy, recepción lenta y saturación. Las demás cubren configuración, cabeceras, caché, health, hosts, orígenes, endpoints y límites. Ejecutar la suite sin variables de producción heredadas: las pruebas específicas configuran su entorno.

Se simula la terminación TLS con un proxy local confiable. **No se ha verificado un certificado, HTTPS externo ni infraestructura desplegada.** Repetir las comprobaciones al elegir proveedor. Esta revisión específica no es una auditoría profesional ni garantiza ausencia de vulnerabilidades.

Nuevos archivos: `src/password_security_checker/web/config.py` (configuración), `server.py` en la misma carpeta (arranque), `tests/test_config.py`, `tests/test_production.py`, `tests/test_server.py`, `requirements.lock`, `requirements-test.lock` y `.env.example`. La API y los textos/protección de transporte del frontend se ajustan sin cambiar el núcleo ni CSS. `.gitignore` excluye configuración privada y material TLS.

Referencias: [FastAPI detrás de un proxy](https://fastapi.tiangolo.com/advanced/behind-a-proxy/), [HTTPS y terminación TLS](https://fastapi.tiangolo.com/deployment/https/).

## Deploy en Render

Configuración para **Web Service Free**, conectado mediante Git Provider a
`heberto98/password-security-checker`, rama `main`. No se ha desplegado desde
esta tarea ni se requieren credenciales de Render en el repositorio.

### Por qué no necesitamos IP del reverse proxy

Render documenta que el puerto de la aplicación no es accesible directamente
desde Internet: el balanceador termina TLS y entrega HTTP interno; el HTTP público
se redirige a HTTPS antes de llegar a la aplicación.
[Contrato de Web Services](https://render.com/docs/web-services#port-binding).
Además, los Web Services Free no reciben tráfico de la red privada.
[Red privada](https://render.com/docs/private-network).

A partir de estas garantías, el modo explícito `DEPLOYMENT_TARGET=render-free`
trata HTTPS **externo** como propiedad del ingreso de esa plataforma, no como
una afirmación de `X-Forwarded-Proto`. Uvicorn deja `proxy_headers=False` y
`forwarded_allow_ips=""`: ignora X-Forwarded-Proto, X-Forwarded-For y
X-Forwarded-Host; tampoco se interpreta Forwarded. No se cambia la IP del cliente
ni el esquema HTTP interno del scope ASGI. La aplicación usa el origen HTTPS
canónico validado para comprobar Origin y emitir HSTS.

No se han inventado rangos de Render ni se acepta `*`. Render proporciona
`FORWARDED_ALLOW_IPS=*` en Python, pero el arranque del proyecto anula esa
configuración de manera explícita.
[Variables automáticas](https://render.com/docs/environment-variables).

Esto cambia **dónde** se exige TLS externo: en Render Free lo garantiza el
ingreso de Render; no se intenta verificar TLS usando una cabecera no autenticada.
Una petición HTTP directa al proceso será aceptada bajo este modo, porque se
presupone que ya pasó por ese ingreso. Por eso **no sirve para un servidor
expuesto directamente**, un túnel HTTP o cualquier plataforma distinta.
El modo genérico conserva el rechazo de HTTP y la lista explícita de proxies.

El arranque Render exige APP_ENV=production, RENDER=true, RENDER_SERVICE_TYPE=web,
hostname onrender.com y URL HTTPS coherentes, PORT válido y escucha 0.0.0.0.
No basta con una cabecera ni con RENDER=true para activar este modo.
Estas variables pertenecen al entorno del proceso, pero **no son una
atestación criptográfica ni prueban el plan Free**. No existe aquí una consulta
a la cuenta de Render. El operador debe mantener el servicio en Free.

**Antes de cambiar el servicio a un plan de pago**, revisar la frontera de red:
esos servicios pueden recibir conexiones privadas que no pasaron por TLS.
No basta con conservar render-free o añadir IP privadas indiscriminadamente.
Habrá que aislar/autenticar el ingreso o volver a un proxy explícitamente
verificable. Esta fase no implementa ni autoriza ese cambio.

### Pantalla Configure and deploy your new Web Service

Elige **Git Provider**, conecta GitHub y selecciona el repositorio; no uses
la opción Public Git Repository si quieres integración directa y auto-deploys.

| Campo | Valor |
| --- | --- |
| Name | `password-security-checker` (si no está disponible, un nombre similar) |
| Project / Environment | Opcional; dejar sin asignar si no tienes uno |
| Language / Runtime | `Python 3`, no Docker |
| Branch | `main` |
| Region | La disponible más cercana a tus usuarios; para México, Oregon (US West) es una opción |
| Root Directory | Vacío: usar la raíz del repositorio |
| Instance Type / Compute plan | **Free** |
| Build Command | `python -m pip install -r requirements.lock && python -m pip install --no-deps . && python -m pip check` |
| Start Command | `python -B -m password_security_checker.web.server` |
| Health Check Path | `/healthz` |
| Auto-Deploy | `On Commit` para desplegar los futuros pushes a main |

Si el selector de región cambia, otra región Free funciona: ninguna decisión
de seguridad depende de una IP o región hardcodeada. No añadas servicios privados.
Con On Commit, sube a main solo cambios ya verificados. No elijas After CI Checks
Pass hasta tener CI configurado: con cero checks no se dispara el auto-deploy.
[Comportamiento de auto-deploy](https://render.com/docs/deploys#automatic-deploys).

El Build Command instala las versiones bloqueadas y construye/instala el paquete,
incluidos los archivos web. No instala el extra de pruebas. No requiere npm,
Gunicorn, Docker, una base de datos ni comandos de migración.
`.python-version` selecciona la familia 3.12; Render usa su último parche disponible.
No crees PYTHON_VERSION: sobrescribiría este archivo. No es un pin del parche
exacto; revisar el Python efectivo en el build y repetir pruebas al actualizarlo.
[Selección de Python](https://render.com/docs/python-version).

### Environment Variables: crea solamente estas dos

| Key | Value |
| --- | --- |
| `APP_ENV` | `production` |
| `DEPLOYMENT_TARGET` | `render-free` |

No importes `.env.example` completo: contiene valores de desarrollo local.
No crees `ALLOWED_HOSTS`, `PUBLIC_ORIGIN`, `TRUSTED_PROXY_IPS`, `BIND_HOST`,
`PORT`, `FORWARDED_ALLOW_IPS` ni `PYTHON_VERSION` para este primer deployment.
También deja sin definir MAX_CONCURRENCY y BODY_TIMEOUT_SECONDS: se usarán 64 y 5.

Render suministra automáticamente:

| Variable | Uso en este proyecto |
| --- | --- |
| `RENDER` | Debe ser `true` |
| `RENDER_SERVICE_TYPE` | Debe ser `web` |
| `RENDER_EXTERNAL_HOSTNAME` | Valor predeterminado de ALLOWED_HOSTS, específico de este servicio |
| `RENDER_EXTERNAL_URL` | Valor predeterminado de PUBLIC_ORIGIN; debe ser HTTPS y coincidir con el hostname |
| `PORT` | Puerto real de escucha; normalmente 10000, sin fijarlo en código |
| `FORWARDED_ALLOW_IPS` | El valor automático de Python no se utiliza |

No crees ni sobrescribas las variables RENDER_*. Solo se consumen las
documentadas; no se usan nombres internos no garantizados.

### Advanced y primer deployment sin URL previa

- Health Check Path: `/healthz`. Si no aparece en el formulario, configurar
  Settings → Health Checks después de crear el servicio.
- Pre-Deploy Command: vacío. Secret Files, discos y servicios auxiliares: ninguno.
- Build Filters: dejarlos vacíos. No habilitar previews ni integrar APM/log drains
  que capturen solicitudes; no añadir caché delante de la API.
- No hay certificados o claves que cargar. Mantener el dominio onrender.com
  habilitado y no añadir dominios personalizados en este primer deployment.

Al pulsar Create/Deploy Web Service, Render asigna el hostname antes de arrancar
el proceso y lo expone en sus variables. La aplicación deriva host y origen de
ellas: **no necesitas conocer, adivinar ni escribir la URL previamente**, no hay
un primer arranque inseguro, y no hace falta un segundo deploy para completar
ALLOWED_HOSTS/PUBLIC_ORIGIN. Si faltan los metadatos, el arranque falla cerrado:
no se sustituyen por comodines.

Después de crearlo, la URL asignada solo la necesitas para abrir la web y ejecutar
las verificaciones siguientes. El nombre del servicio puede producir una URL con
sufijo: copia siempre la que muestre Render. Si se cambia en el futuro, se
recalcula al arrancar. Un dominio personalizado exigiría definir explícitamente
ALLOWED_HOSTS y PUBLIC_ORIGIN, conservando el hostname de Render en los hosts
permitidos y añadiendo los dominios usados por los probes. No es necesario ahora.

Render envía sus health checks con el Host onrender.com si no hay dominio propio.
Por eso /healthz funciona sin añadir localhost, comodines ni confiar en headers
de proxy. Devuelve 200 y status=ok, sin analizar contraseñas.
[Health checks de Render](https://render.com/docs/health-checks).

### Verificación después del deploy

Esperar a que el estado sea Live. Las comprobaciones locales de esta adaptación
no prueban el TLS público ni la configuración efectiva de Render.

En PowerShell, sustituir el dominio de ejemplo por el asignado:

```powershell
$checkerUrl = 'https://TU-SERVICIO.onrender.com'
curl.exe --max-time 120 -sS -D - "$checkerUrl/healthz"
curl.exe --max-time 120 -sS -D - -o NUL "$checkerUrl/"
curl.exe --max-time 120 -sS -D - -o NUL "$checkerUrl/docs"
# Solo GET sin datos: comprobar que HTTP público redirige a HTTPS.
curl.exe --max-time 120 -sS -D - -o NUL ($checkerUrl.Replace('https://', 'http://') + '/healthz')
```

Esperado: health 200 con `{"status":"ok"}`, página 200, docs 404 y
HTTP público 3xx hacia HTTPS. **No uses -k**: ocultaría problemas de certificados.
No envíes contraseñas por HTTP para probar la redirección: el primer envío ya
sería inseguro. El formulario siempre debe abrirse mediante HTTPS.

Comprobar `Cache-Control: no-store`, CSP sin unsafe-inline,
`X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`,
`X-Frame-Options: DENY`, Permissions-Policy y HSTS en respuestas de la app.
No debe haber Access-Control-Allow-Origin abierto ni cookies de la aplicación.
Las páginas de espera/errores del proveedor pueden tener otras cabeceras;
no confundirlas con una respuesta de nuestra API.

En el navegador:

1. Abrir HTTPS y confirmar certificado válido y ausencia de contenido mixto.
2. Analizar solo `aaa123xQ7!`: debe dar 0, nivel bajo y vaciar el campo.
3. Hacer un segundo análisis con `RenderDemoOnly-7X!` y usar Limpiar.
4. En Network, comprobar POST /api/analyze al mismo origen, sin contraseña
   en URL, respuesta o cabeceras; solo en el cuerpo JSON de la solicitud.
5. Verificar que no hay peticiones a terceros ni almacenamiento del frontend.
6. Revisar Render → Logs en ese intervalo: no debe aparecer
   `RenderDemoOnly-7X!`, el cuerpo, access logs de Uvicorn ni trazas con entrada.

Para errores controlados, usando exclusivamente un marcador ficticio:

```powershell
$payload = '{"password":["RenderDemoOnly-7X!"]}'
try {
    Invoke-WebRequest -Uri "$checkerUrl/api/analyze" -Method Post -ContentType 'application/json' -Body $payload -UseBasicParsing
} catch {
    $_.Exception.Response.StatusCode
    $_.ErrorDetails.Message
}
```

Debe responder 422 con un mensaje genérico, nunca el marcador. Revisar también
no-store en Network o en la respuesta HTTP. Si la API falla o el marcador aparece
en logs, suspender el servicio e investigar; no activar trace/access logs para
diagnosticar usando contraseñas reales.

### Privacidad, límites y operación de Free

La aplicación conserva límites, ausencia de persistencia, CORS cerrado y errores
genéricos. No interpreta IP de usuarios a partir de X-Forwarded-For ni añade
rate limiting por una IP que no puede verificar.

Render ofrece protección DDoS automática, pero eso no constituye una cuota por IP
para esta API ni garantiza disponibilidad. Los límites locales no reemplazan
una estrategia contra abuso sostenido.
[Protección DDoS](https://render.com/docs/ddos-protection).

Los logs visibles de la aplicación no demuestran ausencia de copias internas
de Render. La plataforma termina TLS y procesa cuerpos; este repositorio no
controla buffers, retención interna ni todos sus registros. No se afirma
«Render nunca almacena contraseñas». No habilitar capturas de cuerpos ni usar
datos reales. Los request logs de plataforma, cuando el plan de workspace los
ofrece, son independientes de los access logs de Uvicorn.
[Logs de Render](https://render.com/docs/logging).

Free es adecuado para esta demo educativa, no para prometer un servicio crítico
de contraseñas. Render lo duerme tras 15 minutos sin tráfico; el siguiente acceso
puede tardar alrededor de un minuto y hay límites de uso. Esperar a que despierte
antes de analizar; no añadir pings para mantenerlo despierto. Render desaconseja
Free para aplicaciones de producción críticas.
[Limitaciones Free](https://render.com/docs/free).

### Pruebas de esta adaptación

Línea base: 94 pruebas. Resultado: **108 pruebas aprobadas**. Se mantienen todas
las anteriores y se añaden 14 casos de configuración/HTTP para Render.
Se comprueba el arranque sin URL manual, metadatos inválidos, opt-in explícito,
headers falsificados, health, errores y límites; un caso inicia Uvicorn real con
FORWARDED_ALLOW_IPS=* en el entorno y verifica el comportamiento seguro y los logs.
No cambian núcleo, puntuación, frontend ni dependencias.
