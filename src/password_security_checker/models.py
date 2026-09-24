"""Resultados del análisis; nunca contienen la contraseña original."""

from dataclasses import dataclass
from enum import StrEnum


class StrengthLevel(StrEnum):
    """Nivel de la heurística educativa, no una garantía de seguridad."""

    LOW = "baja"
    MEDIUM = "media"
    HIGH = "alta"


@dataclass(frozen=True)
class CharacterDiversity:
    has_lowercase: bool
    has_uppercase: bool
    has_digit: bool
    has_symbol: bool


@dataclass(frozen=True)
class AnalysisResult:
    length: int
    minimum_length: int
    meets_minimum: bool
    diversity: CharacterDiversity
    has_repetition: bool
    has_sequence: bool
    score: int
    level: StrengthLevel
