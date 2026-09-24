"""Coordina reglas locales sin leer, imprimir, guardar ni enviar entradas."""

from .models import AnalysisResult, CharacterDiversity, StrengthLevel
from .rules import (
    check_character_diversity,
    check_length,
    has_repeated_characters,
    has_simple_sequence,
)


def analyze_password(password: str, minimum_length: int = 12) -> AnalysisResult:
    """Evalúa una entrada usando una puntuación educativa de 0 a 100.

    Base: cinco puntos por punto de código, hasta 100. Se restan 25 por
    cada tipo de patrón detectado (repetición y secuencia), una sola vez.
    Con algún patrón, el máximo es 69; bajo el mínimo, el máximo es 39.
    Niveles: baja 0-39, media 40-69, alta 70-100. La diversidad se informa
    pero no suma puntos. El mínimo predeterminado de 12 es configurable.
    No estima entropía, tiempo de descifrado ni exposición en filtraciones.
    """
    if not isinstance(password, str):
        raise TypeError("password debe ser una cadena de texto.")

    length, meets_minimum = check_length(password, minimum_length)
    diversity = CharacterDiversity(**check_character_diversity(password))
    repetition = has_repeated_characters(password)
    sequence = has_simple_sequence(password)

    score = min(length * 5, 100)
    score -= 25 * (int(repetition) + int(sequence))
    if repetition or sequence:
        score = min(score, 69)
    if not meets_minimum:
        score = min(score, 39)
    score = max(score, 0)

    if score < 40:
        level = StrengthLevel.LOW
    elif score < 70:
        level = StrengthLevel.MEDIUM
    else:
        level = StrengthLevel.HIGH

    return AnalysisResult(
        length=length,
        minimum_length=minimum_length,
        meets_minimum=meets_minimum,
        diversity=diversity,
        has_repetition=repetition,
        has_sequence=sequence,
        score=score,
        level=level,
    )
