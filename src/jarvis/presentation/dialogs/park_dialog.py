
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QTextEdit,
)

from jarvis.domain.entities.park import Park


class ParkDialog(QDialog):
    """Formulaire de création et de modification d'un parc."""

    def __init__(
        self,
        park: Park | None = None,
        parent=None,
    ):
        super().__init__(parent)

        self.park = park

        self.setWindowTitle(
            "Modifier un parc" if park else "Nouveau parc industriel"
        )
        self.setMinimumWidth(480)
        self.setModal(True)

        self._build_ui()

        if park is not None:
            self._load_park(park)

    def _build_ui(self):
        from PySide6.QtWidgets import QVBoxLayout

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(16)

        title = QLabel(
            "Informations du parc industriel"
        )
        title.setObjectName("DialogTitle")

        description = QLabel(
            "Définis l'identité et la fonction de ton installation."
        )
        description.setObjectName("PageSubtitle")
        description.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(description)

        form = QFormLayout()
        form.setSpacing(13)

        self.name_input = QLineEdit()
        self.name_input.setObjectName("FormInput")
        self.name_input.setMaxLength(80)
        self.name_input.setPlaceholderText(
            "Exemple : Parc métallurgique"
        )

        self.description_input = QTextEdit()
        self.description_input.setObjectName("FormInput")
        self.description_input.setPlaceholderText(
            "Décris la fonction de ton parc..."
        )
        self.description_input.setMaximumHeight(100)

        self.location_input = QLineEdit()
        self.location_input.setObjectName("FormInput")
        self.location_input.setMaxLength(120)
        self.location_input.setPlaceholderText(
            "Exemple : Dune Desert"
        )

        form.addRow("Nom du parc :", self.name_input)
        form.addRow("Description :", self.description_input)
        form.addRow("Localisation :", self.location_input)

        layout.addLayout(form)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )

        self.buttons.button(
            QDialogButtonBox.StandardButton.Save
        ).setText(
            "Enregistrer" if self.park else "Créer le parc"
        )

        self.buttons.accepted.connect(self._validate_form)
        self.buttons.rejected.connect(self.reject)

        layout.addStretch()
        layout.addWidget(self.buttons)

    def _load_park(self, park: Park):
        """Charge les informations du parc dans le formulaire."""

        self.name_input.setText(park.name)
        self.description_input.setPlainText(park.description)
        self.location_input.setText(park.location or "")

    def _validate_form(self):
        """Vérifie les informations obligatoires."""

        if not self.name_input.text().strip():
            QMessageBox.warning(
                self,
                "Nom manquant",
                "Le nom du parc est obligatoire.",
            )
            self.name_input.setFocus()
            return

        self.accept()

    def get_values(self) -> dict:
        """Retourne les informations saisies."""

        location = self.location_input.text().strip()

        return {
            "name": self.name_input.text().strip(),
            "description": self.description_input.toPlainText().strip(),
            "location": location or None,
        }
