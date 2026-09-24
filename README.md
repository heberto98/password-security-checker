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

Requiere Python 3.12 o superior. Licencia MIT; consulta el archivo [LICENSE](LICENSE).
