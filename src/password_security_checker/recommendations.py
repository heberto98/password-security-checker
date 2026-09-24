"""Consejos derivados del resultado, sin recibir la contraseña."""

from .models import AnalysisResult


def generate_recommendations(result: AnalysisResult) -> tuple[str, ...]:
    """Devuelve consejos ordenados y sin duplicados para un análisis.

    Primero atiende longitud y patrones; después añade consejos generales.
    No exige diversidad de caracteres ni asegura que la entrada sea segura.
    """
    messages = []
    if not result.meets_minimum:
        messages.append(
            f"Aumenta la longitud hasta al menos {result.minimum_length} "
            "caracteres para cumplir el mínimo configurado."
        )
    elif result.length < 16:
        messages.append(
            "Considera aumentar la longitud a 16 o más caracteres; "
            "es una sugerencia educativa, no una garantía de seguridad."
        )

    if result.has_repetition:
        messages.append("Evita tres o más caracteres idénticos consecutivos.")
    if result.has_sequence:
        messages.append("Evita secuencias alfabéticas o numéricas predecibles.")

    messages.extend((
        "Usa una contraseña única para cada cuenta; evita datos personales "
        "y frases conocidas.",
        "Considera un administrador de contraseñas para generar y guardar "
        "contraseñas largas y aleatorias.",
        "Activa la autenticación multifactor cuando esté disponible.",
        "La puntuación es orientativa: no comprueba filtraciones ni "
        "garantiza que la contraseña sea segura.",
    ))
    return tuple(messages)
