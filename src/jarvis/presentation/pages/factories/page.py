from uuid import UUID

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from jarvis.application.services.factory_service import FactoryService
from jarvis.application.services.park_service import ParkService
from jarvis.domain.entities.factory import Factory
from jarvis.domain.entities.park import Park
from jarvis.domain.entities.project import Project
from jarvis.domain.entities.scenario import Scenario
from jarvis.presentation.dialogs.factory_dialog import FactoryDialog
from jarvis.presentation.numeric_format import format_decimal, format_power


class ScenarioDetailsDialog(QDialog):
    """Consultation en lecture seule d'un instantané de production."""

    def __init__(self, factory: Factory, scenarios: list[Scenario], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Scénarios — {factory.name}")
        self.setMinimumSize(820, 560)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(12)
        title = QLabel(factory.name)
        title.setObjectName("DialogTitle")
        subtitle = QLabel(
            factory.description
            or "Historique des calculs de production enregistrés dans cette usine."
        )
        subtitle.setObjectName("PageSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        content = QHBoxLayout()
        self.scenario_list = QListWidget()
        self.scenario_list.setMinimumWidth(260)
        self.scenario_details = QPlainTextEdit()
        self.scenario_details.setReadOnly(True)
        self.scenario_details.setObjectName("FormInput")
        content.addWidget(self.scenario_list, 1)
        content.addWidget(self.scenario_details, 2)
        layout.addLayout(content, 1)

        buttons = QHBoxLayout()
        buttons.addStretch()
        close_button = QPushButton("Fermer")
        close_button.setObjectName("SecondarySmallButton")
        close_button.clicked.connect(self.accept)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)

        self._scenarios = {str(scenario.id): scenario for scenario in scenarios}
        for scenario in scenarios:
            rate = self._format_decimal(scenario.target_rate_per_minute)
            label = (
                f"{scenario.name}\n"
                f"{scenario.target_name} · {rate} {scenario.target_unit_label}/min"
            )
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, str(scenario.id))
            self.scenario_list.addItem(item)
        self.scenario_list.currentItemChanged.connect(self._show_selected_scenario)
        if scenarios:
            self.scenario_list.setCurrentRow(0)
        else:
            self.scenario_details.setPlainText(
                "Aucun calcul n'a encore été enregistré dans cette usine.\n\n"
                "Lance une simulation puis utilise « Enregistrer dans une usine » "
                "pour ajouter un scénario."
            )

    def _show_selected_scenario(self, current, _previous) -> None:
        if current is None:
            return
        scenario = self._scenarios.get(current.data(Qt.ItemDataRole.UserRole))
        if scenario is None:
            return
        snapshot = scenario.plan_snapshot
        lines = [
            scenario.name,
            "=" * max(12, len(scenario.name)),
            f"Produit : {scenario.target_name}",
            "Objectif : "
            f"{self._format_decimal(scenario.target_rate_per_minute)} "
            f"{scenario.target_unit_label}/min",
            f"Langue du catalogue : {scenario.locale}",
            f"Enregistré le : {scenario.created_at.astimezone().strftime('%d/%m/%Y à %H:%M')}",
            "",
            "PUISSANCE",
            "Fabrication : "
            f"{self._format_optional_power(snapshot.get('production_power_min_mw'))} à "
            f"{self._format_optional_power(snapshot.get('production_power_max_mw'))} MW",
            "Extraction : "
            f"{self._format_optional_power(snapshot.get('extraction_power_min_mw'))} à "
            f"{self._format_optional_power(snapshot.get('extraction_power_max_mw'))} MW",
            "Total : "
            f"{self._format_optional_power(snapshot.get('total_power_min_mw'))} à "
            f"{self._format_optional_power(snapshot.get('total_power_max_mw'))} MW",
            "",
            "FABRICANTS",
        ]
        machine_requirements = snapshot.get("machine_requirements", [])
        if machine_requirements:
            for machine in machine_requirements:
                lines.append(
                    f"• {machine.get('recipe_name', 'Recette')} — "
                    f"{machine.get('producer_name', 'Fabricant')} : "
                    f"{machine.get('machine_count', '—')} machine(s), "
                    f"{self._format_optional(machine.get('clock_percent'))} %"
                )
        else:
            lines.append("Aucun fabricant renseigné.")
        lines.extend(["", "RESSOURCES À FOURNIR"])
        resources = snapshot.get("resource_requirements", [])
        if resources:
            for resource in resources:
                lines.append(
                    f"• {resource.get('display_name', resource.get('class_name', 'Ressource'))} : "
                    f"{self._format_optional(resource.get('rate_per_minute'))} "
                    f"{resource.get('unit_label', 'unité')}/min"
                )
        else:
            lines.append("Aucune ressource externe.")
        byproducts = snapshot.get("byproducts", [])
        if byproducts:
            lines.extend(["", "COPRODUITS"])
            for product in byproducts:
                lines.append(
                    f"• {product.get('display_name', product.get('class_name', 'Coproduit'))} : "
                    f"{self._format_optional(product.get('rate_per_minute'))} "
                    f"{product.get('unit_label', 'unité')}/min"
                )
        warnings = snapshot.get("warnings", [])
        if warnings:
            lines.extend(["", "AVERTISSEMENTS"])
            lines.extend(f"• {warning}" for warning in warnings)
        self.scenario_details.setPlainText("\n".join(lines))

    @staticmethod
    def _format_decimal(value) -> str:
        return format_decimal(value, max_decimals=3)

    @staticmethod
    def _format_optional(value) -> str:
        return "Non déterminée" if value is None else format_decimal(value, max_decimals=3)

    @staticmethod
    def _format_optional_power(value) -> str:
        return "Non déterminée" if value is None else format_power(value)


