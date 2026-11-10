
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QTextEdit,
    QVBoxLayout,
)

from jarvis.domain.entities.project import Project


class ProjectDialog(QDialog):
    """Fenêtre de création et de modification d'une partie."""

    def __init__(
        self,
        project: Project | None = None,
        parent=None,
    ):
        super().__init__(parent)

        self.project = project

        self.setWindowTitle(
            "Modifier une partie" if project else "Nouvelle partie"
        )
        self.setMinimumWidth(480)
        self.setModal(True)

        self._build_ui()

        if project:
            self._load_project(project)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(16)

        title = QLabel(
            "Informations de la partie"
        )
        title.setObjectName("DialogTitle")

        description = QLabel(
            "Configure les informations de ta partie Satisfactory."
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
            "Exemple : Monde principal"
        )

        self.description_input = QTextEdit()
        self.description_input.setObjectName("FormInput")
        self.description_input.setPlaceholderText(
            "Description facultative de ta partie..."
        )
        self.description_input.setMaximumHeight(105)

        self.version_input = QLineEdit()
        self.version_input.setObjectName("FormInput")
        self.version_input.setMaxLength(40)
        self.version_input.setPlaceholderText(
            "Exemple : 1.2"
        )

        form.addRow("Nom de la partie :", self.name_input)
        form.addRow("Description :", self.description_input)
        form.addRow("Version du jeu :", self.version_input)

        layout.addLayout(form)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )

        self.buttons.button(
            QDialogButtonBox.StandardButton.Ok
        ).setText(
            "Enregistrer" if self.project else "Créer la partie"
        )

        self.buttons.accepted.connect(self._validate_form)
        self.buttons.rejected.connect(self.reject)

        layout.addStretch()
        layout.addWidget(self.buttons)

    def _load_project(self, project: Project):
        """Préremplit les informations d'une partie."""

        self.name_input.setText(project.name)
        self.description_input.setPlainText(
            project.description
        )
        self.version_input.setText(
            project.game_version or ""
        )

    def _validate_form(self):
        """Vérifie les champs avant validation."""

        if not self.name_input.text().strip():
            QMessageBox.warning(
                self,
                "Nom manquant",
                "Le nom de la partie est obligatoire.",
            )
            self.name_input.setFocus()
            return

        self.accept()

    def get_values(self) -> dict:
        """Retourne les informations saisies."""

        version = self.version_input.text().strip()

        return {
            "name": self.name_input.text().strip(),
            "description": self.description_input.toPlainText().strip(),
            "game_version": version or None,
        }
