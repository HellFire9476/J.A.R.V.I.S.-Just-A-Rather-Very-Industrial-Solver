"""QDoubleSpinBox qui masque les zéros décimaux non significatifs."""

from PySide6.QtWidgets import QDoubleSpinBox


class CompactDoubleSpinBox(QDoubleSpinBox):
    """Conserve la précision configurée sans imposer des décimales à l'écran."""

    def textFromValue(self, value: float) -> str:  # noqa: N802 - méthode Qt
        text = super().textFromValue(value)
        decimal_point = self.locale().decimalPoint()
        if decimal_point in text:
            text = text.rstrip("0").rstrip(decimal_point)
        return text
