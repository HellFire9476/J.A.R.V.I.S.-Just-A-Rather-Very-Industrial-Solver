"""Formatage homogène des valeurs numériques destinées à l'interface."""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation


def format_decimal(
    value: Decimal | int | float | str,
    *,
    max_decimals: int = 3,
    grouping: bool = False,
) -> str:
    """Affiche un nombre sans zéros décimaux insignifiants.

    La valeur métier n'est jamais modifiée : l'arrondi est uniquement appliqué
    à la représentation destinée à l'utilisateur.
    """
    if max_decimals < 0:
        raise ValueError("Le nombre maximal de décimales ne peut pas être négatif.")

    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return str(value)

    if not number.is_finite():
        return str(value)

    quantum = Decimal(1).scaleb(-max_decimals)
    try:
        rounded = number.quantize(quantum, rounding=ROUND_HALF_UP)
    except InvalidOperation:
        return str(value)

    if rounded == 0:
        rounded = abs(rounded)

    format_spec = f",.{max_decimals}f" if grouping else f".{max_decimals}f"
    text = format(rounded, format_spec)
    if "." in text:
        text = text.rstrip("0").rstrip(".")

    if grouping:
        text = text.replace(",", "\u00a0")
    return text.replace(".", ",")


def format_power(value: Decimal | int | float | str) -> str:
    """Affiche une puissance avec au plus deux décimales."""
    return format_decimal(value, max_decimals=2, grouping=True)
