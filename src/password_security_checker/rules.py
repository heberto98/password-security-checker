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


def has_repeated_characters(password: str) -> bool:
    """Detecta tres o más puntos de código idénticos consecutivos.

    Distingue mayúsculas de minúsculas e incluye espacios y Unicode.
    No detecta bloques repetidos como 'ababab' ni normaliza la entrada.
    Devuelve solo un indicador, sin incluir caracteres de la contraseña.
    """
    for index in range(len(password) - 2):
        if password[index] == password[index + 1] == password[index + 2]:
            return True
    return False


def has_simple_sequence(password: str) -> bool:
    """Detecta secuencias ASCII de al menos tres letras o dígitos.

    Reconoce a-z y 0-9 en ambos sentidos, sin distinguir mayúsculas.
    No une extremos (890, zab), no combina letras con números y no
    detecta patrones de teclado ni secuencias de otros alfabetos.
    Devuelve solo un indicador, sin incluir partes de la contraseña.
    """
    ordered_characters = (
        "abcdefghijklmnopqrstuvwxyz",
        "zyxwvutsrqponmlkjihgfedcba",
        "0123456789",
        "9876543210",
    )
    for index in range(len(password) - 2):
        segment = password[index:index + 3]
        if segment.isascii() and any(
            segment.lower() in order for order in ordered_characters
        ):
            return True
    return False
