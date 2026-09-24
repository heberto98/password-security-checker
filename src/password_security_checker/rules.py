"""Comprobaciones individuales para el análisis local de contraseñas."""


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
