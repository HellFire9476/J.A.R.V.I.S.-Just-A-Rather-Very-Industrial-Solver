"""Interface de configuration et de suivi des chaînes Modular Power."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

from PySide6.QtCore import QLocale, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from jarvis.application.services.park_service import ParkService
from jarvis.application.services.project_service import ProjectService
from jarvis.application.services.refined_power_service import RefinedPowerService
from jarvis.domain.entities.project import Project
from jarvis.domain.entities.refined_power import RefinedPowerChainConfiguration
from jarvis.engines.refined_power_engine import RefinedPowerChainResult
from jarvis.presentation.pages.refined_power.optimization_panel import (
    RefinedPowerOptimizationPanel,
)


class RefinedPowerPage(QWidget):
    """Configure les chaînes Refined Power d'un parc et affiche leurs bilans."""

    mods_requested = Signal()

    def __init__(
        self,
        service: RefinedPowerService | None = None,
        project_service: ProjectService | None = None,
        park_service: ParkService | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("RefinedPowerPage")

        self.service = service or RefinedPowerService()
        self.project_service = project_service or ProjectService()
        self.park_service = park_service or ParkService()

        self.project: Project | None = None
        self._preferred_project_id: UUID | None = None
        self._projects_by_id: dict[str, Project] = {}
        self._selected_park_id: UUID | None = None
        self._module_enabled = False
        self._editing_chain_id: UUID | None = None
        self._loading_form = False
        self._catalog = None
        self._catalog_error: str | None = None
        try:
            self._available_locales = self.service.list_locales()
        except Exception:
            self._available_locales = ["fr", "en-US"]
        if not self._available_locales:
            self._available_locales = ["fr", "en-US"]
        self._locale = self._preferred_locale(self._available_locales)

        try:
            self._catalog = self.service.get_catalog()
        except Exception as error:  # affiché dans l'interface si le catalogue est invalide
            self._catalog_error = f"{type(error).__name__}: {error}"

        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 27, 30, 24)
        root.setSpacing(14)

        title = QLabel("Refined Power")
        title.setObjectName("PageTitle")
        subtitle = QLabel(
            "Configurez les installations Modular Power de chaque parc et contrôlez "
            "leurs consommations, leurs flux de vapeur et leur production électrique."
        )
        subtitle.setObjectName("PageSubtitle")
        subtitle.setWordWrap(True)
        root.addWidget(title)
        root.addWidget(subtitle)

        target_panel = QFrame()
        target_panel.setObjectName("RPContextPanel")
        target_layout = QHBoxLayout(target_panel)
        target_layout.setContentsMargins(14, 12, 14, 12)
        target_layout.setSpacing(10)

        project_label = QLabel("PARTIE")
        project_label.setObjectName("SectionLabel")
        target_layout.addWidget(project_label)

        self.project_combo = QComboBox()
        self.project_combo.setObjectName("ModsProjectSelector")
        self.project_combo.setMinimumWidth(180)
        self.project_combo.setMinimumHeight(36)
        self.project_combo.setToolTip(
            "Choisissez la partie Satisfactory qui contient le parc énergétique."
        )
        self.project_combo.currentIndexChanged.connect(self._on_project_changed)
        target_layout.addWidget(self.project_combo)

        park_label = QLabel("PARC")
        park_label.setObjectName("SectionLabel")
        target_layout.addWidget(park_label)

        self.park_combo = QComboBox()
        self.park_combo.setObjectName("ModsParkSelector")
        self.park_combo.setMinimumWidth(180)
        self.park_combo.setMinimumHeight(36)
        self.park_combo.setToolTip(
            "Les installations Refined Power sont enregistrées dans le parc sélectionné."
        )
        self.park_combo.currentIndexChanged.connect(self._on_park_changed)
        target_layout.addWidget(self.park_combo)

        language_label = QLabel("LANGUE DU CATALOGUE")
        language_label.setObjectName("SectionLabel")
        target_layout.addWidget(language_label)

        self.locale_combo = QComboBox()
        self.locale_combo.setObjectName("RPLocaleSelector")
        self.locale_combo.setMinimumWidth(165)
        self.locale_combo.setMinimumHeight(36)
        self.locale_combo.setToolTip(
            "Choisissez la langue des noms de ressources Satisfactory et des équipements "
            "Refined Power. Les identifiants techniques et les calculs restent inchangés. "
            "La langue de l'interface générale reste le français pour le moment."
        )
        for locale in self._available_locales:
            self.locale_combo.addItem(self._locale_label(locale), locale)
        locale_index = self.locale_combo.findData(self._locale)
        self.locale_combo.setCurrentIndex(max(locale_index, 0))
        self.locale_combo.currentIndexChanged.connect(self._on_locale_changed)
        target_layout.addWidget(self.locale_combo)
        target_layout.addStretch(1)

        self.module_state_label = QLabel("AUCUN PARC SÉLECTIONNÉ")
        self.module_state_label.setObjectName("RPModuleStateDisabled")
        target_layout.addWidget(self.module_state_label)

        self.manage_mods_button = QPushButton("Gérer les modules")
        self.manage_mods_button.setObjectName("SecondarySmallButton")
        self.manage_mods_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.manage_mods_button.clicked.connect(self.mods_requested.emit)
        target_layout.addWidget(self.manage_mods_button)
        root.addWidget(target_panel)

        self.status_label = QLabel()
        self.status_label.setObjectName("RPStatus")
        self.status_label.setWordWrap(True)
        root.addWidget(self.status_label)

        self.content_scroll = QScrollArea()
        self.content_scroll.setObjectName("RPScrollArea")
        self.content_scroll.setWidgetResizable(True)
        self.content_scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        content.setObjectName("RPContent")
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(0, 3, 4, 8)
        content_layout.setSpacing(14)

        self._build_chain_panel(content_layout)
        self._build_detail_panel(content_layout)

        self.content_scroll.setWidget(content)
        root.addWidget(self.content_scroll, 1)

    def _build_chain_panel(self, parent_layout: QHBoxLayout) -> None:
        panel = QFrame()
        panel.setObjectName("RPPanel")
        panel.setMinimumWidth(245)
        panel.setMaximumWidth(310)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 15, 14, 14)
        layout.setSpacing(10)

        heading = QLabel("INSTALLATIONS")
        heading.setObjectName("SectionLabel")
        layout.addWidget(heading)

        self.new_chain_button = QPushButton("+ Nouvelle chaîne")
        self.new_chain_button.setObjectName("PrimarySmallButton")
        self.new_chain_button.setMinimumHeight(36)
        self.new_chain_button.clicked.connect(self._start_new_chain)
        layout.addWidget(self.new_chain_button)

        self.chain_list = QListWidget()
        self.chain_list.setObjectName("RPChainList")
        self.chain_list.setToolTip(
            "Sélectionnez une installation pour consulter ou modifier sa configuration."
        )
        self.chain_list.currentItemChanged.connect(self._on_chain_selected)
        layout.addWidget(self.chain_list, 1)

        self.chain_count_label = QLabel("0 chaîne enregistrée")
        self.chain_count_label.setObjectName("ProjectMetadata")
        layout.addWidget(self.chain_count_label)
        parent_layout.addWidget(panel, 0)

    def _build_detail_panel(self, parent_layout: QHBoxLayout) -> None:
        right = QWidget()
        right.setObjectName("RPDetails")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(13)

        self.detail_tabs = QTabWidget()
        self.detail_tabs.setObjectName("RPTabs")
        configuration_tab = QWidget()
        configuration_layout = QVBoxLayout(configuration_tab)
        configuration_layout.setContentsMargins(0, 0, 0, 0)
        configuration_layout.setSpacing(13)

        editor = QFrame()
        editor.setObjectName("RPPanel")
        editor_layout = QVBoxLayout(editor)
        editor_layout.setContentsMargins(17, 15, 17, 15)
        editor_layout.setSpacing(12)

        editor_heading = QHBoxLayout()
        editor_title = QLabel("CONFIGURATION DE LA CHAÎNE")
        editor_title.setObjectName("SectionLabel")
        editor_heading.addWidget(editor_title)
        editor_heading.addStretch(1)
        self.editor_mode_label = QLabel("NOUVELLE INSTALLATION")
        self.editor_mode_label.setObjectName("RPModeLabel")
        editor_heading.addWidget(self.editor_mode_label)
        editor_layout.addLayout(editor_heading)

        form = QGridLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(9)

        self.chain_name_input = QLineEdit()
        self.chain_name_input.setObjectName("RPInput")
        self.chain_name_input.setPlaceholderText("Ex. Centrale charbon Nord")
        self.chain_name_input.setMaxLength(80)
        form.addWidget(self._field_label("NOM DE L'INSTALLATION"), 0, 0)
        form.addWidget(self.chain_name_input, 0, 1, 1, 3)

        self.heater_combo = self._create_combo("RPHeaterSelector")
        self.fuel_combo = self._create_combo("RPFuelSelector")
        self.boiler_combo = self._create_combo("RPBoilerSelector")
        self.turbine_combo = self._create_combo("RPTurbineSelector")
        self.generator_combo = self._create_combo("RPGeneratorSelector")

        self.boiler_count_spin = self._create_spin("RPBoilerCount", 1, minimum=1)
        self.turbine_count_spin = self._create_spin("RPTurbineCount", 1)
        self.generator_count_spin = self._create_spin("RPGeneratorCount", 1)
        self.chimney_count_spin = self._create_spin("RPChimneyCount", 1)
        self.cooling_tower_count_spin = self._create_spin("RPCoolingTowerCount", 1)

        self._add_form_pair(form, 1, "CHAUFFAGE", self.heater_combo, "COMBUSTIBLE", self.fuel_combo)
        self._add_form_pair(
            form, 2, "CHAUDIÈRE", self.boiler_combo, "NOMBRE", self.boiler_count_spin
        )
        self._add_form_pair(
            form, 3, "TURBINE", self.turbine_combo, "NOMBRE", self.turbine_count_spin
        )
        self._add_form_pair(
            form, 4, "GÉNÉRATEUR", self.generator_combo, "NOMBRE", self.generator_count_spin
        )
        self._add_form_pair(
            form,
            5,
            "CHEMINÉES CO₂",
            self.chimney_count_spin,
            "TOURS DE REFROIDISSEMENT",
            self.cooling_tower_count_spin,
        )
        editor_layout.addLayout(form)

        self.heater_combo.currentIndexChanged.connect(self._on_heater_changed)
        self.turbine_combo.currentIndexChanged.connect(self._on_turbine_changed)

        actions = QHBoxLayout()
        actions.addStretch(1)

        self.duplicate_button = QPushButton("Dupliquer")
        self.duplicate_button.setObjectName("SecondarySmallButton")
        self.duplicate_button.clicked.connect(self._duplicate_chain)
        actions.addWidget(self.duplicate_button)

        self.delete_button = QPushButton("Supprimer")
        self.delete_button.setObjectName("DangerSmallButton")
        self.delete_button.clicked.connect(self._delete_chain)
        actions.addWidget(self.delete_button)

        self.save_button = QPushButton("Enregistrer la chaîne")
        self.save_button.setObjectName("PrimarySmallButton")
        self.save_button.clicked.connect(self._save_chain)
        actions.addWidget(self.save_button)
        editor_layout.addLayout(actions)
        configuration_layout.addWidget(editor)

        results = QFrame()
        results.setObjectName("RPPanel")
        results_layout = QVBoxLayout(results)
        results_layout.setContentsMargins(17, 15, 17, 15)
        results_layout.setSpacing(11)

        results_title = QLabel("BILAN ÉNERGÉTIQUE")
        results_title.setObjectName("SectionLabel")
        results_layout.addWidget(results_title)

        metrics = QGridLayout()
        metrics.setHorizontalSpacing(9)
        metrics.setVerticalSpacing(9)
        self.power_value = self._add_metric(metrics, 0, 0, "PUISSANCE PRODUITE", "—", "MW")
        self.fuel_value = self._add_metric(metrics, 0, 1, "COMBUSTIBLE", "—", "par minute")
        self.water_value = self._add_metric(metrics, 1, 0, "EAU", "—", "m³/min")
        self.rpm_value = self._add_metric(metrics, 1, 1, "RÉGIME TURBINE", "—", "RPM")
        results_layout.addLayout(metrics)

        self.result_state_label = QLabel("AUCUN CALCUL")
        self.result_state_label.setObjectName("RPResultState")
        results_layout.addWidget(self.result_state_label)

        self.flow_details_label = QLabel(
            "Sélectionnez une chaîne enregistrée ou créez une installation pour afficher les flux."
        )
        self.flow_details_label.setObjectName("RPFlowDetails")
        self.flow_details_label.setWordWrap(True)
        results_layout.addWidget(self.flow_details_label)

        self.warnings_label = QLabel()
        self.warnings_label.setObjectName("RPWarnings")
        self.warnings_label.setWordWrap(True)
        results_layout.addWidget(self.warnings_label)

        configuration_layout.addWidget(results)
        configuration_layout.addStretch(1)

        self.optimization_panel = RefinedPowerOptimizationPanel(self.service, self.detail_tabs)
        self.optimization_panel.set_locale(self._locale)
        self.optimization_panel.apply_requested.connect(self._apply_optimization)
        self.detail_tabs.addTab(configuration_tab, "Installations")
        self.detail_tabs.addTab(self.optimization_panel, "Équilibrage automatique")
        right_layout.addWidget(self.detail_tabs, 1)
        parent_layout.addWidget(right, 1)

        self._populate_catalog_controls()
        self._connect_preview_signals()
        self._set_form_enabled(False)

    @staticmethod
    def _field_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("RPFieldLabel")
        return label

    @staticmethod
    def _create_combo(object_name: str) -> QComboBox:
        combo = QComboBox()
        combo.setObjectName(object_name)
        combo.setMinimumHeight(34)
        return combo

    @staticmethod
    def _create_spin(
        object_name: str,
        value: int,
        minimum: int = 0,
    ) -> QSpinBox:
        spin = QSpinBox()
        spin.setObjectName(object_name)
        spin.setRange(minimum, 10000)
        spin.setValue(value)
        spin.setMinimumHeight(34)
        return spin

    def _add_form_pair(
        self,
        layout: QGridLayout,
        row: int,
        first_label: str,
        first_widget: QWidget,
        second_label: str,
        second_widget: QWidget,
    ) -> None:
        layout.addWidget(self._field_label(first_label), row, 0)
        layout.addWidget(first_widget, row, 1)
        layout.addWidget(self._field_label(second_label), row, 2)
        layout.addWidget(second_widget, row, 3)

    @staticmethod
    def _add_metric(
        layout: QGridLayout,
        row: int,
        column: int,
        label_text: str,
        value_text: str,
        unit_text: str,
    ) -> QLabel:
        card = QFrame()
        card.setObjectName("RPMetricCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 10, 12, 10)
        card_layout.setSpacing(3)

        label = QLabel(label_text)
        label.setObjectName("SimulationMetricLabel")
        value = QLabel(value_text)
        value.setObjectName("SimulationMetricValue")
        unit = QLabel(unit_text)
        unit.setObjectName("ProjectMetadata")

        card_layout.addWidget(label)
        card_layout.addWidget(value)
        card_layout.addWidget(unit)
        layout.addWidget(card, row, column)
        return value

    @staticmethod
    def _preferred_locale(locales: list[str]) -> str:
        normalized = {locale.casefold(): locale for locale in locales}
        for preferred in ("fr", "en-US"):
            exact = normalized.get(preferred.casefold())
            if exact:
                return exact
            language = preferred.split("-", 1)[0].casefold()
            regional_match = next(
                (
                    locale
                    for locale in locales
                    if locale.casefold().split("-", 1)[0] == language
                ),
                None,
            )
            if regional_match:
                return regional_match
        return locales[0]

    @staticmethod
    def _locale_label(locale: str) -> str:
        native_name = QLocale(locale).nativeLanguageName().strip()
        if not native_name:
            return locale
        return f"{native_name[:1].upper()}{native_name[1:]} ({locale})"

    def _on_locale_changed(self, _index: int) -> None:
        locale = self.locale_combo.currentData()
        if not locale or locale == self._locale:
            return

        self._locale = str(locale)
        selected = {
            "heater": self.heater_combo.currentData(),
            "fuel": self.fuel_combo.currentData(),
            "boiler": self.boiler_combo.currentData(),
            "turbine": self.turbine_combo.currentData(),
            "generator": self.generator_combo.currentData(),
        }
        self._loading_form = True
        self._populate_catalog_controls(selected)
        self._loading_form = False
        self.optimization_panel.set_locale(self._locale)
        self._preview_form()

    def _populate_catalog_controls(self, preferred: dict[str, str | None] | None = None) -> None:
        if self._catalog is None:
            self.status_label.setText(
                f"Catalogue Refined Power indisponible : {self._catalog_error or 'erreur inconnue'}"
            )
            return

        preferred = preferred or {}
        selected_heater = preferred.get("heater", self.heater_combo.currentData())
        selected_fuel = preferred.get("fuel", self.fuel_combo.currentData())
        selected_boiler = preferred.get("boiler", self.boiler_combo.currentData())
        selected_turbine = preferred.get("turbine", self.turbine_combo.currentData())
        selected_generator = preferred.get("generator", self.generator_combo.currentData())

        self.heater_combo.clear()
        for heater in self._catalog.heaters:
            self.heater_combo.addItem(
                self.service.get_profile_display_name(heater, self._locale),
                heater.heater_id,
            )
        self._set_combo_value(self.heater_combo, selected_heater)

        self.boiler_combo.clear()
        for boiler in self._catalog.boilers:
            self.boiler_combo.addItem(
                self.service.get_profile_display_name(boiler, self._locale),
                boiler.boiler_id,
            )
        self._set_combo_value(self.boiler_combo, selected_boiler)

        self.turbine_combo.clear()
        for turbine in self._catalog.turbines:
            self.turbine_combo.addItem(
                self.service.get_profile_display_name(turbine, self._locale),
                turbine.turbine_id,
            )
        self._set_combo_value(self.turbine_combo, selected_turbine)

        self._populate_generators(selected_generator)
        self._populate_fuels(selected_fuel)

    def _populate_generators(self, preferred_generator_id: str | None = None) -> None:
        if self._catalog is None:
            return
        turbine_id = self.turbine_combo.currentData()
        supported_ids = {
            item.generator_id
            for item in self._catalog.generator_performance
            if item.turbine_id == turbine_id
        }
        self.generator_combo.blockSignals(True)
        self.generator_combo.clear()
        for generator in self._catalog.generators:
            if generator.generator_id in supported_ids:
                self.generator_combo.addItem(
                    self.service.get_profile_display_name(generator, self._locale),
                    generator.generator_id,
                )
        selected = self.generator_combo.findData(preferred_generator_id)
        if selected >= 0:
            self.generator_combo.setCurrentIndex(selected)
        self.generator_combo.blockSignals(False)

    def _connect_preview_signals(self) -> None:
        for combo in (
            self.heater_combo,
            self.fuel_combo,
            self.boiler_combo,
            self.turbine_combo,
            self.generator_combo,
        ):
            combo.currentIndexChanged.connect(self._preview_form)
        for spin in (
            self.boiler_count_spin,
            self.turbine_count_spin,
            self.generator_count_spin,
            self.chimney_count_spin,
            self.cooling_tower_count_spin,
        ):
            spin.valueChanged.connect(self._preview_form)
        self.chain_name_input.textChanged.connect(self._preview_form)

    def _populate_fuels(self, preferred_fuel_id: str | None = None) -> None:
        if self._catalog is None:
            return
        heater_id = self.heater_combo.currentData()
        self.fuel_combo.blockSignals(True)
        self.fuel_combo.clear()
        fuels = [fuel for fuel in self._catalog.fuels if fuel.heater_id == heater_id]
        for fuel in fuels:
            label = (
                f"{self.service.get_profile_display_name(fuel, self._locale)} · "
                f"{fuel.operating_temperature_c} °C"
            )
            self.fuel_combo.addItem(label, fuel.fuel_id)
        index = self.fuel_combo.findData(preferred_fuel_id)
        if index >= 0:
            self.fuel_combo.setCurrentIndex(index)
        self.fuel_combo.blockSignals(False)

    @property
    def selected_park_id(self) -> UUID | None:
        """Identifiant du parc actuellement affiché."""

        return self._selected_park_id

    def set_project(self, project: Project | None) -> None:
        """Préselectionne la partie active sans imposer ce contexte à la page."""

        self._preferred_project_id = project.id if project else None
        self.refresh()

    def refresh(self) -> None:
        """Recharge les parties, parcs, chaînes et états du module."""

        current_project_id = self.project_combo.currentData()
        project_id = (
            str(self._preferred_project_id)
            if self._preferred_project_id is not None
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
            self.status_label.setText(f"Impossible de charger les parties : {error}")

        self._projects_by_id = {str(item.id): item for item in projects}
        for project in projects:
            self.project_combo.addItem(project.name, str(project.id))

        if projects:
            self.project_combo.setEnabled(True)
            selected = self.project_combo.findData(project_id)
            if selected < 0:
                selected = 0
            self.project_combo.setCurrentIndex(selected)
            self.project = self._projects_by_id[self.project_combo.currentData()]
        else:
            self.project_combo.addItem("Aucune partie enregistrée", None)
            self.project_combo.setEnabled(False)
            self.project = None

        self.project_combo.blockSignals(False)
        self._refresh_parks(previous_park_id)

    def _refresh_parks(self, previous_park_id: UUID | None = None) -> None:
        self.park_combo.blockSignals(True)
        self.park_combo.clear()
        self._selected_park_id = None
        self._module_enabled = False

        if self.project is None:
            self.park_combo.addItem("Sélectionnez une partie", None)
            self.park_combo.setEnabled(False)
            self.project_status_text(
                "Aucune partie enregistrée. Créez une partie et un parc pour configurer "
                "une installation Refined Power."
            )
            self.park_combo.blockSignals(False)
            self._render_chains()
            return

        try:
            parks = self.park_service.get_all_parks(self.project.id)
        except Exception as error:
            parks = []
            self.project_status_text(f"Impossible de charger les parcs : {error}")

        if not parks:
            self.park_combo.addItem("Aucun parc dans cette partie", None)
            self.park_combo.setEnabled(False)
            self.manage_mods_button.setEnabled(False)
            self.project_status_text(
                f"Partie sélectionnée : {self.project.name}. Créez un parc pour y "
                "configurer vos installations énergétiques."
            )
            self.park_combo.blockSignals(False)
            self._render_chains()
            return

        self.park_combo.setEnabled(True)
        for park in parks:
            self.park_combo.addItem(park.name, str(park.id))
        selected = self.park_combo.findData(
            str(previous_park_id) if previous_park_id else None
        )
        if selected < 0:
            selected = 0
        self.park_combo.setCurrentIndex(selected)
        self._selected_park_id = UUID(self.park_combo.currentData())
        self.park_combo.blockSignals(False)
        self._load_selected_park()

    def project_status_text(self, message: str) -> None:
        self.status_label.setText(message)
        self.module_state_label.setText("PARC NON SÉLECTIONNÉ")
        self.module_state_label.setObjectName("RPModuleStateDisabled")
        self.module_state_label.style().unpolish(self.module_state_label)
        self.module_state_label.style().polish(self.module_state_label)
        self.manage_mods_button.setEnabled(False)
        self._set_form_enabled(False)

    def _on_project_changed(self, index: int) -> None:
        if index < 0:
            return
        project_id = self.project_combo.itemData(index)
        self.project = self._projects_by_id.get(project_id)
        self._refresh_parks()

    def _on_park_changed(self, index: int) -> None:
        park_id = self.park_combo.itemData(index) if index >= 0 else None
        self._selected_park_id = UUID(park_id) if park_id else None
        self._load_selected_park()

    def _load_selected_park(self) -> None:
        self._module_enabled = False
        if self.project is None or self._selected_park_id is None:
            self._render_chains()
            return

        try:
            park = self.park_service.get_park(self.project.id, self._selected_park_id)
        except Exception as error:
            self.project_status_text(f"Impossible de lire le parc sélectionné : {error}")
            self._render_chains()
            return

        installation = park.mods.get(RefinedPowerService.MOD_ID)
        self._module_enabled = bool(installation and installation.enabled)
        if self._module_enabled:
            self.status_label.setText(
                f"Refined Power est actif dans « {park.name} ». Les modifications "
                "seront enregistrées uniquement dans ce parc."
            )
            self.module_state_label.setText("REFINED POWER ACTIF")
            self.module_state_label.setObjectName("RPModuleStateEnabled")
        else:
            self.status_label.setText(
                f"Refined Power est désactivé dans « {park.name} ». Les chaînes déjà "
                "enregistrées restent consultables, mais leur modification et leur "
                "calcul nécessitent l'activation du module."
            )
            self.module_state_label.setText("MODULE DÉSACTIVÉ")
            self.module_state_label.setObjectName("RPModuleStateDisabled")
        self.module_state_label.style().unpolish(self.module_state_label)
        self.module_state_label.style().polish(self.module_state_label)
        self.manage_mods_button.setEnabled(True)
        if self._catalog_error:
            self.status_label.setText(
                f"Catalogue Refined Power indisponible : {self._catalog_error}"
            )
        self._render_chains()

    def _render_chains(self, selected_chain_id: UUID | None = None) -> None:
        self.chain_list.blockSignals(True)
        self.chain_list.clear()
        chains = ()
        if self.project is not None and self._selected_park_id is not None:
            try:
                chains = self.service.list_chains(self.project.id, self._selected_park_id)
            except Exception as error:
                self.status_label.setText(f"Impossible de charger les chaînes : {error}")

        for chain in chains:
            item = QListWidgetItem(chain.name)
            item.setData(Qt.ItemDataRole.UserRole, str(chain.chain_id))
            self.chain_list.addItem(item)

        self.chain_count_label.setText(
            f"{len(chains)} chaîne(s) enregistrée(s) dans ce parc"
        )
        self.chain_list.blockSignals(False)
        self.optimization_panel.set_context(
            self.project.id if self.project is not None else None,
            self._selected_park_id,
            self._module_enabled,
            tuple(chains),
        )

        enabled = (
            self._target_selected()
            and self._module_enabled
            and self._catalog is not None
        )
        self.new_chain_button.setEnabled(enabled)
        if chains:
            selected_item = None
            if selected_chain_id is not None:
                for row in range(self.chain_list.count()):
                    item = self.chain_list.item(row)
                    if item.data(Qt.ItemDataRole.UserRole) == str(selected_chain_id):
                        selected_item = item
                        break
            if selected_item is not None:
                self.chain_list.setCurrentItem(selected_item)
            else:
                self.chain_list.setCurrentRow(0)
        else:
            self._start_new_chain()
            self._reset_result()
            self._set_form_enabled(enabled)

    def _target_selected(self) -> bool:
        return self.project is not None and self._selected_park_id is not None

    def _on_chain_selected(
        self,
        current: QListWidgetItem | None,
        previous: QListWidgetItem | None,
    ) -> None:
        del previous
        if current is None:
            return
        try:
            chain_id = UUID(current.data(Qt.ItemDataRole.UserRole))
            chain = next(
                item for item in self.service.list_chains(
                    self.project.id,
                    self._selected_park_id,
                )
                if item.chain_id == chain_id
            )
        except Exception as error:
            self._show_error("Lecture de la chaîne impossible", error)
            return
        self._populate_form(chain)
        self.optimization_panel.select_reference_chain(chain_id)
        self._calculate_selected_chain(chain_id)

    def _start_new_chain(self) -> None:
        self.chain_list.blockSignals(True)
        self.chain_list.clearSelection()
        self.chain_list.setCurrentRow(-1)
        self.chain_list.blockSignals(False)
        self._editing_chain_id = None
        self.editor_mode_label.setText("NOUVELLE INSTALLATION")
        self.chain_name_input.setText("")
        self.boiler_count_spin.setValue(1)
        self.turbine_count_spin.setValue(1)
        self.generator_count_spin.setValue(1)
        self.chimney_count_spin.setValue(1)
        self.cooling_tower_count_spin.setValue(1)
        self._populate_catalog_controls()
        self._set_form_enabled(
            self._target_selected()
            and self._module_enabled
            and self._catalog is not None
        )
        self.duplicate_button.setEnabled(False)
        self.delete_button.setEnabled(False)
        self.save_button.setText("Enregistrer la chaîne")
        self._reset_result()

    def _populate_form(self, chain: RefinedPowerChainConfiguration) -> None:
        self._loading_form = True
        self._editing_chain_id = chain.chain_id
        self.editor_mode_label.setText("MODIFICATION D'UNE INSTALLATION")
        self.chain_name_input.setText(chain.name)
        self._set_combo_value(self.heater_combo, chain.heater_id)
        self._populate_fuels(chain.fuel_id)
        self._set_combo_value(self.fuel_combo, chain.fuel_id)
        self._set_combo_value(self.boiler_combo, chain.boiler_id)
        self._set_combo_value(self.turbine_combo, chain.turbine_id)
        self._populate_generators(chain.generator_id)
        self._set_combo_value(self.generator_combo, chain.generator_id)
        self.boiler_count_spin.setValue(chain.boiler_count)
        self.turbine_count_spin.setValue(chain.turbine_count)
        self.generator_count_spin.setValue(chain.generator_count)
        self.chimney_count_spin.setValue(chain.co2_chimney_count)
        self.cooling_tower_count_spin.setValue(chain.steam_cooling_tower_count)
        self._loading_form = False
        self._set_form_enabled(
            self._target_selected()
            and self._module_enabled
            and self._catalog is not None
        )
        self.duplicate_button.setEnabled(self._module_enabled)
        self.delete_button.setEnabled(self._module_enabled)
        self.save_button.setText("Enregistrer les modifications")

    def _on_heater_changed(self, index: int) -> None:
        if self._loading_form or index < 0:
            return
        self._loading_form = True
        self._populate_fuels()
        self._loading_form = False
        self._preview_form()

    def _on_turbine_changed(self, index: int) -> None:
        if self._loading_form or index < 0:
            return
        self._loading_form = True
        self._populate_generators()
        self._loading_form = False
        self._preview_form()

    @staticmethod
    def _set_combo_value(combo: QComboBox, value: str) -> None:
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    def _set_form_enabled(self, enabled: bool) -> None:
        for widget in (
            self.chain_name_input,
            self.heater_combo,
            self.fuel_combo,
            self.boiler_combo,
            self.boiler_count_spin,
            self.turbine_combo,
            self.turbine_count_spin,
            self.generator_combo,
            self.generator_count_spin,
            self.chimney_count_spin,
            self.cooling_tower_count_spin,
            self.save_button,
        ):
            widget.setEnabled(enabled)
        if not enabled:
            self.duplicate_button.setEnabled(False)
            self.delete_button.setEnabled(False)
        elif self._editing_chain_id is None:
            self.duplicate_button.setEnabled(False)
            self.delete_button.setEnabled(False)

    def _build_form_configuration(self) -> RefinedPowerChainConfiguration:
        values = {
            "name": self.chain_name_input.text().strip(),
            "heater_id": self.heater_combo.currentData(),
            "fuel_id": self.fuel_combo.currentData(),
            "boiler_id": self.boiler_combo.currentData(),
            "boiler_count": self.boiler_count_spin.value(),
            "turbine_id": self.turbine_combo.currentData(),
            "turbine_count": self.turbine_count_spin.value(),
            "generator_id": self.generator_combo.currentData(),
            "generator_count": self.generator_count_spin.value(),
            "co2_chimney_count": self.chimney_count_spin.value(),
            "steam_cooling_tower_count": self.cooling_tower_count_spin.value(),
        }
        if self._editing_chain_id is not None:
            values["chain_id"] = self._editing_chain_id
        return RefinedPowerChainConfiguration.model_validate(values)

    def _preview_form(self, *_args) -> None:
        """Actualise le bilan sans enregistrer les modifications du formulaire."""

        if (
            self._loading_form
            or not self._target_selected()
            or not self._module_enabled
            or self._catalog is None
            or not self.chain_name_input.text().strip()
        ):
            return
        try:
            configuration = self._build_form_configuration()
            result = self.service.preview_configuration(configuration, self._locale)
        except Exception as error:
            self._reset_result()
            self.result_state_label.setText("APERÇU INCOMPLET")
            self.result_state_label.setObjectName("RPResultStateWarning")
            self.result_state_label.style().unpolish(self.result_state_label)
            self.result_state_label.style().polish(self.result_state_label)
            self.flow_details_label.setText(
                f"Configuration à corriger : {error}"
            )
            self.warnings_label.clear()
            return
        self._display_result(result, preview=True)

    def _save_chain(self) -> None:
        if not self._target_selected() or not self._module_enabled:
            return
        if not self.chain_name_input.text().strip():
            QMessageBox.warning(self, "Nom manquant", "Donnez un nom à cette installation.")
            self.chain_name_input.setFocus()
            return

        try:
            configuration = self._build_form_configuration()
            # Valide les compatibilités et les flux avant toute écriture.
            self.service.preview_configuration(configuration, self._locale)
            if self._editing_chain_id is None:
                saved = self.service.create_chain(
                    self.project.id,
                    self._selected_park_id,
                    configuration,
                )
            else:
                saved = self.service.update_chain(
                    self.project.id,
                    self._selected_park_id,
                    self._editing_chain_id,
                    configuration,
                )
        except Exception as error:
            self._show_error("Enregistrement impossible", error)
            return

        self._render_chains(saved.chain_id)
        self.status_label.setText(
            f"Installation « {saved.name} » enregistrée dans le parc."
        )

    def _apply_optimization(self, configuration: RefinedPowerChainConfiguration) -> None:
        """Persiste une proposition uniquement après confirmation explicite."""

        if not self._target_selected() or not self._module_enabled:
            return

        try:
            existing_chains = self.service.list_chains(
                self.project.id,
                self._selected_park_id,
            )
            is_update = any(
                item.chain_id == configuration.chain_id for item in existing_chains
            )
        except Exception as error:
            self._show_error("Lecture des installations impossible", error)
            return

        action = "remplacer la configuration" if is_update else "créer une nouvelle chaîne"
        target_note = ""
        solution = self.optimization_panel.solution
        if solution is not None and solution.target_reached is False:
            target_note = (
                "\n\nAttention : la puissance cible n'a pas été atteinte. "
                "La proposition correspond à la meilleure solution réalisable trouvée."
            )
        answer = QMessageBox.question(
            self,
            "Appliquer l'équilibrage",
            f"Voulez-vous {action} « {configuration.name} » dans ce parc ?"
            f"{target_note}\n\nCette opération modifiera les données enregistrées du parc.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            if is_update:
                saved = self.service.update_chain(
                    self.project.id,
                    self._selected_park_id,
                    configuration.chain_id,
                    configuration,
                )
            else:
                saved = self.service.create_chain(
                    self.project.id,
                    self._selected_park_id,
                    configuration,
                )
        except Exception as error:
            self._show_error("Application de l'équilibrage impossible", error)
            return

        self._render_chains(saved.chain_id)
        self.detail_tabs.setCurrentIndex(0)
        self.status_label.setText(
            f"Proposition appliquée : « {saved.name} » a été enregistrée dans ce parc."
        )

    def _duplicate_chain(self) -> None:
        if (
            not self._target_selected()
            or not self._module_enabled
            or self._editing_chain_id is None
        ):
            return
        try:
            source = next(
                item for item in self.service.list_chains(
                    self.project.id,
                    self._selected_park_id,
                )
                if item.chain_id == self._editing_chain_id
            )
            existing_names = {
                item.name.casefold()
                for item in self.service.list_chains(
                    self.project.id,
                    self._selected_park_id,
                )
            }
            copy_suffix = " (copie)"
            base_name = f"{source.name[:80 - len(copy_suffix)]}{copy_suffix}"
            name = base_name
            suffix = 2
            while name.casefold() in existing_names:
                suffix_text = f" {suffix}"
                name = (
                    f"{base_name[:80 - len(suffix_text)]}{suffix_text}"
                )
                suffix += 1
            duplicate_data = source.model_dump(mode="python")
            duplicate_data.update({"chain_id": uuid4(), "name": name})
            duplicate = RefinedPowerChainConfiguration.model_validate(
                duplicate_data
            )
            saved = self.service.create_chain(
                self.project.id,
                self._selected_park_id,
                duplicate,
            )
        except Exception as error:
            self._show_error("Duplication impossible", error)
            return
        self._render_chains(saved.chain_id)

    def _delete_chain(self) -> None:
        if (
            not self._target_selected()
            or not self._module_enabled
            or self._editing_chain_id is None
        ):
            return
        answer = QMessageBox.question(
            self,
            "Supprimer l'installation",
            "Supprimer définitivement cette chaîne de ce parc ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.service.delete_chain(
                self.project.id,
                self._selected_park_id,
                self._editing_chain_id,
            )
        except Exception as error:
            self._show_error("Suppression impossible", error)
            return
        self._render_chains()

    def _calculate_selected_chain(self, chain_id: UUID) -> None:
        self._reset_result()
        if not self._module_enabled:
            self.result_state_label.setText("CALCUL INDISPONIBLE · MODULE DÉSACTIVÉ")
            self.flow_details_label.setText(
                "La configuration est conservée. Activez Refined Power dans "
                "Mods & extensions pour relancer les calculs."
            )
            return
        try:
            result = self.service.calculate_chain(
                self.project.id,
                self._selected_park_id,
                chain_id,
                self._locale,
            )
        except Exception as error:
            self._show_error("Calcul impossible", error)
            return
        self._display_result(result)

    def _display_result(
        self,
        result: RefinedPowerChainResult,
        preview: bool = False,
    ) -> None:
        self.power_value.setText(f"{self._format_decimal(result.estimated_power_mw)} MW")
        self.fuel_value.setText(
            f"{self._format_decimal(result.fuel_consumption_per_minute)} "
            f"{result.fuel_unit}"
        )
        self.water_value.setText(
            f"{self._format_decimal(result.water_consumption_m3_per_minute)} m³/min"
        )
        self.rpm_value.setText(f"{self._format_decimal(result.turbine_rpm)} RPM")

        balance_label = (
            "FLUX ÉQUILIBRÉS" if result.sustainable else "ÉQUILIBRE À CORRIGER"
        )
        self.result_state_label.setText(
            f"APERÇU NON ENREGISTRÉ · {balance_label}"
            if preview
            else balance_label
        )
        self.result_state_label.setObjectName(
            "RPResultStateGood" if result.sustainable else "RPResultStateWarning"
        )
        self.result_state_label.style().unpolish(self.result_state_label)
        self.result_state_label.style().polish(self.result_state_label)

        estimate_note = (
            "Puissance estimée : la chaîne fonctionne à régime vapeur partiel."
            if result.power_is_estimated
            else "Puissance nominale documentée pour la combinaison sélectionnée."
        )
        flow_lines = [
            f"Vapeur haute pression produite : "
            f"{self._format_decimal(result.high_pressure_steam_generated_m3_per_minute)} m³/min",
            f"Vapeur haute pression utilisée : "
            f"{self._format_decimal(result.high_pressure_steam_used_m3_per_minute)} m³/min",
            f"Surplus haute pression : "
            f"{self._format_decimal(result.high_pressure_steam_surplus_m3_per_minute)} m³/min",
            f"Vapeur basse pression : "
            f"{self._format_decimal(result.low_pressure_steam_output_m3_per_minute)} m³/min "
            f"(évacuation "
            f"{self._format_decimal(result.low_pressure_steam_vent_capacity_m3_per_minute)} "
            f"m³/min, débordement "
            f"{self._format_decimal(result.low_pressure_steam_overflow_m3_per_minute)} "
            f"m³/min)",
            f"CO₂ : {self._format_decimal(result.co2_output_m3_per_minute)} m³/min "
            f"(évacuation {self._format_decimal(result.co2_vent_capacity_m3_per_minute)} m³/min, "
            f"débordement {self._format_decimal(result.co2_overflow_m3_per_minute)} m³/min)",
            f"Générateurs raccordés : {result.connected_generator_count} · "
            f"sans turbine : {result.idle_generator_count}",
            estimate_note,
        ]
        if result.byproducts:
            flow_lines.append(
                "Sous-produits : "
                + ", ".join(
                    f"{item.display_name} {self._format_decimal(item.rate_per_minute)} "
                    f"{item.unit}"
                    for item in result.byproducts
                )
            )
        self.flow_details_label.setText("\n".join(flow_lines))

        if result.warnings:
            self.warnings_label.setText(
                "POINTS À SURVEILLER\n" + "\n".join(f"•  {warning}" for warning in result.warnings)
            )
        else:
            self.warnings_label.setText("Aucune anomalie détectée sur les flux configurés.")

    def _reset_result(self) -> None:
        for value in (self.power_value, self.fuel_value, self.water_value, self.rpm_value):
            value.setText("—")
        self.result_state_label.setText("AUCUN CALCUL")
        self.result_state_label.setObjectName("RPResultState")
        self.result_state_label.style().unpolish(self.result_state_label)
        self.result_state_label.style().polish(self.result_state_label)
        self.flow_details_label.setText(
            "Sélectionnez une chaîne enregistrée ou créez une installation pour afficher les flux."
        )
        self.warnings_label.clear()

    @staticmethod
    def _format_decimal(value: Decimal) -> str:
        formatted = f"{value:,.2f}"
        return formatted.replace(",", " ").replace(".", ",")

    def _show_error(self, title: str, error: Exception) -> None:
        QMessageBox.critical(self, title, f"{type(error).__name__} : {error}")
