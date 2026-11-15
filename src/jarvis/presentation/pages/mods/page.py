"""Gestion des modules disponibles et de leur activation par parc."""

from uuid import UUID

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from jarvis.application.services.mod_service import ModService
from jarvis.application.services.project_service import ProjectService
from jarvis.domain.entities.mod import ModDefinition
from jarvis.domain.entities.project import Project


class ModsPage(QWidget):
    """Présente les extensions et leur activation indépendante par parc."""

    def __init__(
        self,
        service: ModService | None = None,
        project_service: ProjectService | None = None,
        parent=None,
    ):
        super().__init__(parent)

        self.setObjectName("ModsPage")
        self.service = service or ModService()
        self.project_service = project_service or ProjectService()
        self.project: Project | None = None
        self._preferred_project_id: UUID | None = None
        self._projects_by_id: dict[str, Project] = {}
        self._selected_park_id: UUID | None = None

        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 28, 30, 25)
        root.setSpacing(17)

        header = QHBoxLayout()
        title_area = QVBoxLayout()
        title_area.setSpacing(5)

        title = QLabel("Mods & extensions")
        title.setObjectName("PageTitle")

        subtitle = QLabel(
            "Choisissez une partie et un parc pour configurer les modules "
            "qui seront utilisés dans cette installation."
        )
        subtitle.setObjectName("PageSubtitle")
        subtitle.setWordWrap(True)

        title_area.addWidget(title)
        title_area.addWidget(subtitle)
        header.addLayout(title_area)
        header.addStretch()
        root.addLayout(header)

        intro = QFrame()
        intro.setObjectName("ModsInfoPanel")
        intro_layout = QVBoxLayout(intro)
        intro_layout.setContentsMargins(18, 14, 18, 14)
        intro_layout.setSpacing(6)

        intro_title = QLabel("MODULES DISPONIBLES DANS J.A.R.V.I.S.")
        intro_title.setObjectName("SectionLabel")

        intro_text = QLabel(
            "L'activation est propre au parc sélectionné : un module peut être utilisé "
            "dans un parc et rester absent d'un autre. Désactiver un module ne supprime "
            "pas ses paramètres. Cette page configure J.A.R.V.I.S. ; elle n'installe "
            "pas les mods dans le jeu Satisfactory."
        )
        intro_text.setObjectName("PageSubtitle")
        intro_text.setWordWrap(True)

        intro_layout.addWidget(intro_title)
        intro_layout.addWidget(intro_text)
        root.addWidget(intro)

        target_row = QHBoxLayout()
        target_row.setSpacing(10)

        project_label = QLabel("PARTIE")
        project_label.setObjectName("SectionLabel")
        target_row.addWidget(project_label)

        self.project_combo = QComboBox()
        self.project_combo.setObjectName("ModsProjectSelector")
        self.project_combo.setMinimumWidth(260)
        self.project_combo.setMinimumHeight(38)
        self.project_combo.setToolTip(
            "Choisissez la partie Satisfactory qui contient le parc à configurer."
        )
        self.project_combo.currentIndexChanged.connect(self._on_project_changed)
        target_row.addWidget(self.project_combo)

        park_label = QLabel("PARC")
        park_label.setObjectName("SectionLabel")
        target_row.addWidget(park_label)

        self.park_combo = QComboBox()
        self.park_combo.setObjectName("ModsParkSelector")
        self.park_combo.setMinimumWidth(260)
        self.park_combo.setMinimumHeight(38)
        self.park_combo.setToolTip(
            "Les activations et paramètres des modules sont enregistrés séparément "
            "pour chaque parc."
        )
        self.park_combo.currentIndexChanged.connect(self._on_park_changed)
        target_row.addWidget(self.park_combo)
        target_row.addStretch()
        root.addLayout(target_row)

        self.project_status = QLabel(
            "Le catalogue est consultable sans partie active. "
            "Sélectionnez une partie et un parc pour activer un module."
        )
        self.project_status.setObjectName("ProjectMetadata")
        self.project_status.setWordWrap(True)
        root.addWidget(self.project_status)

        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("ModsScrollArea")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        self.cards_container = QWidget()
        self.cards_container.setObjectName("ModsContainer")
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 5, 8, 10)
        self.cards_layout.setSpacing(12)

        self.scroll_area.setWidget(self.cards_container)
        root.addWidget(self.scroll_area, 1)

    def set_project(self, project: Project | None) -> None:
        """Préselectionne la partie active dans le gestionnaire de modules."""

        self._preferred_project_id = project.id if project else None
        self.refresh()

    def refresh(self) -> None:
        """Recharge les parties, les parcs et le catalogue des modules."""

        self._clear_cards()

        current_project_id = self.project_combo.currentData()
        preferred_project_id = self._preferred_project_id
        project_id_to_restore = (
            str(preferred_project_id)
            if preferred_project_id is not None
            else current_project_id
        )
        previous_park_id = self._selected_park_id
        self._preferred_project_id = None

        self.project_combo.blockSignals(True)
        self.project_combo.clear()

        try:
            projects = self.project_service.get_all_projects()
        except Exception as error:
            projects = []
            self.project_status.setText(
                f"Impossible de charger les parties : {error}"
            )

        self._projects_by_id = {
            str(project.id): project for project in projects
        }

        for project in projects:
            self.project_combo.addItem(project.name, str(project.id))

        if projects:
            self.project_combo.setEnabled(True)
            selected_index = self.project_combo.findData(project_id_to_restore)
            if selected_index < 0:
                selected_index = 0
            self.project_combo.setCurrentIndex(selected_index)
            selected_project_id = self.project_combo.currentData()
            self.project = self._projects_by_id[selected_project_id]
        else:
            self.project_combo.addItem("Aucune partie enregistrée", None)
            self.project_combo.setEnabled(False)
            self.project = None

        self.project_combo.blockSignals(False)
        self._refresh_parks(previous_park_id)

    def _refresh_parks(self, previous_park_id: UUID | None = None) -> None:
        """Recharge les parcs de la partie sélectionnée."""

        self._clear_cards()
        self.park_combo.blockSignals(True)
        self.park_combo.clear()
        self._selected_park_id = None

        if self.project is None:
            self.park_combo.addItem("Sélectionnez une partie", None)
            self.park_combo.setEnabled(False)
            self.project_status.setText(
                "Le catalogue est consultable sans partie active. "
                "Sélectionnez une partie et un parc pour activer un module."
            )
            self.park_combo.blockSignals(False)
            self._render_mod_cards()
            return

        try:
            parks = self.service.list_parks(self.project.id)
        except Exception as error:
            parks = []
            self.project_status.setText(
                f"Impossible de charger les parcs de {self.project.name} : {error}"
            )

        if not parks:
            self.park_combo.addItem("Aucun parc dans cette partie", None)
            self.park_combo.setEnabled(False)
            self.project_status.setText(
                f"Partie sélectionnée : {self.project.name}. "
                "Créez un parc industriel pour pouvoir y activer des modules."
            )
            self.park_combo.blockSignals(False)
            self._render_mod_cards()
            return

        self.park_combo.setEnabled(True)
        for park in parks:
            self.park_combo.addItem(park.name, str(park.id))

        selected_index = self.park_combo.findData(
            str(previous_park_id) if previous_park_id else None
        )
        if selected_index < 0:
            selected_index = 0
        self.park_combo.setCurrentIndex(selected_index)
        self._selected_park_id = UUID(self.park_combo.currentData())
        self.project_status.setText(
            f"Partie sélectionnée : {self.project.name}. "
            "Les changements ne concerneront que le parc choisi."
        )
        self.park_combo.blockSignals(False)
        self._render_mod_cards()

    def _on_project_changed(self, index: int) -> None:
        if index < 0:
            return

        project_id = self.project_combo.itemData(index)
        self.project = self._projects_by_id.get(project_id)
        self._refresh_parks()

    def _on_park_changed(self, index: int) -> None:
        if index < 0:
            self._selected_park_id = None
        else:
            park_id = self.park_combo.itemData(index)
            self._selected_park_id = UUID(park_id) if park_id else None

        self._clear_cards()
        self._render_mod_cards()

    def _render_mod_cards(self) -> None:
        """Affiche le catalogue, même lorsqu'aucun parc n'est sélectionné."""

        for definition in self.service.list_supported_mods():
            enabled = None
            if self.project is not None and self._selected_park_id is not None:
                try:
                    state = self.service.get_mod_state(
                        self.project.id,
                        self._selected_park_id,
                        definition.mod_id,
                    )
                except Exception as error:
                    self.project_status.setText(
                        f"Impossible de lire l'état de {definition.name} : {error}"
                    )
                else:
                    enabled = state.enabled

            self.cards_layout.addWidget(
                self._create_mod_card(definition, enabled)
            )

        self.cards_layout.addStretch()

    def _create_mod_card(
        self,
        definition: ModDefinition,
        enabled: bool | None,
    ) -> QFrame:
        card = QFrame()
        card.setObjectName("ModCard")

        row = QHBoxLayout(card)
        row.setContentsMargins(19, 17, 19, 17)
        row.setSpacing(17)

        icon_frame = QFrame()
        icon_frame.setObjectName("ModIconBadge")
        icon_frame.setFixedSize(54, 54)
        icon_layout = QVBoxLayout(icon_frame)
        icon_layout.setContentsMargins(0, 0, 0, 0)

        icon_label = QLabel(
            "⚡" if definition.mod_id == "refined_power" else "▦"
        )
        icon_label.setObjectName("ModIcon")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_layout.addWidget(icon_label)
        row.addWidget(icon_frame, 0, Qt.AlignmentFlag.AlignTop)

        details = QVBoxLayout()
        details.setSpacing(6)

        title_row = QHBoxLayout()
        title = QLabel(definition.name)
        title.setObjectName("SectionTitle")

        category = QLabel(definition.category.upper())
        category.setObjectName("ModCategory")

        title_row.addWidget(title)
        title_row.addWidget(category)
        title_row.addStretch()
        details.addLayout(title_row)

        summary = QLabel(definition.summary)
        summary.setObjectName("ProjectDescription")
        summary.setWordWrap(True)
        details.addWidget(summary)

        description = QLabel(definition.description)
        description.setObjectName("PageSubtitle")
        description.setWordWrap(True)
        details.addWidget(description)

        features = QLabel(
            "\n".join(f"•  {feature}" for feature in definition.features)
        )
        features.setObjectName("ModFeatureList")
        features.setWordWrap(True)
        details.addWidget(features)

        integration_note = QLabel(definition.integration_note)
        integration_note.setObjectName("ModIntegrationNote")
        integration_note.setWordWrap(True)
        details.addWidget(integration_note)

        row.addLayout(details, 1)

        actions = QVBoxLayout()
        actions.setSpacing(8)

        if enabled is None:
            state_text = "PARC NON SÉLECTIONNÉ"
            state_object_name = "ModStateDisabled"
            button_text = "Sélectionner un parc"
            button_object_name = "SecondarySmallButton"
        else:
            state_text = "ACTIF DANS CE PARC" if enabled else "ABSENT DE CE PARC"
            state_object_name = (
                "ModStateEnabled" if enabled else "ModStateDisabled"
            )
            button_text = "Retirer du parc" if enabled else "Ajouter au parc"
            button_object_name = (
                "SecondarySmallButton" if enabled else "PrimarySmallButton"
            )

        state_label = QLabel(state_text)
        state_label.setObjectName(state_object_name)
        state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        actions.addWidget(state_label)

        toggle = QPushButton(button_text)
        toggle.setObjectName(button_object_name)
        toggle.setMinimumWidth(155)
        toggle.setMinimumHeight(38)
        toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        toggle.setEnabled(enabled is not None)

        if enabled is None:
            toggle.setToolTip(
                "Sélectionnez une partie contenant au moins un parc, puis choisissez "
                "ce parc pour activer ou désactiver le module."
            )
        else:
            toggle.setToolTip(
                "Désactive ce module pour le parc sélectionné sans effacer ses paramètres."
                if enabled
                else "Enregistre ce module dans le parc sélectionné. "
                "Les autres parcs ne changent pas."
            )
            toggle.clicked.connect(
                lambda checked=False, mod_id=definition.mod_id, value=not enabled:
                self._set_mod_enabled(mod_id, value)
            )

        actions.addWidget(toggle)
        row.addLayout(actions)
        return card

    def _set_mod_enabled(self, mod_id: str, enabled: bool) -> None:
        if self.project is None or self._selected_park_id is None:
            return

        try:
            self.service.set_mod_enabled(
                self.project.id,
                self._selected_park_id,
                mod_id,
                enabled,
            )
        except Exception as error:
            QMessageBox.critical(
                self,
                "Enregistrement impossible",
                f"Impossible de modifier ce module :\n{error}",
            )
            return

        # Recharge depuis le dépôt pour confirmer l'état effectivement enregistré.
        self._clear_cards()
        self._render_mod_cards()

    def _clear_cards(self) -> None:
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.deleteLater()
