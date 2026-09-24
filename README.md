# Password Security Checker

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
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
```

Si ya tienes el proyecto, comienza dentro de su carpeta y omite los dos primeros
comandos. Se usa el ejecutable del entorno directamente, sin cambiar la política
de ejecución de PowerShell ni activar scripts. Para instalar solo la aplicación,
puedes sustituir `".[test]"` por `.`.

En macOS o Linux, los comandos equivalentes son:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -e '.[test]'
```

## Ejecutar la web localmente

Desde la carpeta del proyecto, en PowerShell:

```powershell
.\.venv\Scripts\python.exe -B -m uvicorn password_security_checker.web.app:app --host 127.0.0.1 --port 8000 --no-access-log --no-proxy-headers --no-server-header
```

En macOS o Linux:

```sh
.venv/bin/python -B -m uvicorn password_security_checker.web.app:app --host 127.0.0.1 --port 8000 --no-access-log --no-proxy-headers --no-server-header
```

Abre **http://127.0.0.1:8000** en el navegador. Detén el servidor con `Ctrl+C`.
Si el puerto está ocupado, usa `--port 8001` y abre la dirección correspondiente.
No abras el HTML directamente: necesita el backend Python. JavaScript debe estar
habilitado; sin él, el formulario permanece desactivado y no envía entradas.

Usa ejemplos ficticios para explorar la herramienta. Al pulsar **Analizar
contraseña**, el campo se vacía y el resultado aparece en la misma página.
**Limpiar** borra el resultado y cancela la espera de un análisis en curso.
Puedes introducir otra entrada para empezar de nuevo.

El servidor escucha únicamente en loopback y acepta los hosts `127.0.0.1` y
`localhost`. No se ha preparado un despliegue público ni una CLI.

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
| Uvicorn `>=0.53,<0.54` | Servidor ASGI local |
| HTTPX2 `>=2.13.1,<3` (extra `test`) | Cliente utilizado por el TestClient actual de Starlette |
| setuptools `>=77` (construcción) | Instalación del paquete y empaquetado del frontend |

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
- El comando documentado desactiva los access logs y las cabeceras de proxy.
  No actives modo trace, registradores de cuerpos o depuradores con datos reales.
  No pongas contraseñas reales en URLs, comandos, scripts ni capturas de pantalla.

Si alojas la aplicación en otro equipo, la contraseña viajará a ese servidor.
La configuración actual está pensada para uso local; publicarla requeriría un
diseño de despliegue separado, HTTPS y revisión de proxy, límites y registros.
No basta con cambiar el host a `0.0.0.0`.

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
