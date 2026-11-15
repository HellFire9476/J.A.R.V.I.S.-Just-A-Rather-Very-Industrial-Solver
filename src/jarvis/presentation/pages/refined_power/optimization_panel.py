"""Panneau graphique de prévisualisation de l'équilibrage Refined Power."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from uuid import UUID

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from jarvis.application.services.refined_power_service import RefinedPowerService
from jarvis.domain.entities.refined_power import RefinedPowerChainConfiguration
from jarvis.domain.entities.refined_power_optimization import (
    RefinedPowerOptimizationLimits,
    RefinedPowerOptimizationRequest,
    RefinedPowerOptimizationSolution,
)


class RefinedPowerOptimizationPanel(QWidget):
    """Configure et prévisualise une optimisation sans sauvegarder la chaîne."""

    apply_requested = Signal(object)

    def __init__(
        self,
        service: RefinedPowerService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.service = service
        self.locale = "fr"
        self.catalog = None
        self.catalog_error: str | None = None
        try:
            self.catalog = service.get_catalog()
        except Exception as error:
            self.catalog_error = f"{type(error).__name__}: {error}"
        self.project_id: UUID | None = None
        self.park_id: UUID | None = None
        self.module_enabled = False
        self.chains: tuple[RefinedPowerChainConfiguration, ...] = ()
        self.solution: RefinedPowerOptimizationSolution | None = None
        self.byproduct_inputs: dict[str, QLineEdit] = {}

        self.setObjectName("RPOOptimizationPanel")
        self._build_ui()
        self._populate_profiles()
        self._update_mode_explanation()
        self._update_mode_controls()
        self._clear_solution()
        if self.catalog_error:
            self.status_label.setText(
                f"Catalogue Refined Power indisponible : {self.catalog_error}"
            )
            self.preview_button.setEnabled(False)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 18)
        root.setSpacing(12)

        intro = QLabel(
            "Comparez une installation existante, recherchez la production maximale ou "
            "dimensionnez une centrale pour atteindre une puissance cible. La proposition "
            "reste temporaire jusqu'à votre confirmation."
        )
        intro.setObjectName("RPOIntro")
        intro.setWordWrap(True)
        root.addWidget(intro)

        help_panel = QFrame()
        help_panel.setObjectName("RPOHelpPanel")
        help_layout = QVBoxLayout(help_panel)
        help_layout.setContentsMargins(14, 12, 14, 12)
        help_layout.setSpacing(7)

        self.mode_explanation_label = QLabel()
        self.mode_explanation_label.setObjectName("RPOHelpDescription")
        self.mode_explanation_label.setWordWrap(True)
        help_layout.addWidget(self.mode_explanation_label)

        self.mode_example_label = QLabel()
        self.mode_example_label.setObjectName("RPOHelpExample")
        self.mode_example_label.setWordWrap(True)
        help_layout.addWidget(self.mode_example_label)

        self.tutorial_button = QToolButton()
        self.tutorial_button.setObjectName("RPOTutorialToggle")
        self.tutorial_button.setText("Afficher le tutoriel express (2 min)")
        self.tutorial_button.setCheckable(True)
        help_layout.addWidget(self.tutorial_button, 0)

        self.tutorial_panel = self._build_tutorial_panel()
        self.tutorial_panel.setVisible(False)
        help_layout.addWidget(self.tutorial_panel)
        self.tutorial_button.toggled.connect(self._toggle_tutorial)
        root.addWidget(help_panel)

        request_panel = QFrame()
        request_panel.setObjectName("RPPanel")
        request_layout = QVBoxLayout(request_panel)
        request_layout.setContentsMargins(16, 14, 16, 14)
        request_layout.setSpacing(10)

        heading = QLabel("PARAMÈTRES DE L'ÉQUILIBRAGE")
        heading.setObjectName("SectionLabel")
        request_layout.addWidget(heading)

        request_grid = QGridLayout()
        request_grid.setHorizontalSpacing(12)
        request_grid.setVerticalSpacing(8)

        self.mode_combo = QComboBox()
        self.mode_combo.setObjectName("RPOModeSelector")
        self.mode_combo.setToolTip(
            "Équilibrer répare une chaîne existante ; Production maximale recherche "
            "le plus de MW possible sous les limites ; Puissance cible dimensionne "
            "une nouvelle chaîne pour un objectif donné."
        )
        self.mode_combo.addItem("Équilibrer une installation", "balance_existing")
        self.mode_combo.addItem("Production maximale", "maximize")
        self.mode_combo.addItem("Atteindre une puissance cible", "target")
        request_grid.addWidget(self._field_label("MODE"), 0, 0)
        request_grid.addWidget(self.mode_combo, 0, 1)

        self.reference_combo = QComboBox()
        self.reference_combo.setObjectName("RPOReferenceSelector")
        self.reference_combo.setMinimumWidth(220)
        self.reference_combo.setToolTip(
            "Sélectionnez la chaîne existante à corriger. Ce champ n'est utilisé "
            "que dans le mode Équilibrer une installation."
        )
        request_grid.addWidget(self._field_label("INSTALLATION À ÉQUILIBRER"), 0, 2)
        request_grid.addWidget(self.reference_combo, 0, 3)

        self.chain_name_input = QLineEdit("Centrale optimisée")
        self.chain_name_input.setObjectName("RPInput")
        self.chain_name_input.setMaxLength(80)
        self.chain_name_input.setToolTip(
            "Nom de la nouvelle chaîne qui sera créée après confirmation. "
            "Ce nom n'est pas utilisé pour modifier une chaîne existante."
        )
        request_grid.addWidget(self._field_label("NOM DE LA PROPOSITION"), 1, 0)
        request_grid.addWidget(self.chain_name_input, 1, 1)

        self.target_power_spin = QDoubleSpinBox()
        self.target_power_spin.setObjectName("RPOTargetPower")
        self.target_power_spin.setRange(0.1, 500000.0)
        self.target_power_spin.setDecimals(2)
        self.target_power_spin.setSingleStep(50.0)
        self.target_power_spin.setValue(500.0)
        self.target_power_spin.setSuffix(" MW")
        self.target_power_spin.setToolTip(
            "Puissance électrique souhaitée. Le solveur cherchera une configuration "
            "qui atteint cette valeur sans dépasser les limites de ressources et de matériel."
        )
        request_grid.addWidget(self._field_label("PUISSANCE CIBLE"), 1, 2)
        request_grid.addWidget(self.target_power_spin, 1, 3)
        request_layout.addLayout(request_grid)

        profile_heading = QLabel("PROFILS AUTORISÉS · MODES DE RECHERCHE")
        profile_heading.setObjectName("RPOptimizerSubheading")
        request_layout.addWidget(profile_heading)
        profile_grid = QGridLayout()
        profile_grid.setHorizontalSpacing(12)
        profile_grid.setVerticalSpacing(8)

        self.heater_filter = self._profile_combo("Tous les chauffages")
        self.fuel_filter = self._profile_combo("Tous les combustibles")
        self.boiler_filter = self._profile_combo("Toutes les chaudières")
        self.turbine_filter = self._profile_combo("Toutes les turbines")
        self.generator_filter = self._profile_combo("Tous les générateurs")

        profile_fields = (
            ("CHAUFFAGE", self.heater_filter),
            ("COMBUSTIBLE", self.fuel_filter),
            ("CHAUDIÈRE", self.boiler_filter),
            ("TURBINE", self.turbine_filter),
            ("GÉNÉRATEUR", self.generator_filter),
        )
        for index, (label_text, widget) in enumerate(profile_fields):
            row = index // 2
            column = (index % 2) * 2
            profile_grid.addWidget(self._field_label(label_text), row, column)
            profile_grid.addWidget(widget, row, column + 1)
        request_layout.addLayout(profile_grid)

        limits_heading = QLabel("RESSOURCES ET LIMITES MATÉRIELLES")
        limits_heading.setObjectName("RPOptimizerSubheading")
        request_layout.addWidget(limits_heading)
        limits_grid = QGridLayout()
        limits_grid.setHorizontalSpacing(12)
        limits_grid.setVerticalSpacing(8)

        self.max_boilers_spin = self._create_count_spin(10)
        self.max_turbines_spin = self._create_count_spin(10)
        self.max_generators_spin = self._create_count_spin(10)
        self.max_chimneys_spin = self._create_count_spin(10)
        self.max_cooling_towers_spin = self._create_count_spin(10)
        self.max_water_input = self._create_optional_input("Vide = pas de limite, en m³/min")
        self.fuel_available_input = self._create_optional_input("Vide = pas de limite")
        self.fuel_available_input.setToolTip(
            "Limite par minute dans l'unité du profil (items/min ou m³/min). "
            "Sélectionnez un combustible précis pour utiliser cette limite."
        )
        self.max_boilers_spin.setToolTip(
            "Nombre maximal de chaudières autorisées. Obligatoire pour rechercher "
            "une nouvelle configuration ; ce plafond borne le temps de calcul."
        )
        self.max_turbines_spin.setToolTip(
            "Nombre maximal de turbines autorisées dans la configuration proposée."
        )
        self.max_generators_spin.setToolTip(
            "Nombre maximal de générateurs autorisés. Le solveur vérifie les associations "
            "compatibles avec la turbine choisie."
        )
        self.max_chimneys_spin.setToolTip(
            "Nombre maximal de cheminées pour évacuer le CO₂ produit."
        )
        self.max_cooling_towers_spin.setToolTip(
            "Nombre maximal de tours pour évacuer la vapeur basse pression."
        )
        self.max_water_input.setToolTip(
            "Débit d'eau maximal réellement disponible en m³/min. Laisser vide signifie "
            "qu'aucune limite d'eau n'est imposée au calcul."
        )
        limit_fields = (
            ("CHAUDIÈRES MAX. *", self.max_boilers_spin),
            ("TURBINES MAX.", self.max_turbines_spin),
            ("GÉNÉRATEURS MAX.", self.max_generators_spin),
            ("CHEMINÉES CO₂ MAX.", self.max_chimneys_spin),
            ("TOURS DE REFROIDISSEMENT MAX.", self.max_cooling_towers_spin),
            ("EAU DISPONIBLE", self.max_water_input),
            ("COMBUSTIBLE DISPONIBLE", self.fuel_available_input),
        )
        for index, (label_text, widget) in enumerate(limit_fields):
            row = index // 2
            column = (index % 2) * 2
            limits_grid.addWidget(self._field_label(label_text), row, column)
            limits_grid.addWidget(widget, row, column + 1)
        request_layout.addLayout(limits_grid)

        coproduct_heading = QLabel("CAPACITÉS D'ACCUEIL DES COPRODUITS")
        coproduct_heading.setObjectName("RPOptimizerSubheading")
        request_layout.addWidget(coproduct_heading)
        coproduct_hint = QLabel(
            "Renseignez uniquement les capacités réellement disponibles. Une filière qui "
            "produit un déchet sans capacité d'accueil suffisante sera écartée."
        )
        coproduct_hint.setObjectName("ProjectMetadata")
        coproduct_hint.setWordWrap(True)
        request_layout.addWidget(coproduct_hint)
        self.byproduct_container = QWidget()
        self.byproduct_grid = QGridLayout(self.byproduct_container)
        self.byproduct_grid.setContentsMargins(0, 0, 0, 0)
        self.byproduct_grid.setHorizontalSpacing(12)
        self.byproduct_grid.setVerticalSpacing(6)
        self._build_byproduct_fields()
        request_layout.addWidget(self.byproduct_container)

        note = QLabel(
            "* Obligatoire pour les modes Production maximale et Puissance cible afin de "
            "borner la recherche. Les limites d'équipements sont des nombres entiers."
        )
        note.setObjectName("ProjectMetadata")
        note.setWordWrap(True)
        request_layout.addWidget(note)
        root.addWidget(request_panel)

        actions = QHBoxLayout()
        actions.addStretch(1)
        self.preview_button = QPushButton("Lancer l'équilibrage")
        self.preview_button.setObjectName("PrimarySmallButton")
        self.preview_button.setMinimumHeight(38)
        self.preview_button.clicked.connect(self._run_optimization)
        actions.addWidget(self.preview_button)

        self.apply_button = QPushButton("Appliquer la proposition")
        self.apply_button.setObjectName("RPApplyOptimizationButton")
        self.apply_button.setMinimumHeight(38)
        self.apply_button.setEnabled(False)
        self.apply_button.clicked.connect(self._request_apply)
        actions.addWidget(self.apply_button)
        root.addLayout(actions)

        self.status_label = QLabel("Sélectionnez un parc actif pour lancer un équilibrage.")
        self.status_label.setObjectName("RPOptimizerStatus")
        self.status_label.setWordWrap(True)
        root.addWidget(self.status_label)

        self.result_panel = QFrame()
        self.result_panel.setObjectName("RPPanel")
        result_layout = QVBoxLayout(self.result_panel)
        result_layout.setContentsMargins(16, 14, 16, 14)
        result_layout.setSpacing(9)

        result_heading = QLabel("RÉSULTAT ET COMPARATIF")
        result_heading.setObjectName("SectionLabel")
        result_layout.addWidget(result_heading)

        metrics = QGridLayout()
        metrics.setHorizontalSpacing(10)
        self.before_power_value = self._add_metric(metrics, 0, 0, "AVANT", "—")
        self.after_power_value = self._add_metric(metrics, 0, 1, "PROPOSITION", "—")
        self.water_value = self._add_metric(metrics, 0, 2, "EAU REQUISE", "—")
        self.fuel_value = self._add_metric(metrics, 0, 3, "COMBUSTIBLE", "—")
        result_layout.addLayout(metrics)

        self.solution_summary = QLabel("Aucun équilibrage lancé.")
        self.solution_summary.setObjectName("RPOptimizerSummary")
        self.solution_summary.setWordWrap(True)
        result_layout.addWidget(self.solution_summary)

        changes_heading = QLabel("MODIFICATIONS PROPOSÉES")
        changes_heading.setObjectName("RPOptimizerSubheading")
        result_layout.addWidget(changes_heading)
        self.changes_list = QListWidget()
        self.changes_list.setObjectName("RPOChangesList")
        self.changes_list.setMinimumHeight(120)
        result_layout.addWidget(self.changes_list)

        self.constraints_label = QLabel()
        self.constraints_label.setObjectName("RPOptimizerConstraints")
        self.constraints_label.setWordWrap(True)
        result_layout.addWidget(self.constraints_label)
        self.warnings_label = QLabel()
        self.warnings_label.setObjectName("RPOptimizerWarnings")
        self.warnings_label.setWordWrap(True)
        result_layout.addWidget(self.warnings_label)
        root.addWidget(self.result_panel)

        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        self.fuel_filter.currentIndexChanged.connect(self._on_fuel_filter_changed)
        self.reference_combo.currentIndexChanged.connect(self._clear_solution)
        for combo in (
            self.heater_filter,
            self.boiler_filter,
            self.turbine_filter,
            self.generator_filter,
        ):
            combo.currentIndexChanged.connect(self._clear_solution)
        for spin in (
            self.target_power_spin,
            self.max_boilers_spin,
            self.max_turbines_spin,
            self.max_generators_spin,
            self.max_chimneys_spin,
            self.max_cooling_towers_spin,
        ):
            spin.valueChanged.connect(self._clear_solution)
        for field in (
            self.chain_name_input,
            self.max_water_input,
            self.fuel_available_input,
            *self.byproduct_inputs.values(),
        ):
            field.textChanged.connect(self._clear_solution)

    @staticmethod
    def _field_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("RPFieldLabel")
        return label

    @staticmethod
    def _profile_combo(placeholder: str) -> QComboBox:
        combo = QComboBox()
        combo.setMinimumHeight(34)
        combo.setObjectName("RPOProfileSelector")
        combo.addItem(placeholder, None)
        combo.setToolTip(
            "Laissez sur le choix général pour autoriser tous les profils compatibles. "
            "Sélectionnez un profil pour limiter la recherche à cet équipement ou combustible."
        )
        return combo

    @staticmethod
    def _create_count_spin(value: int) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(0, 10000)
        spin.setValue(value)
        spin.setMinimumHeight(34)
        spin.setObjectName("RPOEquipmentLimit")
        return spin

    @staticmethod
    def _create_optional_input(placeholder: str) -> QLineEdit:
        field = QLineEdit()
        field.setObjectName("RPInput")
        field.setMinimumHeight(34)
        field.setPlaceholderText(placeholder)
        return field

    @staticmethod
    def _add_metric(
        layout: QGridLayout,
        row: int,
        column: int,
        label_text: str,
        value_text: str,
    ) -> QLabel:
        card = QFrame()
        card.setObjectName("RPMetricCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(10, 9, 10, 9)
        card_layout.setSpacing(3)
        heading = QLabel(label_text)
        heading.setObjectName("SimulationMetricLabel")
        value = QLabel(value_text)
        value.setObjectName("SimulationMetricValue")
        card_layout.addWidget(heading)
        card_layout.addWidget(value)
        layout.addWidget(card, row, column)
        return value

    def _populate_profiles(self, preferred: dict[str, str | None] | None = None) -> None:
        if self.catalog is None:
            return
        preferred = preferred or {}
        self._populate_profile_combo(
            self.heater_filter,
            self.catalog.heaters,
            "heater_id",
            preferred.get("heater"),
        )
        self._populate_profile_combo(
            self.fuel_filter,
            self.catalog.fuels,
            "fuel_id",
            preferred.get("fuel"),
        )
        self._populate_profile_combo(
            self.boiler_filter,
            self.catalog.boilers,
            "boiler_id",
            preferred.get("boiler"),
        )
        self._populate_profile_combo(
            self.turbine_filter,
            self.catalog.turbines,
            "turbine_id",
            preferred.get("turbine"),
        )
        self._populate_profile_combo(
            self.generator_filter,
            self.catalog.generators,
            "generator_id",
            preferred.get("generator"),
        )

    def _populate_profile_combo(
        self,
        combo,
        profiles,
        id_field: str,
        preferred_id: str | None = None,
    ) -> None:
        placeholder = combo.itemText(0) or "Tous"
        if preferred_id is None:
            preferred_id = combo.currentData()
        combo.blockSignals(True)
        combo.clear()
        combo.addItem(placeholder, None)
        for profile in profiles:
            display_name = self.service.get_profile_display_name(profile, self.locale)
            combo.addItem(display_name, getattr(profile, id_field))
        selected_index = combo.findData(preferred_id)
        combo.setCurrentIndex(max(selected_index, 0))
        combo.blockSignals(False)

    def _build_byproduct_fields(self) -> None:
        if self.catalog is None:
            return
        previous_values = {
            resource_id: field.text()
            for resource_id, field in self.byproduct_inputs.items()
        }
        while self.byproduct_grid.count():
            item = self.byproduct_grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.byproduct_inputs.clear()
        byproducts = {}
        for fuel in self.catalog.fuels:
            for product in fuel.byproducts:
                byproducts[product.resource_id] = (
                    self.service.get_profile_display_name(product, self.locale),
                    product.unit,
                )

        for row, (resource_id, (display_name, unit)) in enumerate(sorted(byproducts.items())):
            label = self._field_label(f"{display_name} · {unit}")
            field = self._create_optional_input("Vide = aucune capacité")
            field.setText(previous_values.get(resource_id, ""))
            field.textChanged.connect(self._clear_solution)
            field.setToolTip(
                f"Capacité d'accueil pour {display_name}, par minute. "
                "Laisser vide signifie qu'aucune capacité n'est disponible."
            )
            self.byproduct_inputs[resource_id] = field
            self.byproduct_grid.addWidget(label, row, 0)
            self.byproduct_grid.addWidget(field, row, 1)

    def set_locale(self, locale: str) -> None:
        """Actualise les libellés sans modifier les identifiants des profils."""

        if not locale or locale == self.locale:
            return
        preferred = {
            "heater": self.heater_filter.currentData(),
            "fuel": self.fuel_filter.currentData(),
            "boiler": self.boiler_filter.currentData(),
            "turbine": self.turbine_filter.currentData(),
            "generator": self.generator_filter.currentData(),
        }
        self.locale = locale
        self._populate_profiles(preferred)
        self._build_byproduct_fields()
        self._update_fuel_limit_hint()
        self._clear_solution()

    def _build_tutorial_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("RPOTutorialPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)
        steps = (
            (
                "1. Choisissez le parc et vérifiez que Refined Power est activé "
                "dans « Mods & extensions »."
            ),
            (
                "2. Sélectionnez un mode : réparer une chaîne existante, chercher "
                "le maximum ou viser une puissance précise."
            ),
            (
                "3. Renseignez les limites réelles. Le nombre maximal de chaudières "
                "est obligatoire pour les deux modes de recherche. Pour limiter le "
                "combustible, choisissez d'abord un combustible précis ; les champs "
                "eau ou combustible laissés vides signifient « pas de limite »."
            ),
            (
                "4. Pour un coproduit (déchet ou ressource secondaire), indiquez une "
                "capacité de stockage ou d'évacuation. Sans capacité, une solution "
                "qui en produit sera écartée."
            ),
            (
                "5. Cliquez sur « Lancer l'équilibrage ». Lisez les écarts, les "
                "contraintes et les avertissements. Rien n'est enregistré à cette étape."
            ),
            (
                "6. Cliquez sur « Appliquer la proposition » uniquement après "
                "vérification. Le mode Installation met à jour la chaîne choisie ; "
                "les deux autres créent une nouvelle chaîne."
            ),
        )
        title = QLabel("GUIDE PAS À PAS")
        title.setObjectName("RPOHelpHeading")
        layout.addWidget(title)
        for text in steps:
            step = QLabel(text)
            step.setObjectName("RPOHelpStep")
            step.setWordWrap(True)
            layout.addWidget(step)

        glossary = QLabel(
            "Repères : m³/min = débit par minute · RPM = vitesse de rotation · "
            "vapeur HP/LP = haute/basse pression · coproduit = ressource secondaire ou déchet."
        )
        glossary.setObjectName("RPOHelpGlossary")
        glossary.setWordWrap(True)
        layout.addWidget(glossary)

        example = QLabel(
            "Exemple concret : vous visez 500 MW avec du charbon. Sélectionnez "
            "« Atteindre une puissance cible », indiquez 500 MW, choisissez le charbon, puis "
            "renseignez le nombre maximal de chaudières et vos capacités de "
            "refroidissement et d'évacuation du CO₂. L'aperçu indique la puissance "
            "atteignable, les machines nécessaires et les éventuelles contraintes. "
            "Si 500 MW sont impossibles avec ces limites, J.A.R.V.I.S. affiche la "
            "meilleure solution réalisable sans l'enregistrer automatiquement."
        )
        example.setObjectName("RPOHelpExample")
        example.setWordWrap(True)
        layout.addWidget(example)
        return panel

    def _toggle_tutorial(self, expanded: bool) -> None:
        self.tutorial_panel.setVisible(expanded)
        self.tutorial_button.setText(
            "Masquer le tutoriel" if expanded else "Afficher le tutoriel express (2 min)"
        )

    def _update_mode_explanation(self) -> None:
        explanations = {
            "balance_existing": (
                (
                    "Vous avez déjà construit une centrale. Choisissez-la dans le champ "
                    "« Installation à équilibrer ». J.A.R.V.I.S. conserve son chauffage, "
                    "son combustible et sa chaudière, puis ajuste les turbines, les "
                    "générateurs et les équipements d'évacuation."
                ),
                (
                    "Exemple : votre chaudière produit plus de vapeur que vos turbines "
                    "ne peuvent en absorber. Ce mode ajoute ou ajuste les équipements "
                    "nécessaires sans changer votre filière de combustible."
                ),
            ),
            "maximize": (
                (
                    "Vous voulez connaître la production maximale possible. Choisissez "
                    "les profils autorisés, fixez un maximum de chaudières et indiquez "
                    "les ressources ou équipements réellement disponibles."
                ),
                (
                    "Exemple : vous disposez de 90 m³/min d'eau et d'un stock de "
                    "combustible limité. J.A.R.V.I.S. cherche la configuration qui "
                    "produit le plus de MW sans dépasser ces limites."
                ),
            ),
            "target": (
                (
                    "Vous connaissez la puissance dont vous avez besoin. Indiquez "
                    "votre objectif en MW, les profils autorisés et vos limites de "
                    "ressources et d'équipements."
                ),
                (
                    "Exemple : pour une cible de 500 MW, J.A.R.V.I.S. cherche une "
                    "combinaison réalisable. Si 500 MW sont impossibles, il présente "
                    "la meilleure puissance atteignable et les limites bloquantes."
                ),
            ),
        }
        mode = self.mode_combo.currentData() if hasattr(self, "mode_combo") else "balance_existing"
        description, example = explanations.get(mode, explanations["balance_existing"])
        if hasattr(self, "mode_explanation_label"):
            self.mode_explanation_label.setText(description)
            self.mode_example_label.setText(example)

    def set_context(
        self,
        project_id: UUID | None,
        park_id: UUID | None,
        module_enabled: bool,
        chains: tuple[RefinedPowerChainConfiguration, ...],
    ) -> None:
        self.project_id = project_id
        self.park_id = park_id
        self.module_enabled = module_enabled
        self.chains = chains

        previous_reference_id = self.reference_combo.currentData()
        self.reference_combo.blockSignals(True)
        self.reference_combo.clear()
        for chain in chains:
            self.reference_combo.addItem(chain.name, str(chain.chain_id))
        selected = self.reference_combo.findData(previous_reference_id)
        if selected < 0 and chains:
            selected = 0
        if selected >= 0:
            self.reference_combo.setCurrentIndex(selected)
        self.reference_combo.blockSignals(False)
        if not chains and self.mode_combo.currentData() == "balance_existing":
            maximize_index = self.mode_combo.findData("maximize")
            if maximize_index >= 0:
                self.mode_combo.setCurrentIndex(maximize_index)

        enabled = (
            project_id is not None
            and park_id is not None
            and module_enabled
            and self.catalog is not None
        )
        self.preview_button.setEnabled(enabled)
        self.apply_button.setEnabled(False)
        if not enabled:
            self.status_label.setText(
                "Sélectionnez un parc où Refined Power est activé pour lancer un équilibrage."
            )
        elif not chains:
            self.status_label.setText(
                "Aucune chaîne existante : les modes Production maximale et Puissance cible "
                "peuvent créer une nouvelle installation."
            )
        else:
            self.status_label.setText(
                "Choisissez un mode. La prévisualisation ne modifie aucune donnée enregistrée."
            )
        self._update_mode_controls()
        self._clear_solution()

    def select_reference_chain(self, chain_id: UUID | None) -> None:
        if chain_id is None:
            return
        index = self.reference_combo.findData(str(chain_id))
        if index >= 0:
            self.reference_combo.setCurrentIndex(index)

    def _on_mode_changed(self, *_args) -> None:
        self._update_mode_controls()
        self._update_mode_explanation()
        self._clear_solution()

    def _on_fuel_filter_changed(self, *_args) -> None:
        self._update_fuel_limit_hint()
        self._clear_solution()

    def _update_mode_controls(self, *_args) -> None:
        mode = self.mode_combo.currentData()
        is_balance = mode == "balance_existing"
        is_target = mode == "target"
        self.reference_combo.setEnabled(is_balance and self.module_enabled and bool(self.chains))
        self.chain_name_input.setEnabled(not is_balance)
        self.target_power_spin.setEnabled(is_target)
        for combo in (
            self.heater_filter,
            self.fuel_filter,
            self.boiler_filter,
            self.turbine_filter,
            self.generator_filter,
        ):
            combo.setEnabled(not is_balance)
        self.max_boilers_spin.setEnabled(not is_balance)
        self.fuel_available_input.setEnabled(
            self.fuel_filter.currentData() is not None or is_balance
        )
        self._update_fuel_limit_hint()

    def _update_fuel_limit_hint(self, *_args) -> None:
        fuel_id = self.fuel_filter.currentData()
        is_balance = self.mode_combo.currentData() == "balance_existing"
        if is_balance:
            self.fuel_available_input.setPlaceholderText(
                "Vide = pas de limite pour le combustible de la chaîne"
            )
        elif fuel_id is None:
            self.fuel_available_input.clear()
            self.fuel_available_input.setEnabled(False)
            self.fuel_available_input.setPlaceholderText(
                "Sélectionnez un combustible précis"
            )
        else:
            fuel = self.catalog.get_fuel(fuel_id)
            self.fuel_available_input.setEnabled(True)
            self.fuel_available_input.setPlaceholderText(
                f"En {fuel.input_unit} · vide = pas de limite"
            )

    def _build_limits(self, mode: str) -> RefinedPowerOptimizationLimits:
        max_water = self._optional_decimal(self.max_water_input, "Eau disponible")
        fuel_available = self._optional_decimal(
            self.fuel_available_input,
            "Combustible disponible",
        )
        fuel_limits = {}
        if fuel_available is not None:
            if mode == "balance_existing":
                reference = self._selected_reference_chain()
                fuel_limits[reference.fuel_id] = fuel_available
            else:
                fuel_id = self.fuel_filter.currentData()
                if fuel_id is None:
                    raise ValueError(
                        "Sélectionnez un combustible précis pour limiter sa disponibilité."
                    )
                fuel_limits[fuel_id] = fuel_available

        byproduct_limits = {}
        for resource_id, field in self.byproduct_inputs.items():
            value = self._optional_decimal(field, f"Capacité de {resource_id}")
            if value is not None:
                byproduct_limits[resource_id] = value

        return RefinedPowerOptimizationLimits(
            max_water_m3_per_minute=max_water,
            fuel_available_per_minute=fuel_limits,
            byproduct_capacity_per_minute=byproduct_limits,
            max_boilers=None if mode == "balance_existing" else self.max_boilers_spin.value(),
            max_turbines=self.max_turbines_spin.value(),
            max_generators=self.max_generators_spin.value(),
            max_co2_chimneys=self.max_chimneys_spin.value(),
            max_steam_cooling_towers=self.max_cooling_towers_spin.value(),
        )

    @staticmethod
    def _optional_decimal(field: QLineEdit, label: str) -> Decimal | None:
        raw_value = field.text().strip().replace(" ", "").replace(",", ".")
        if not raw_value:
            return None
        try:
            value = Decimal(raw_value)
        except InvalidOperation as error:
            raise ValueError(f"Valeur invalide pour « {label} ».") from error
        if not value.is_finite() or value < 0:
            raise ValueError(f"« {label} » doit être un nombre positif ou nul.")
        return value

    def _selected_reference_chain(self) -> RefinedPowerChainConfiguration:
        chain_id = self.reference_combo.currentData()
        if chain_id is None:
            raise ValueError("Sélectionnez une installation à équilibrer.")
        selected_id = UUID(chain_id)
        for chain in self.chains:
            if chain.chain_id == selected_id:
                return chain
        raise ValueError("L'installation sélectionnée n'est plus disponible dans ce parc.")

    def _build_request(self) -> RefinedPowerOptimizationRequest:
        mode = self.mode_combo.currentData()
        limits = self._build_limits(mode)
        reference = self._selected_reference_chain() if mode == "balance_existing" else None

        def selected_id(combo: QComboBox) -> tuple[str, ...]:
            value = combo.currentData()
            return (value,) if value is not None else ()

        values = {
            "mode": mode,
            "reference_configuration": reference,
            "target_power_mw": (
                Decimal(str(self.target_power_spin.value())) if mode == "target" else None
            ),
            "chain_name": self.chain_name_input.text().strip() or "Centrale optimisée",
            "allowed_heater_ids": selected_id(self.heater_filter),
            "allowed_fuel_ids": selected_id(self.fuel_filter),
            "allowed_boiler_ids": selected_id(self.boiler_filter),
            "allowed_turbine_ids": selected_id(self.turbine_filter),
            "allowed_generator_ids": selected_id(self.generator_filter),
            "limits": limits,
        }
        return RefinedPowerOptimizationRequest.model_validate(values)

    def _run_optimization(self) -> None:
        if not self.module_enabled or self.project_id is None or self.park_id is None:
            self.status_label.setText("Aucun parc actif avec Refined Power sélectionné.")
            return
        try:
            request = self._build_request()
            self.solution = self.service.preview_optimization(request, self.locale)
        except Exception as error:
            self.solution = None
            self.apply_button.setEnabled(False)
            self._clear_solution(clear_status=False)
            self.status_label.setText(f"Équilibrage impossible : {error}")
            return
        self._display_solution(self.solution)

    def _display_solution(self, solution: RefinedPowerOptimizationSolution) -> None:
        self.changes_list.clear()
        before = solution.reference_calculation
        after = solution.calculation
        self.before_power_value.setText(
            f"{self._format_decimal(before.estimated_power_mw)} MW" if before else "—"
        )
        self.after_power_value.setText(
            f"{self._format_decimal(after.estimated_power_mw)} MW" if after else "Aucune"
        )
        self.water_value.setText(
            f"{self._format_decimal(after.water_consumption_m3_per_minute)} m³/min"
            if after
            else "—"
        )
        if after:
            self.fuel_value.setText(
                f"{self._format_decimal(after.fuel_consumption_per_minute)} "
                f"{after.fuel_unit}"
            )
        else:
            self.fuel_value.setText("—")

        if not solution.feasible:
            headline = "AUCUNE CONFIGURATION CONFORME AUX LIMITES"
        elif solution.target_reached is False:
            headline = "MEILLEURE SOLUTION TROUVÉE · CIBLE NON ATTEINTE"
        elif solution.mode == "balance_existing" and not solution.changes:
            headline = "INSTALLATION DÉJÀ ÉQUILIBRÉE"
        else:
            headline = "PROPOSITION RÉALISABLE"
        self.solution_summary.setText(
            f"{headline}\n{solution.objective_summary}\n"
            f"Candidats évalués : {solution.candidates_evaluated:,}".replace(",", " ")
        )

        if solution.changes:
            for change in solution.changes:
                self.changes_list.addItem(
                    f"{change.label} : {change.previous_value} → {change.proposed_value}\n"
                    f"   Motif : {change.reason}"
                )
        elif solution.feasible:
            self.changes_list.addItem("Aucune modification matérielle nécessaire.")
        else:
            self.changes_list.addItem("Aucune configuration exploitable n'a été produite.")

        details = []
        if solution.limiting_constraints:
            details.append(
                "CONTRAINTES / LIMITES\n"
                + "\n".join(f"• {item}" for item in solution.limiting_constraints)
            )
        if solution.warnings:
            details.append(
                "AVERTISSEMENTS\n" + "\n".join(f"• {item}" for item in solution.warnings)
            )
        self.constraints_label.setText("\n\n".join(details))
        self.warnings_label.setText(
            "Aucune donnée n'a été enregistrée. La proposition ne sera persistée "
            "qu'après confirmation explicite."
        )
        self.apply_button.setEnabled(
            solution.feasible and solution.configuration is not None and self.module_enabled
        )
        self.status_label.setText(
            "Prévisualisation terminée. Vérifiez les écarts, puis appliquez ou abandonnez "
            "la proposition."
        )

    def _request_apply(self) -> None:
        if (
            self.solution is None
            or not self.solution.feasible
            or self.solution.configuration is None
            or not self.module_enabled
        ):
            return
        self.apply_requested.emit(self.solution.configuration)

    def _clear_solution(self, *_args, clear_status: bool = True) -> None:
        self.solution = None
        self.apply_button.setEnabled(False)
        self.before_power_value.setText("—")
        self.after_power_value.setText("—")
        self.water_value.setText("—")
        self.fuel_value.setText("—")
        self.solution_summary.setText("Aucun équilibrage lancé.")
        self.changes_list.clear()
        self.constraints_label.clear()
        self.warnings_label.setText(
            "Les aperçus sont temporaires et ne modifient aucune chaîne enregistrée."
        )
        if clear_status and hasattr(self, "status_label"):
            if self.module_enabled:
                self.status_label.setText("Prêt à lancer un équilibrage.")

    def _update_mode_controls_after_refresh(self) -> None:
        self._update_mode_controls()

    @staticmethod
    def _format_decimal(value: Decimal) -> str:
        return f"{value:,.2f}".replace(",", " ").replace(".", ",")


__all__ = ["RefinedPowerOptimizationPanel"]