class FactoriesPage(QWidget):
    """Gestion des usines et de leurs scénarios dans le parc sélectionné."""

    def __init__(
        self,
        factory_service: FactoryService | None = None,
        park_service: ParkService | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("FactoriesPage")
        self.factory_service = factory_service or FactoryService()
        self.park_service = park_service or ParkService()
        self.project: Project | None = None
        self.parks: list[Park] = []
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 28, 30, 25)
        root.setSpacing(17)

        header = QHBoxLayout()
        title_area = QVBoxLayout()
        title = QLabel("Usines industrielles")
        title.setObjectName("PageTitle")
        subtitle = QLabel(
            "Regroupe les calculs de production dans des usines propres à chaque parc."
        )
        subtitle.setObjectName("PageSubtitle")
        subtitle.setWordWrap(True)
        title_area.addWidget(title)
        title_area.addWidget(subtitle)
        header.addLayout(title_area, 1)

        self.create_button = QPushButton("+ Nouvelle usine")
        self.create_button.setObjectName("PrimaryButton")
        self.create_button.setMinimumHeight(40)
        self.create_button.setEnabled(False)
        self.create_button.clicked.connect(self.create_factory)
        header.addWidget(self.create_button)
        root.addLayout(header)

        selection = QHBoxLayout()
        selection.addWidget(QLabel("PARC INDUSTRIEL"))
        self.park_combo = QComboBox()
        self.park_combo.setObjectName("SimulationInput")
        self.park_combo.setMinimumWidth(280)
        self.park_combo.currentIndexChanged.connect(self._on_park_changed)
        selection.addWidget(self.park_combo)
        selection.addStretch()
        root.addLayout(selection)

        self.project_label = QLabel("Aucun projet ouvert")
        self.project_label.setObjectName("ProjectMetadata")
        root.addWidget(self.project_label)

        self.count_label = QLabel("USINES  •  0")
        self.count_label.setObjectName("SectionLabel")
        root.addWidget(self.count_label)

        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("ProjectScrollArea")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.container = QWidget()
        self.list_layout = QVBoxLayout(self.container)
        self.list_layout.setContentsMargins(0, 5, 8, 10)
        self.list_layout.setSpacing(12)
        self.scroll_area.setWidget(self.container)
        root.addWidget(self.scroll_area, 1)

    @property
    def selected_park_id(self) -> UUID | None:
        value = self.park_combo.currentData()
        return UUID(str(value)) if value else None

    def set_project(self, project: Project | None) -> None:
        self.project = project
        self.project_label.setText(
            f"PARTIE ACTIVE  •  {project.name}" if project else "Aucun projet ouvert"
        )
        self.create_button.setEnabled(project is not None)
        self.park_combo.blockSignals(True)
        self.park_combo.clear()
        self.parks = []
        if project is not None:
            try:
                self.parks = self.park_service.get_all_parks(project.id)
            except Exception as error:
                self.park_combo.addItem("Erreur de chargement des parcs", "")
                self.park_combo.blockSignals(False)
                self._show_error("Chargement des parcs impossible", error)
                self.refresh()
                return
        if not self.parks:
            self.park_combo.addItem("Aucun parc disponible", "")
        else:
            for park in self.parks:
                self.park_combo.addItem(park.name, str(park.id))
        self.park_combo.blockSignals(False)
        self.refresh()

    def refresh(self) -> None:
        self._clear_list()
        if self.project is None:
            self.count_label.setText("USINES  •  0")
            self._show_empty(
                "Aucune partie sélectionnée",
                "Ouvre une partie pour consulter ses usines.",
            )
            return
        park_id = self.selected_park_id
        if park_id is None:
            self.count_label.setText("USINES  •  0")
            self._show_empty("Aucun parc disponible", "Crée d'abord un parc industriel.")
            return
        try:
            factories = self.factory_service.list_factories(self.project.id, park_id)
        except Exception as error:
            self.count_label.setText("ERREUR DE CHARGEMENT")
            self._show_error("Chargement des usines impossible", error)
            return
        self.count_label.setText(f"USINES  •  {len(factories)}")
        if not factories:
            self._show_empty(
                "Aucune usine dans ce parc",
                "Enregistre un calcul depuis Simulations ou crée une usine "
                "pour préparer ton organisation.",
            )
            return
        for factory in factories:
            self.list_layout.addWidget(self._create_factory_card(factory))
        self.list_layout.addStretch()

    def _create_factory_card(self, factory: Factory) -> QFrame:
        card = QFrame()
        card.setObjectName("ProjectCard")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)

        icon = QFrame()
        icon.setObjectName("ParkIconBadge")
        icon.setFixedSize(46, 46)
        icon_layout = QVBoxLayout(icon)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_label = QLabel("U")
        icon_label.setObjectName("ParkIconLabel")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_layout.addWidget(icon_label)
        layout.addWidget(icon)

        info = QVBoxLayout()
        name = QLabel(factory.name)
        name.setObjectName("ProjectTitle")
        description = QLabel(factory.description or "Aucune description renseignée.")
        description.setObjectName("ProjectDescription")
        description.setWordWrap(True)
        try:
            scenario_count = len(
                self.factory_service.list_scenarios(
                    factory.project_id,
                    factory.park_id,
                    factory.id,
                )
            )
        except Exception:
            scenario_count = len(factory.scenario_ids)
        meta = QLabel(f"{scenario_count} scénario(s) enregistré(s)")
        meta.setObjectName("ProjectMetadata")
        info.addWidget(name)
        info.addWidget(description)
        info.addWidget(meta)
        layout.addLayout(info, 1)

        actions = QVBoxLayout()
        details = QPushButton("Consulter")
        details.setObjectName("SecondarySmallButton")
        details.clicked.connect(
            lambda checked=False, fid=factory.id: self.show_factory_details(fid)
        )
        rename = QPushButton("Renommer")
        rename.setObjectName("SecondarySmallButton")
        rename.clicked.connect(
            lambda checked=False, fid=factory.id: self.rename_factory(fid)
        )
        archive = QPushButton("Archiver")
        archive.setObjectName("DangerSmallButton")
        archive.clicked.connect(
            lambda checked=False, fid=factory.id: self.archive_factory(fid)
        )
        actions.addWidget(details)
        actions.addWidget(rename)
        actions.addWidget(archive)
        layout.addLayout(actions)
        return card

    def create_factory(self) -> None:
        if self.project is None or self.selected_park_id is None:
            return
        dialog = FactoryDialog(parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            self.factory_service.create_factory(
                self.project.id,
                self.selected_park_id,
                **dialog.get_values(),
            )
            self.refresh()
        except ValueError as error:
            self._show_error("Création impossible", error)
        except Exception as error:
            self._show_error("Création impossible", error)

    def rename_factory(self, factory_id: UUID) -> None:
        if self.project is None or self.selected_park_id is None:
            return
        try:
            factory = self.factory_service.get_factory(
                self.project.id,
                self.selected_park_id,
                factory_id,
            )
        except Exception as error:
            self._show_error("Chargement impossible", error)
            return
        dialog = FactoryDialog(factory, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            self.factory_service.update_factory(
                self.project.id,
                self.selected_park_id,
                factory_id,
                **dialog.get_values(),
            )
            self.refresh()
        except Exception as error:
            self._show_error("Modification impossible", error)

    def archive_factory(self, factory_id: UUID) -> None:
        if self.project is None or self.selected_park_id is None:
            return
        answer = QMessageBox.question(
            self,
            "Archiver cette usine",
            "L'usine et tous ses scénarios seront retirés du parc actif et "
            "conservés dans le centre d'archives.\n\nContinuer ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.factory_service.archive_factory(
                self.project.id,
                self.selected_park_id,
                factory_id,
            )
            self.refresh()
        except Exception as error:
            self._show_error("Archivage impossible", error)

    def show_factory_details(self, factory_id: UUID) -> None:
        if self.project is None or self.selected_park_id is None:
            return
        try:
            factory = self.factory_service.get_factory(
                self.project.id,
                self.selected_park_id,
                factory_id,
            )
            scenarios = self.factory_service.list_scenarios(
                self.project.id,
                self.selected_park_id,
                factory_id,
            )
        except Exception as error:
            self._show_error("Consultation impossible", error)
            return
        ScenarioDetailsDialog(factory, scenarios, self).exec()

    def _on_park_changed(self, _index: int) -> None:
        self.refresh()

    def _clear_list(self) -> None:
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.deleteLater()

    def _show_empty(self, title_text: str, detail: str) -> None:
        card = QFrame()
        card.setObjectName("EmptyProjectsCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(10)
        eyebrow = QLabel("INDUSTRIAL PRODUCTION")
        eyebrow.setObjectName("Eyebrow")
        title = QLabel(title_text)
        title.setObjectName("SectionTitle")
        description = QLabel(detail)
        description.setObjectName("PageSubtitle")
        description.setWordWrap(True)
        layout.addWidget(eyebrow)
        layout.addWidget(title)
        layout.addWidget(description)
        self.list_layout.addWidget(card)
        self.list_layout.addStretch()

    def _show_error(self, title: str, error: Exception) -> None:
        QMessageBox.critical(self, title, str(error))
