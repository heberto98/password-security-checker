# Password Security Checker

Proyecto educativo en Python para desarrollar una herramienta defensiva de análisis de fortaleza de contraseñas.

Su objetivo es aprender a diseñar una aplicación sencilla y modular, incorporando las funciones de análisis de forma incremental.

Las contraseñas se analizarán exclusivamente de forma local. No se almacenarán ni se enviarán a servicios externos.

Actualmente, el proyecto incluye una primera regla de longitud en
`src/password_security_checker/rules.py`. La función `check_length` recibe
una contraseña y un mínimo entero positivo explícito, y devuelve una tupla
`(longitud, cumple_mínimo)`. Cumplir ese mínimo no garantiza la fortaleza de
la contraseña.

La regla cuenta puntos de código Unicode mediante `len()`, incluidos los
espacios, sin modificar la entrada. Todavía no hay interfaz de usuario ni
evaluación general de fortaleza.

La función `check_character_diversity` devuelve un diccionario con cuatro
indicadores: `has_lowercase`, `has_uppercase`, `has_digit` y `has_symbol`.
Reconoce letras y dígitos decimales Unicode; los símbolos incluyen
puntuación y emojis. Los espacios, controles y marcas combinantes no
cuentan como símbolos. Los números no decimales, como `²` o `½`, no cuentan
como dígitos. Estos indicadores describen la composición; no asignan una
puntuación ni exigen que estén presentes todos los tipos de caracteres.

Requiere Python 3.12 o superior. Licencia MIT; consulta el archivo [LICENSE](LICENSE).

## Pruebas

Las pruebas usan `unittest`, incluido en Python, y solo entradas ficticias.
Desde la raíz del proyecto, en PowerShell:

```powershell
$env:PYTHONPATH = "src"
py -3.12 -B -m unittest discover -s tests -v
```

`PYTHONPATH` permite encontrar el paquete dentro de `src` sin instalarlo.
La opción `-B` evita generar archivos de caché al ejecutar las pruebas.
