
from PySide6.QtWidgets import (
    QLabel,
    QVBoxLayout,
    QWidget,
)


class PlaceholderPage(QWidget):
    """Page temporaire en attendant le développement d'un module."""

    def __init__(
        self,
        title: str,
        description: str,
        parent=None,
    ):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(35, 35, 35, 35)
        layout.setSpacing(12)

        title_label = QLabel(title)
        title_label.setObjectName("PageTitle")

        description_label = QLabel(description)
        description_label.setObjectName("PageSubtitle")
        description_label.setWordWrap(True)

        status = QLabel("MODULE EN CONSTRUCTION")
        status.setObjectName("Eyebrow")

        layout.addWidget(title_label)
        layout.addWidget(description_label)
        layout.addSpacing(15)
        layout.addWidget(status)
        layout.addStretch()
