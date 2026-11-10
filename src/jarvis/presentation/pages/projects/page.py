
from uuid import UUID

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from jarvis.application.services.project_service import ProjectService
from jarvis.domain.entities.project import Project
from jarvis.presentation.dialogs.project_dialog import ProjectDialog


class ProjectPage(QWidget):
    """Page de gestion des parties Satisfactory."""

    project_opened = Signal(object)
    project_updated = Signal(object)

    def __init__(
        self,
        service: ProjectService | None = None,
        parent=None,
    ):
        super().__init__(parent)

        self.setObjectName("ProjectsPage")
        self.service = service or ProjectService()

        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 28, 30, 25)
        layout.setSpacing(20)

        # En-tête
        header = QHBoxLayout()

        title_area = QVBoxLayout()

        title = QLabel("Mes projets")
        title.setObjectName("PageTitle")

        subtitle = QLabel(
            "Gérez vos parties Satisfactory et retrouvez "
            "vos configurations industrielles."
        )
        subtitle.setObjectName("PageSubtitle")
        subtitle.setWordWrap(True)

        title_area.addWidget(title)
        title_area.addWidget(subtitle)

        header.addLayout(title_area)
        header.addStretch()

        self.create_button = QPushButton(
            "+ Nouvelle partie"
        )
        self.create_button.setObjectName("PrimaryButton")
        self.create_button.setMinimumHeight(39)
        self.create_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self.create_button.clicked.connect(self.create_project)

        header.addWidget(self.create_button)

        layout.addLayout(header)

        # Titre de la liste
        self.count_label = QLabel("PARTIES ENREGISTRÉES")
        self.count_label.setObjectName("SectionLabel")

        layout.addWidget(self.count_label)

        # Zone de défilement
        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("ProjectScrollArea")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        self.project_container = QWidget()
        self.project_container.setObjectName("ProjectContainer")

        self.project_layout = QVBoxLayout(
            self.project_container
        )
        self.project_layout.setContentsMargins(0, 5, 8, 10)
        self.project_layout.setSpacing(12)

        self.scroll_area.setWidget(self.project_container)

        layout.addWidget(self.scroll_area, 1)

    def _clear_projects(self):
        """Vide la liste avant son actualisation."""

        while self.project_layout.count():
            item = self.project_layout.takeAt(0)

            widget = item.widget()

            if widget is not None:
                widget.deleteLater()

    def refresh(self):
        """Recharge les projets depuis les fichiers JSON."""

        self._clear_projects()

        try:
            projects = self.service.get_all_projects()

        except Exception as error:
            self.count_label.setText("ERREUR DE CHARGEMENT")

            QMessageBox.critical(
                self,
                "Chargement impossible",
                f"Impossible de charger les projets :\n{error}",
            )
            return

        count = len(projects)

        self.count_label.setText(
            f"PARTIES ENREGISTRÉES  ·  {count}"
        )

        if not projects:
            self._show_empty_state()
            return

        for project in projects:
            self.project_layout.addWidget(
                self._create_project_card(project)
            )

        self.project_layout.addStretch()

    def _show_empty_state(self):
        """Affiche un message lorsque la liste est vide."""

        card = QFrame()
        card.setObjectName("EmptyProjectsCard")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(30, 35, 30, 35)
        layout.setSpacing(12)

        icon = QLabel("▤")
        icon.setObjectName("EmptyProjectIcon")

        title = QLabel("Aucune partie enregistrée")
        title.setObjectName("SectionTitle")

        description = QLabel(
            "Commence par créer ta première partie Satisfactory. "
            "Tes parcs et installations seront ensuite organisés "
            "à l'intérieur de celle-ci."
        )
        description.setObjectName("PageSubtitle")
        description.setWordWrap(True)

        button = QPushButton("Créer ma première partie")
        button.setObjectName("PrimaryButton")
        button.clicked.connect(self.create_project)

        layout.addWidget(icon, 0)
        layout.addWidget(title)
        layout.addWidget(description)
        layout.addSpacing(8)
        layout.addWidget(button, 0)

        self.project_layout.addWidget(card)
        self.project_layout.addStretch()

    def _create_project_card(self, project: Project) -> QFrame:
        """Construit une carte représentant une partie."""

        card = QFrame()
        card.setObjectName("ProjectCard")

        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(20, 17, 20, 17)
        card_layout.setSpacing(18)

        # Icône
        icon = QLabel("▤")
        icon.setObjectName("ProjectCardIcon")

        icon.setFixedWidth(36)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card_layout.addWidget(icon)

        # Informations
        info_layout = QVBoxLayout()
        info_layout.setSpacing(5)

        name = QLabel(project.name)
        name.setObjectName("ProjectTitle")

        description_text = (
            project.description
            or "Aucune description renseignée."
        )

        description = QLabel(description_text)
        description.setObjectName("ProjectDescription")
        description.setWordWrap(True)

        version_text = (
            f"Satisfactory {project.game_version}"
            if project.game_version
            else "Version du jeu non renseignée"
        )

        modified_text = project.updated_at.astimezone().strftime(
            "%d/%m/%Y à %H:%M"
        )

        metadata = QLabel(
            f"{version_text}    •    Modifié le {modified_text}"
        )
        metadata.setObjectName("ProjectMetadata")

        info_layout.addWidget(name)
        info_layout.addWidget(description)
        info_layout.addWidget(metadata)

        card_layout.addLayout(info_layout, 1)

        # Actions
        actions = QVBoxLayout()
        actions.setSpacing(7)

        open_button = QPushButton("Ouvrir")
        open_button.setObjectName("PrimarySmallButton")
        open_button.clicked.connect(
            lambda checked=False, pid=project.id:
            self.open_project(pid)
        )

        edit_button = QPushButton("Modifier")
        edit_button.setObjectName("SecondarySmallButton")
        edit_button.clicked.connect(
            lambda checked=False, pid=project.id:
            self.edit_project(pid)
        )

        actions.addWidget(open_button)
        actions.addWidget(edit_button)

        card_layout.addLayout(actions)

        return card

    def create_project(self):
        """Ouvre le formulaire de création."""

        dialog = ProjectDialog(parent=self)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        try:
            project = self.service.create_project(
                **dialog.get_values()
            )

            self.refresh()

            # Une nouvelle partie devient immédiatement active.
            self.project_opened.emit(project)

        except Exception as error:
            QMessageBox.critical(
                self,
                "Création impossible",
                f"Impossible de créer la partie :\n{error}",
            )

    def open_project(self, project_id: UUID):
        """Ouvre une partie existante."""

        try:
            project = self.service.get_project(project_id)
            self.project_opened.emit(project)

        except Exception as error:
            QMessageBox.critical(
                self,
                "Ouverture impossible",
                f"Impossible d'ouvrir cette partie :\n{error}",
            )

    def edit_project(self, project_id: UUID):
        """Ouvre le formulaire de modification."""

        try:
            project = self.service.get_project(project_id)

        except Exception as error:
            QMessageBox.critical(
                self,
                "Chargement impossible",
                f"Impossible de charger cette partie :\n{error}",
            )
            return

        dialog = ProjectDialog(project, self)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        try:
            values = dialog.get_values()

            project.name = values["name"]
            project.description = values["description"]
            project.game_version = values["game_version"]

            updated = self.service.save_project(project)

            self.refresh()
            self.project_updated.emit(updated)

        except Exception as error:
            QMessageBox.critical(
                self,
                "Modification impossible",
                f"Impossible de modifier cette partie :\n{error}",
            )
