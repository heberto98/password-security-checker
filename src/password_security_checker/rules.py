"""Comprobaciones individuales para el análisis local de contraseñas."""

import unicodedata


def check_length(password: str, minimum_length: int) -> tuple[int, bool]:
    """Devuelve (longitud, cumple_mínimo) sin modificar la contraseña.

    El mínimo debe ser un entero positivo y lo elige quien llama a la
    función. Alcanzarlo no garantiza que la contraseña sea segura.
    La longitud se calcula con len(): cuenta puntos de código Unicode,
    incluidos los espacios, no necesariamente caracteres visuales.
    """
    if isinstance(minimum_length, bool) or not isinstance(minimum_length, int):
        raise TypeError("minimum_length debe ser un entero positivo.")
    if minimum_length < 1:
        raise ValueError("minimum_length debe ser mayor que cero.")

    length = len(password)
    return length, length >= minimum_length


def check_character_diversity(password: str) -> dict[str, bool]:
    """Indica qué tipos de caracteres aparecen, sin evaluar fortaleza.

    Reconoce minúsculas, mayúsculas y dígitos decimales Unicode.
    Los símbolos incluyen puntuación y símbolos Unicode (como emojis).
    Espacios, controles y marcas combinantes no cuentan como símbolos.
    El resultado no contiene la contraseña ni sus caracteres.
    """
    return {
        "has_lowercase": any(char.islower() for char in password),
        "has_uppercase": any(char.isupper() for char in password),
        "has_digit": any(char.isdecimal() for char in password),
        "has_symbol": any(
            unicodedata.category(char).startswith(("P", "S"))
            for char in password
        ),
    }
