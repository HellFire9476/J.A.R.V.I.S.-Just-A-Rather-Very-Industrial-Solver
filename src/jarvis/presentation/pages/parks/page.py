
from uuid import UUID

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
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

from jarvis.application.services.park_service import ParkService
from jarvis.domain.entities.park import Park
from jarvis.domain.entities.project import Project
from jarvis.presentation.dialogs.park_dialog import ParkDialog


class ParksPage(QWidget):
    """Interface de gestion des parcs industriels."""

    parks_changed = Signal()
    park_selected = Signal(object)

    def __init__(
        self,
        service: ParkService | None = None,
        parent=None,
    ):
        super().__init__(parent)

        self.setObjectName("ParksPage")

        self.service = service or ParkService()
        self.project: Project | None = None
        self.advanced_view = False

        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 28, 30, 25)
        layout.setSpacing(20)

        # En-tête
        header = QHBoxLayout()
        title_area = QVBoxLayout()

        title = QLabel("Parcs industriels")
        title.setObjectName("PageTitle")

        subtitle = QLabel(
            "Organisez vos installations et vos zones de production."
        )
        subtitle.setObjectName("PageSubtitle")
        subtitle.setWordWrap(True)

        title_area.addWidget(title)
        title_area.addWidget(subtitle)

        header.addLayout(title_area)
        header.addStretch()

        # Sélecteur de vue
        self.simple_button = QPushButton("Vue simplifiée")
        self.advanced_button = QPushButton("Vue avancée")

        self.view_group = QButtonGroup(self)
        self.view_group.setExclusive(True)

        for index, button in enumerate(
            (self.simple_button, self.advanced_button)
        ):
            button.setObjectName("ModeButton")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setMinimumHeight(40)
            self.view_group.addButton(button, index)
            header.addWidget(button)

        self.simple_button.setChecked(True)

        self.simple_button.clicked.connect(
            lambda checked=False: self.set_view_mode(False)
        )
        self.advanced_button.clicked.connect(
            lambda checked=False: self.set_view_mode(True)
        )

        # Création
        self.create_button = QPushButton("+ Nouveau parc")
        self.create_button.setObjectName("PrimaryButton")
        self.create_button.setMinimumHeight(40)
        self.create_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.create_button.setEnabled(False)
        self.create_button.clicked.connect(
            lambda checked=False: self.create_park()
        )

        header.addWidget(self.create_button)

        layout.addLayout(header)

        # Informations du projet actif
        self.project_label = QLabel("Aucun projet ouvert")
        self.project_label.setObjectName("ProjectMetadata")

        layout.addWidget(self.project_label)

        # Titre de la liste
        self.count_label = QLabel("PARCS INDUSTRIELS")
        self.count_label.setObjectName("SectionLabel")

        layout.addWidget(self.count_label)

        # Liste défilante
        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("ProjectScrollArea")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        self.container = QWidget()
        self.container.setObjectName("ProjectContainer")

        self.list_layout = QVBoxLayout(self.container)
        self.list_layout.setContentsMargins(0, 5, 8, 10)
        self.list_layout.setSpacing(12)

        self.scroll_area.setWidget(self.container)
        layout.addWidget(self.scroll_area, 1)

    def set_project(self, project: Project | None):
        """Définit la partie dont les parcs doivent être affichés."""

        self.project = project

        self.create_button.setEnabled(project is not None)

        if project is None:
            self.project_label.setText("Aucun projet ouvert")
        else:
            self.project_label.setText(
                f"PARTIE ACTIVE  •  {project.name}"
            )

        self.refresh()

    def set_view_mode(self, advanced: bool):
        """Change entre la vue simplifiée et la vue avancée."""

        if self.advanced_view == advanced:
            return

        self.advanced_view = advanced
        self.refresh()

    def _clear_list(self):
        """Supprime les anciens widgets de la liste."""

        while self.list_layout.count():
            item = self.list_layout.takeAt(0)

            widget = item.widget()

            if widget is not None:
                # Masque immédiatement l'ancien widget : deleteLater()
                # attend le prochain cycle Qt et peut laisser une carte
                # fantôme visible lors de rafraîchissements rapprochés.
                widget.hide()
                widget.deleteLater()

    def refresh(self):
        """Recharge les parcs de la partie active."""

        self._clear_list()

        if self.project is None:
            self.count_label.setText("PARCS INDUSTRIELS  •  0")
            self._show_empty_state(
                "Aucune partie sélectionnée",
                "Ouvre une partie pour accéder à ses parcs industriels.",
            )
            return

        try:
            parks = self.service.get_all_parks(self.project.id)

        except Exception as error:
            self.count_label.setText("ERREUR DE CHARGEMENT")

            QMessageBox.critical(
                self,
                "Chargement impossible",
                f"Impossible de charger les parcs :\n{error}",
            )
            return

        count = len(parks)

        self.count_label.setText(
            f"PARCS INDUSTRIELS  •  {count}"
        )

        if not parks:
            self._show_empty_state(
                "Aucun parc industriel",
                "Commence par créer ton premier parc industriel.",
            )
            return

        for park in parks:
            self.list_layout.addWidget(
                self._create_park_card(park)
            )

        self.list_layout.addStretch()

    def _show_empty_state(self, title_text: str, detail: str):
        """Affiche un état vide explicite."""

        card = QFrame()
        card.setObjectName("EmptyProjectsCard")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 30, 28, 30)
        layout.setSpacing(12)

        icon = QLabel("INDUSTRIAL ZONE")
        icon.setObjectName("Eyebrow")

        title = QLabel(title_text)
        title.setObjectName("SectionTitle")

        description = QLabel(detail)
        description.setObjectName("PageSubtitle")
        description.setWordWrap(True)

        layout.addWidget(icon)
        layout.addWidget(title)
        layout.addWidget(description)

        if self.project is not None:
            button = QPushButton("Créer mon premier parc")
            button.setObjectName("PrimaryButton")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(
                lambda checked=False: self.create_park()
            )
            layout.addSpacing(5)
            layout.addWidget(
                button,
                0,
                Qt.AlignmentFlag.AlignLeft,
            )

        self.list_layout.addWidget(card)
        self.list_layout.addStretch()

    def _create_park_card(self, park: Park) -> QFrame:
        """Construit une carte de parc industriel."""

        card = QFrame()
        card.setObjectName("ProjectCard")

        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(20, 17, 20, 17)
        card_layout.setSpacing(18)

        # Identification visuelle
        icon = QFrame()
        icon.setObjectName("ParkIconBadge")
        icon.setFixedSize(46, 46)

        icon_layout = QVBoxLayout(icon)
        icon_layout.setContentsMargins(0, 0, 0, 0)

        icon_label = QLabel("P")
        icon_label.setObjectName("ParkIconLabel")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_layout.addWidget(icon_label)
        card_layout.addWidget(icon)

        # Informations
        info = QVBoxLayout()
        info.setSpacing(5)

        name = QLabel(park.name)
        name.setObjectName("ProjectTitle")

        description = QLabel(
            park.description or "Aucune description renseignée."
        )
        description.setObjectName("ProjectDescription")
        description.setWordWrap(True)

        location = park.location or "Localisation non renseignée"

        metadata = QLabel(f"LOCALISATION  •  {location}")
        metadata.setObjectName("ProjectMetadata")

        info.addWidget(name)
        info.addWidget(description)
        info.addWidget(metadata)

        if self.advanced_view:
            technical = QLabel(
                f"ID : {park.id}\n"
                f"Créé le : {park.created_at.astimezone().strftime('%d/%m/%Y à %H:%M')}\n"
                f"Modifié le : {park.updated_at.astimezone().strftime('%d/%m/%Y à %H:%M')}"
            )
            technical.setObjectName("ProjectMetadata")
            technical.setWordWrap(True)
            info.addWidget(technical)

        card_layout.addLayout(info, 1)

        # Actions
        actions = QVBoxLayout()
        actions.setSpacing(7)

        edit_button = QPushButton("Modifier")
        edit_button.setObjectName("SecondarySmallButton")
        edit_button.clicked.connect(
            lambda checked=False, pid=park.id:
            self.edit_park(pid)
        )

        archive_button = QPushButton("Archiver")
        archive_button.setObjectName("DangerSmallButton")
        archive_button.clicked.connect(
            lambda checked=False, pid=park.id:
            self.archive_park(pid)
        )

        actions.addWidget(edit_button)
        actions.addWidget(archive_button)

        card_layout.addLayout(actions)

        return card

    def create_park(self):
        """Ouvre le formulaire de création."""

        if self.project is None:
            return

        dialog = ParkDialog(parent=self)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        try:
            park = self.service.create_park(
                project_id=self.project.id,
                **dialog.get_values(),
            )

            self.refresh()
            self.parks_changed.emit()
            self.park_selected.emit(park)

        except ValueError as error:
            QMessageBox.warning(
                self,
                "Informations invalides",
                str(error),
            )

        except Exception as error:
            QMessageBox.critical(
                self,
                "Création impossible",
                f"Impossible de créer le parc :\n{error}",
            )

    def edit_park(self, park_id: UUID):
        """Modifie un parc existant."""

        if self.project is None:
            return

        try:
            park = self.service.get_park(
                self.project.id,
                park_id,
            )

        except Exception as error:
            QMessageBox.critical(
                self,
                "Chargement impossible",
                str(error),
            )
            return

        dialog = ParkDialog(park, self)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        try:
            updated = self.service.update_park(
                self.project.id,
                park_id,
                **dialog.get_values(),
            )

            self.refresh()
            self.parks_changed.emit()
            self.park_selected.emit(updated)

        except ValueError as error:
            QMessageBox.warning(
                self,
                "Modification impossible",
                str(error),
            )

        except Exception as error:
            QMessageBox.critical(
                self,
                "Modification impossible",
                str(error),
            )

    def archive_park(self, park_id: UUID):
        """Archive un parc après confirmation."""

        if self.project is None:
            return

        answer = QMessageBox.question(
            self,
            "Archiver ce parc",
            "Ce parc sera retiré de la liste active et déplacé "
            "dans les archives du projet.\n\n"
            "Ses données seront conservées.\n\n"
            "Souhaites-tu continuer ?",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            self.service.delete_park(
                self.project.id,
                park_id,
            )

            self.refresh()
            self.parks_changed.emit()

            QMessageBox.information(
                self,
                "Parc archivé",
                "Le parc a été archivé avec succès.",
            )

        except Exception as error:
            QMessageBox.critical(
                self,
                "Archivage impossible",
                str(error),
            )
