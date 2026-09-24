# Password Security Checker

Proyecto educativo en Python para desarrollar una herramienta defensiva de análisis de fortaleza de contraseñas.

Su objetivo es aprender a diseñar una aplicación sencilla y modular, incorporando las funciones de análisis de forma incremental.

Las contraseñas se analizarán exclusivamente de forma local. No se almacenarán ni se enviarán a servicios externos.

El núcleo puede utilizarse desde Python e incluye reglas locales en
`src/password_security_checker/rules.py`. La función `check_length` recibe
una contraseña y un mínimo entero positivo explícito, y devuelve una tupla
`(longitud, cumple_mínimo)`. Cumplir ese mínimo no garantiza la fortaleza de
la contraseña.

La regla cuenta puntos de código Unicode mediante `len()`, incluidos los
espacios, sin modificar la entrada. El analizador reúne las reglas en una
evaluación educativa. Las interfaces de terminal y gráfica quedan pendientes.

La función `check_character_diversity` devuelve un diccionario con cuatro
indicadores: `has_lowercase`, `has_uppercase`, `has_digit` y `has_symbol`.
Reconoce letras y dígitos decimales Unicode; los símbolos incluyen
puntuación y emojis. Los espacios, controles y marcas combinantes no
cuentan como símbolos. Los números no decimales, como `²` o `½`, no cuentan
como dígitos. Estos indicadores describen la composición; no asignan una
puntuación ni exigen que estén presentes todos los tipos de caracteres.

Requiere Python 3.12 o superior. Licencia MIT; consulta el archivo [LICENSE](LICENSE).

## Repeticiones consecutivas

`has_repeated_characters` devuelve `True` si encuentra tres o más puntos
de código idénticos consecutivos, por ejemplo `aaa`, `!!!` o `ñññ`.
El umbral de tres es una heurística educativa, no una garantía de seguridad.
Distingue mayúsculas de minúsculas: `aAa` devuelve `False`. Cuenta espacios
y no normaliza Unicode ni detecta bloques repetidos como `ababab`.
Solo devuelve un booleano, sin guardar ni devolver la contraseña.

## Secuencias sencillas

`has_simple_sequence` devuelve `True` si encuentra una secuencia contigua
de al menos tres letras ASCII (`a-z`) o dígitos (`0-9`), en orden ascendente
o descendente. Por ejemplo, detecta `abc`, `CbA`, `123` y `321`, incluso
dentro de una entrada más larga. No distingue mayúsculas de minúsculas.

No une los extremos (`890`, `zab`), no combina letras con números y no
detecta patrones de teclado (`qwerty`) ni secuencias de otros alfabetos.
El umbral de tres es educativo. Un resultado `False` en estas reglas solo
indica ausencia del patrón definido; no garantiza una contraseña segura.

## Analizador y puntuación educativa

`analyze_password(password, minimum_length=12)` devuelve un `AnalysisResult`
inmutable con longitud, mínimo elegido, cumplimiento de ese mínimo,
diversidad, indicadores de repetición y secuencia, puntuación y nivel.
`CharacterDiversity` agrupa los cuatro indicadores de composición y
`StrengthLevel` define los niveles `baja`, `media` y `alta`.
Estos objetos no incluyen la contraseña ni fragmentos de ella.

La puntuación es una heurística propia, no un estándar ni una estimación
de entropía o de tiempo de descifrado:

1. Se otorgan cinco puntos por punto de código, con un máximo inicial de 100.
2. Se restan 25 puntos por repetición y 25 por secuencia, una vez por tipo.
3. Si aparece alguno de esos patrones, la puntuación no puede superar 69.
4. Si no se cumple el mínimo configurado, no puede superar 39.
5. El resultado nunca baja de cero. Los niveles son baja (0-39),
   media (40-69) y alta (70-100).

El mínimo predeterminado de 12 es una decisión educativa configurable.
La diversidad no suma puntos ni impone mezclar tipos de caracteres.
Un nivel alto solo refleja estas reglas limitadas: el analizador no conoce
contraseñas comunes, filtraciones, datos personales, reutilización ni
bloques repetidos. Por ejemplo, una entrada larga y predecible como
`xQ7!xQ7!xQ7!xQ7!xQ7!` obtiene 100 porque la detección de bloques repetidos
todavía no está implementada. No uses el resultado como certificación
de seguridad ni como criterio único para aceptar contraseñas reales.

El procesamiento no escribe archivos, no usa servicios externos ni registra
entradas. La contraseña existe en memoria durante la llamada; Python no
garantiza el borrado inmediato o seguro de las cadenas de memoria.

## Pruebas

Las pruebas usan `unittest`, incluido en Python, y solo entradas ficticias.
Desde la raíz del proyecto, en PowerShell:

```powershell
$env:PYTHONPATH = "src"
py -3.12 -B -m unittest discover -s tests -v
```

`PYTHONPATH` permite encontrar el paquete dentro de `src` sin instalarlo.
La opción `-B` evita generar archivos de caché al ejecutar las pruebas.
