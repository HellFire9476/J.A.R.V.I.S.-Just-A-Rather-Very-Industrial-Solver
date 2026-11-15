"""Interface de simulation d'une chaîne de production Satisfactory."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from jarvis.application.services.production_service import ProductionService
from jarvis.domain.entities.production import ItemProfile, ProductionPlan
from jarvis.domain.entities.recipe import Recipe, RecipeComponent
from jarvis.engines.production_engine import (
    ProducerChoiceRequiredError,
    ProductionCalculationError,
    RecipeChoiceRequiredError,
)


class _SimulationCatalogWorker(QThread):
    """Charge les cibles et recettes sans bloquer le thread graphique."""

    loaded = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        service: ProductionService,
        locale: str,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.service = service
        self.locale = locale

    def run(self) -> None:
        try:
            locales = self.service.list_locales()
            selected_locale = self.locale
            if locales and selected_locale not in locales:
                selected_locale = "fr" if "fr" in locales else locales[0]
            targets, recipes_by_product = self.service.get_target_catalog(selected_locale)
            payload = {
                "locales": locales,
                "targets": targets,
                "recipes_by_product": recipes_by_product,
                "locale": selected_locale,
            }
            self.loaded.emit(payload)
        except Exception as exc:  # l'interface présente l'erreur à l'utilisateur
            self.failed.emit(f"{type(exc).__name__}: {exc}")


class _ProductionPlanWorker(QThread):
    """Calcule un plan de production en dehors du thread graphique."""

    completed = Signal(object, object)

    def __init__(
        self,
        service: ProductionService,
        arguments: dict[str, Any],
        parent=None,
    ):
        super().__init__(parent)
        self.service = service
        self.arguments = arguments

    def run(self) -> None:
        try:
            plan = self.service.plan_production(**self.arguments)
        except Exception as exc:  # l'erreur sera affichée dans la page
            self.completed.emit(None, exc)
        else:
            self.completed.emit(plan, None)


class SimulationsPage(QWidget):
    """Configure un objectif, lance le moteur et présente le bilan calculé."""

    def __init__(
        self,
        service: ProductionService | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.service = service or ProductionService()
        self._catalog_loaded = False
        self._catalog_loading = False
        self._plan_loading = False
        self._catalog_worker: _SimulationCatalogWorker | None = None
        self._plan_worker: _ProductionPlanWorker | None = None
        self._targets: dict[str, ItemProfile] = {}
        self._recipes_by_product: dict[str, tuple[Recipe, ...]] = {}
        self._recipes_by_class: dict[str, Recipe] = {}
        self._recipe_choices: dict[str, str] = {}
        self._producer_choices: dict[str, str] = {}
        self._extractor_choices: dict[str, str] = {}
        self._machine_clock_limits: dict[str, Decimal] = {}
        self._extractor_clock_limits: dict[str, Decimal] = {}
        self._deferred_choice_error: Exception | None = None
        self._current_plan: ProductionPlan | None = None
        self._active_locale = "fr"
        self._restoring_controls = False

        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(15)

        title = QLabel("Simulations de production")
        title.setObjectName("PageTitle")
        title.setToolTip(
            "Espace de calcul d'une chaîne industrielle à partir du catalogue local "
            "Satisfactory. Les valeurs affichées sont des besoins théoriques pour "
            "l'objectif sélectionné."
        )
        subtitle = QLabel(
            "Définissez un objectif de fabrication à partir du catalogue Satisfactory : "
            "J.A.R.V.I.S. calcule les besoins théoriques en ressources, les fabricants, "
            "les extracteurs et la puissance nécessaire."
        )
        subtitle.setObjectName("PageSubtitle")
        subtitle.setWordWrap(True)
        subtitle.setToolTip(
            "Le calcul décompose le produit final en recettes, fabricants, ressources "
            "brutes, extracteurs, coproduits et consommation électrique estimée."
        )
        root.addWidget(title)
        root.addWidget(subtitle)

        self.scope_label = QLabel(
            "CALCUL THÉORIQUE · INDÉPENDANT DES PARTIES ET DES PARCS"
        )
        self.scope_label.setObjectName("SimulationScopeLabel")
        self.scope_label.setToolTip(
            "Cette rubrique ne dépend d'aucune partie ni d'aucun parc. Elle utilise "
            "le catalogue technique Satisfactory, l'objectif de production et les "
            "choix de recettes ou d'extracteurs. Les ressources et les bâtiments "
            "sont calculés théoriquement : aucun stock, bâtiment posé ou équipement "
            "possédé dans une sauvegarde n'est consulté."
        )
        root.addWidget(self.scope_label)

        controls = QFrame()
        controls.setObjectName("SimulationControls")
        controls_layout = QGridLayout(controls)
        controls_layout.setContentsMargins(16, 14, 16, 14)
        controls_layout.setHorizontalSpacing(12)
        controls_layout.setVerticalSpacing(8)

        target_label = QLabel("PRODUIT À FABRIQUER")
        target_label.setObjectName("SectionLabel")
        rate_label = QLabel("OBJECTIF DE PRODUCTION")
        rate_label.setObjectName("SectionLabel")
        locale_label = QLabel("LANGUE DU CATALOGUE")
        locale_label.setObjectName("SectionLabel")
        recipe_label = QLabel("RECETTE À UTILISER")
        recipe_label.setObjectName("SectionLabel")
        target_label.setToolTip(
            "Produit final dont vous souhaitez dimensionner la fabrication. "
            "La liste contient les produits disposant d'au moins une recette automatisée."
        )
        rate_label.setToolTip(
            "Débit de sortie souhaité pour le produit final. Les solides sont exprimés "
            "en objets/min et les liquides ou gaz en m³/min."
        )
        locale_label.setToolTip(
            "Langue utilisée pour les noms et descriptions du catalogue. "
            "Le changement de langue ne modifie pas les quantités techniques du calcul."
        )
        recipe_label.setToolTip(
            "Recette utilisée pour fabriquer le produit final. Si plusieurs recettes "
            "existent, choisissez celle à appliquer ; les ingrédients et produits par "
            "cycle sont indiqués dans la liste et son info-bulle."
        )

        self.target_combo = QComboBox()
        self.target_combo.setObjectName("SimulationInput")
        self.target_combo.setEditable(True)
        self.target_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.target_combo.setMaxVisibleItems(22)
        self.target_combo.setMinimumWidth(270)
        self.target_combo.setToolTip(
            "Sélectionnez un produit fabriqué par une recette automatisée."
        )
        self.target_combo.lineEdit().setPlaceholderText("Rechercher un produit…")
        self.target_combo.lineEdit().setToolTip(
            "Saisissez quelques lettres pour filtrer le catalogue des produits automatisables."
        )
        self.target_combo.currentIndexChanged.connect(self._on_target_changed)

        self.rate_spin = QDoubleSpinBox()
        self.rate_spin.setObjectName("SimulationInput")
        self.rate_spin.setDecimals(3)
        self.rate_spin.setRange(0.001, 1_000_000_000)
        self.rate_spin.setValue(60)
        self.rate_spin.setKeyboardTracking(False)
        self.rate_spin.setMinimumWidth(155)
        self.rate_spin.setToolTip(
            "Débit de sortie demandé pour le produit final. Un objet solide utilise "
            "objets/min ; un liquide ou un gaz utilise m³/min. Ce champ définit "
            "l'objectif à atteindre, pas la capacité d'une machine."
        )

        self.locale_combo = QComboBox()
        self.locale_combo.setObjectName("SimulationInput")
        self.locale_combo.setMinimumWidth(120)
        self.locale_combo.setToolTip(
            "Choisit la langue des noms et descriptions des produits, recettes et machines. "
            "Les identifiants et les données de calcul restent identiques."
        )
        self.locale_combo.currentIndexChanged.connect(self._on_locale_changed)

        self.recipe_combo = QComboBox()
        self.recipe_combo.setObjectName("SimulationInput")
        self.recipe_combo.setMinimumWidth(520)
        self.recipe_combo.setMinimumContentsLength(72)
        self.recipe_combo.view().setMinimumWidth(900)
        self.recipe_combo.setToolTip(
            "Chaque choix présente le ou les fabricants compatibles, les ingrédients "
            "consommés et les produits obtenus par cycle. Survolez un choix pour lire "
            "le détail et la durée du cycle. Les identifiants internes ne sont pas "
            "affichés dans le libellé destiné au joueur."
        )
        self.recipe_combo.setEnabled(False)

        self.calculate_button = QPushButton("Calculer la production")
        self.calculate_button.setObjectName("PrimaryButton")
        self.calculate_button.setMinimumHeight(40)
        self.calculate_button.setToolTip(
            "Lance le calcul de la chaîne pour l'objectif choisi. J.A.R.V.I.S. "
            "décompose les recettes et dimensionne fabricants et extracteurs. "
            "Si une recette ou un fabricant est ambigu, un choix vous sera demandé."
        )
        self.calculate_button.clicked.connect(self._calculate_plan)

        controls_layout.addWidget(target_label, 0, 0)
        controls_layout.addWidget(rate_label, 0, 1)
        controls_layout.addWidget(locale_label, 0, 2)
        controls_layout.addWidget(self.target_combo, 1, 0)
        controls_layout.addWidget(self.rate_spin, 1, 1)
        controls_layout.addWidget(self.locale_combo, 1, 2)
        controls_layout.addWidget(recipe_label, 2, 0)
        controls_layout.addWidget(self.recipe_combo, 3, 0, 1, 2)
        controls_layout.addWidget(self.calculate_button, 3, 2)
        root.addWidget(controls)

        self.status_label = QLabel(
            "Le catalogue sera chargé à la première ouverture de cette page."
        )
        self.status_label.setObjectName("SimulationStatus")
        self.status_label.setWordWrap(True)
        self.status_label.setToolTip(
            "État du chargement du catalogue, du calcul ou explication d'un blocage. "
            "Un message d'avertissement ne signifie pas nécessairement que le calcul "
            "des quantités a échoué : consultez aussi le panneau des limites du calcul."
        )
        root.addWidget(self.status_label)

        self.results_scroll = QScrollArea()
        self.results_scroll.setObjectName("SimulationResultsScroll")
        self.results_scroll.setWidgetResizable(True)
        self.results_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.results_scroll.setToolTip(
            "Résultats détaillés de la simulation. Survolez les titres, les valeurs et "
            "les réglages pour obtenir leur définition."
        )

        self.results_body = QWidget()
        self.results_layout = QVBoxLayout(self.results_body)
        self.results_layout.setContentsMargins(0, 0, 6, 0)
        self.results_layout.setSpacing(14)

        metrics = QHBoxLayout()
        self.target_metric = self._metric_card(
            "OBJECTIF",
            "—",
            "Produit final et débit de sortie demandé. L'unité dépend de sa forme : "
            "objets/min pour les solides, m³/min pour les fluides.",
        )
        self.machine_metric = self._metric_card(
            "MACHINES DE FABRICATION",
            "—",
            "Nombre entier de fabricants nécessaires pour exécuter les recettes "
            "sélectionnées. Les extracteurs de ressources ne sont pas inclus dans ce total.",
        )
        self.power_metric = self._metric_card(
            "PUISSANCE TOTALE",
            "—",
            "Somme de la puissance estimée des fabricants et des extracteurs sélectionnés. "
            "Une estimation partielle ou une fourchette est signalée lorsque le catalogue "
            "ne fournit pas une puissance fixe exploitable.",
        )
        metrics.addWidget(self.target_metric[0], 1)
        metrics.addWidget(self.machine_metric[0], 1)
        metrics.addWidget(self.power_metric[0], 1)
        self.results_layout.addLayout(metrics)

        self.machine_table = self._create_table(
            (
                "Recette",
                "Fabricant",
                "Machines",
                "Machines équivalentes à 100 %",
                "Cadence max. / machine",
                "Cadence réelle / machine",
                "Puissance fabrication",
            )
        )
        self._configure_table_columns(
            self.machine_table,
            (235, 145, 82, 205, 155, 145, 160),
        )
        self._set_header_tooltips(
            self.machine_table,
            (
                "Recette utilisée pour produire le composant demandé. Survolez une cellule "
                "pour retrouver ses ingrédients, ses sorties et la durée de cycle.",
                "Bâtiment fabricant qui exécute cette recette (par exemple constructeur, "
                "assembleuse ou raffinerie).",
                "Nombre entier de bâtiments physiques à construire. Ce nombre dépend du "
                "plafond de cadence défini dans la colonne correspondante.",
                "Capacité de production théorique exprimée en machines à 100 %. "
                "Exemple : 1,25 équivalent = 125 % de la capacité d'une machine. "
                "Cela ne signifie pas qu'il faut construire une fraction de bâtiment.",
                "Plafond individuel autorisé pour chaque fabricant. Il sert à réduire le "
                "nombre de machines ; ce n'est pas une consigne de surproduction.",
                "Cadence uniforme réellement appliquée à chaque fabricant après calcul du "
                "nombre entier de machines, afin d'atteindre le débit demandé.",
                "Puissance électrique cumulée de tous les fabricants de cette ligne, en MW. "
                "Elle tient compte de la cadence réelle et du modèle de consommation connu.",
            ),
        )
        self.machine_table.horizontalHeaderItem(3).setToolTip(
            "Capacité théorique exprimée en machines à 100 %. Exemple : 1,25 équivalent "
            "peut être couvert par 2 machines à 62,5 %, ou 1 machine à 125 %. "
            "Le nombre physique dépend du plafond de cadence choisi."
        )
        self.machine_table.horizontalHeaderItem(4).setToolTip(
            "Plafond de cadence autorisé par machine. Le moteur calcule le nombre "
            "entier de machines puis répartit le débit uniformément pour éviter la surproduction."
        )
        self.machine_table.horizontalHeaderItem(5).setToolTip(
            "Cadence réellement appliquée à chaque machine après dimensionnement."
        )
        self.machine_table.horizontalHeaderItem(6).setToolTip(
            "Consommation électrique cumulée des fabricants de cette ligne."
        )
        self._add_table_panel(
            "FABRICANTS NÉCESSAIRES",
            self.machine_table,
            "Équiv. à 100 % : besoin théorique en machines à pleine cadence. "
            "Exemple : 1,25 équivalent peut être couvert par 2 machines à 62,5 % "
            "ou 1 machine à 125 %. La cadence maximale sert à réduire le nombre "
            "de machines ; la cadence réelle est calculée pour éviter la surproduction.",
        )

        self.resource_table = self._create_table(
            (
                "Ressource",
                "Besoin",
                "Extracteur",
                "Machines",
                "Cadence max. / extracteur",
                "Cadence réelle / extracteur",
                "Puissance extraction",
            )
        )
        self._configure_table_columns(
            self.resource_table,
            (165, 150, 238, 82, 150, 118, 145),
        )
        self._set_header_tooltips(
            self.resource_table,
            (
                "Matière première nécessaire en entrée de la chaîne. Les ressources naturelles "
                "sont présentées comme des besoins à extraire ; les autres entrées sont "
                "signalées comme des apports externes lorsqu'aucun extracteur n'est défini.",
                "Débit à fournir à l'ensemble de la chaîne : objets/min pour les solides, "
                "m³/min pour les liquides et les gaz.",
                "Type d'extracteur compatible avec cette ressource. Le choix recalcule le "
                "nombre d'extracteurs, leur cadence et leur consommation électrique.",
                "Nombre entier d'extracteurs physiques nécessaires avec le type et le "
                "plafond de cadence sélectionnés.",
                "Plafond individuel autorisé pour chaque extracteur, entre 1 et 250 %. "
                "Le moteur peut réduire le nombre d'extracteurs en augmentant ce plafond.",
                "Cadence uniforme réellement appliquée à chaque extracteur pour satisfaire "
                "le besoin sans dépasser le débit demandé.",
                "Puissance électrique cumulée des extracteurs sélectionnés pour cette "
                "ressource, en MW.",
            ),
        )
        self.resource_table.horizontalHeaderItem(4).setToolTip(
            "Plafond de cadence autorisé par extracteur, de 1 à 250 %. "
            "Le nombre d'extracteurs et leur cadence réelle sont recalculés."
        )
        self.resource_table.horizontalHeaderItem(5).setToolTip(
            "Cadence réellement appliquée à chaque extracteur."
        )
        self.resource_table.horizontalHeaderItem(6).setToolTip(
            "Consommation électrique totale des extracteurs sélectionnés pour cette ressource."
        )
        self._add_table_panel(
            "RESSOURCES ET EXTRACTION",
            self.resource_table,
            "Choisissez l'extracteur et le plafond de cadence. Le nombre de machines, "
            "la cadence réelle et la puissance électrique sont recalculés automatiquement.",
        )

        self.byproduct_table = self._create_table(("Coproduit", "Débit généré"))
        self._set_header_tooltips(
            self.byproduct_table,
            (
                "Produit secondaire généré par une recette qui fabrique plusieurs sorties. "
                "Il est recensé séparément et n'est pas encore réutilisé automatiquement "
                "pour réduire les besoins d'une autre branche.",
                "Quantité de coproduit générée par minute. Les fluides sont exprimés en "
                "m³/min et les solides en objets/min.",
            ),
        )
        self._add_table_panel(
            "COPRODUITS GÉNÉRÉS",
            self.byproduct_table,
            "Sorties secondaires des recettes sélectionnées. Elles sont visibles dans le "
            "bilan, mais ne compensent pas encore automatiquement les besoins d'autres "
            "recettes de la chaîne.",
        )

        warning_panel = QFrame()
        warning_panel.setObjectName("SimulationPanel")
        warning_layout = QVBoxLayout(warning_panel)
        warning_layout.setContentsMargins(14, 12, 14, 12)
        warning_title = QLabel("AVERTISSEMENTS ET LIMITES DU CALCUL")
        warning_title.setObjectName("SectionLabel")
        warning_title.setToolTip(
            "Limites, hypothèses ou informations que le moteur souhaite porter à votre "
            "attention pour interpréter correctement le résultat."
        )
        self.warning_label = QLabel("Aucun avertissement.")
        self.warning_label.setObjectName("SimulationWarningText")
        self.warning_label.setWordWrap(True)
        self.warning_label.setToolTip(
            "Lisez ces messages avant d'utiliser le dimensionnement : certains éléments "
            "peuvent être estimés, non modélisés ou fournis comme entrées externes."
        )
        warning_layout.addWidget(warning_title)
        warning_layout.addWidget(self.warning_label)
        self.results_layout.addWidget(warning_panel)

        self.results_scroll.setWidget(self.results_body)
        root.addWidget(self.results_scroll, 1)
        self.results_scroll.setVisible(False)

    @staticmethod
    def _metric_card(
        label: str,
        value: str,
        tooltip: str,
    ) -> tuple[QFrame, QLabel]:
        card = QFrame()
        card.setObjectName("SimulationMetricCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(5)
        label_widget = QLabel(label)
        label_widget.setObjectName("SimulationMetricLabel")
        label_widget.setToolTip(tooltip)
        value_widget = QLabel(value)
        value_widget.setObjectName("SimulationMetricValue")
        value_widget.setWordWrap(True)
        card.setToolTip(tooltip)
        value_widget.setToolTip(tooltip)
        layout.addWidget(label_widget)
        layout.addWidget(value_widget)
        return card, value_widget

    @staticmethod
    def _create_table(headers: tuple[str, ...]) -> QTableWidget:
        table = QTableWidget(0, len(headers))
        table.setObjectName("SimulationTable")
        table.setHorizontalHeaderLabels(headers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.setShowGrid(False)
        table.setWordWrap(False)
        table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(40)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        table.horizontalHeader().setStretchLastSection(True)
        table.setMinimumHeight(110)
        table.setToolTip(
            "Tableau des résultats. Survolez un en-tête ou une cellule pour obtenir "
            "une explication de la donnée affichée."
        )
        return table

    @staticmethod
    def _set_header_tooltips(table: QTableWidget, tooltips: tuple[str, ...]) -> None:
        for index, tooltip in enumerate(tooltips):
            header = table.horizontalHeaderItem(index)
            if header is not None:
                header.setToolTip(tooltip)

    @staticmethod
    def _configure_table_columns(table: QTableWidget, widths: tuple[int, ...]) -> None:
        """Fixe des largeurs cohérentes pour éviter le décalage visuel des colonnes."""

        for index, width in enumerate(widths):
            table.setColumnWidth(index, width)

    def _add_table_panel(
        self,
        heading: str,
        table: QTableWidget,
        description: str = "",
    ) -> None:
        panel = QFrame()
        panel.setObjectName("SimulationPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 12, 14, 14)
        layout.setSpacing(9)
        title = QLabel(heading)
        title.setObjectName("SectionLabel")
        title.setToolTip(description or f"Section : {heading.casefold()}.")
        panel.setToolTip(description or f"Résultats de la section {heading.casefold()}.")
        layout.addWidget(title)
        if description:
            help_label = QLabel(description)
            help_label.setObjectName("SimulationHelpText")
            help_label.setWordWrap(True)
            help_label.setToolTip(
                f"Aide de la section {heading.casefold()} : {description}"
            )
            layout.addWidget(help_label)
        layout.addWidget(table)
        self.results_layout.addWidget(panel)

    def refresh(self) -> None:
        """Charge le catalogue à la première ouverture de la rubrique."""

        if self._catalog_loaded or self._catalog_loading:
            return
        self._start_catalog_load(self._active_locale)

    def _start_catalog_load(self, locale: str) -> None:
        if self._catalog_loading or self._plan_loading:
            return
        self._catalog_loading = True
        self._set_controls_enabled(False)
        self.status_label.setText("Chargement des produits et des recettes du catalogue…")
        worker = _SimulationCatalogWorker(self.service, locale, self)
        self._catalog_worker = worker
        worker.loaded.connect(self._on_catalog_loaded)
        worker.failed.connect(self._on_catalog_error)
        worker.finished.connect(self._on_catalog_finished)
        worker.finished.connect(worker.deleteLater)
        worker.start()

    def _on_catalog_loaded(self, payload: dict[str, Any]) -> None:
        locales = payload["locales"]
        self._active_locale = payload["locale"]
        self._targets = {item.class_name: item for item in payload["targets"]}
        self._recipes_by_product = payload["recipes_by_product"]
        self._recipes_by_class = {
            recipe.class_name: recipe
            for recipes in self._recipes_by_product.values()
            for recipe in recipes
        }

        self._restoring_controls = True
        try:
            self.locale_combo.clear()
            for locale in locales:
                index = self.locale_combo.count()
                self.locale_combo.addItem(locale, locale)
                self.locale_combo.setItemData(
                    index,
                    f"Langue du catalogue : {locale}. Les valeurs techniques restent "
                    "identiques ; seuls les noms et descriptions localisés changent.",
                    Qt.ItemDataRole.ToolTipRole,
                )
            locale_index = self.locale_combo.findData(self._active_locale)
            if locale_index >= 0:
                self.locale_combo.setCurrentIndex(locale_index)

            previous_target = self.target_combo.currentData()
            self.target_combo.clear()
            self.target_combo.addItem("Choisir un produit…", "")
            for profile in self._targets.values():
                index = self.target_combo.count()
                self.target_combo.addItem(profile.display_name, profile.class_name)
                self.target_combo.setItemData(
                    index,
                    self._target_tooltip(profile),
                    Qt.ItemDataRole.ToolTipRole,
                )
            target_index = self.target_combo.findData(previous_target)
            self.target_combo.setCurrentIndex(target_index if target_index >= 0 else 0)
        finally:
            self._restoring_controls = False

        self._catalog_loaded = True
        self._on_target_changed(self.target_combo.currentIndex())
        self._set_controls_enabled(True)
        self.status_label.setText(
            f"Catalogue prêt : {len(self._targets)} produits automatisables · "
            f"{len(locales)} langues disponibles."
        )

    def _on_catalog_error(self, message: str) -> None:
        self._catalog_loaded = False
        self._set_controls_enabled(True)
        self.status_label.setText(f"Impossible de charger le catalogue : {message}")

    def _on_catalog_finished(self) -> None:
        self._catalog_loading = False
        self._catalog_worker = None

    def _on_locale_changed(self, _index: int) -> None:
        if self._restoring_controls or not self._catalog_loaded:
            return
        locale = self.locale_combo.currentData()
        if not locale or locale == self._active_locale:
            return
        self._catalog_loaded = False
        self._extractor_choices.clear()
        self._recipe_choices.clear()
        self._producer_choices.clear()
        self._machine_clock_limits.clear()
        self._extractor_clock_limits.clear()
        self._clear_results()
        self._start_catalog_load(locale)

    def _on_target_changed(self, _index: int) -> None:
        if self._restoring_controls:
            return
        class_name = self.target_combo.currentData()
        profile = self._targets.get(class_name)
        self._extractor_choices.clear()
        self._recipe_choices.clear()
        self._producer_choices.clear()
        self._machine_clock_limits.clear()
        self._extractor_clock_limits.clear()
        self._clear_results()

        if profile is None:
            self.rate_spin.setSuffix(" /min")
            self.recipe_combo.clear()
            self.recipe_combo.addItem("Sélectionnez d'abord un produit", "")
            self.recipe_combo.setItemData(
                0,
                "Choisissez d'abord le produit final à fabriquer.",
                Qt.ItemDataRole.ToolTipRole,
            )
            self.recipe_combo.setEnabled(False)
            return

        unit = "m³" if profile.unit_label == "m³" else "objets"
        self.rate_spin.setSuffix(f" {unit}/min")
        options = self._recipes_by_product.get(class_name, ())
        self.recipe_combo.blockSignals(True)
        self.recipe_combo.clear()
        if not options:
            self.recipe_combo.addItem("Aucune recette automatisée trouvée", "")
            self.recipe_combo.setItemData(
                0,
                "Aucune recette avec fabricant automatisé n'a été trouvée pour ce produit.",
                Qt.ItemDataRole.ToolTipRole,
            )
            self.recipe_combo.setEnabled(False)
        elif len(options) == 1:
            recipe = options[0]
            self.recipe_combo.addItem(self._recipe_choice_label(recipe), recipe.class_name)
            self.recipe_combo.setItemData(
                0,
                self._recipe_details(recipe),
                Qt.ItemDataRole.ToolTipRole,
            )
            self.recipe_combo.setEnabled(False)
        else:
            self.recipe_combo.addItem("Choisir une recette…", "")
            self.recipe_combo.setItemData(
                0,
                "Sélectionnez une des recettes disponibles. Survolez chaque option pour "
                "voir les fabricants, entrées, sorties et la durée du cycle.",
                Qt.ItemDataRole.ToolTipRole,
            )
            for recipe in options:
                label = self._recipe_choice_label(recipe)
                index = self.recipe_combo.count()
                self.recipe_combo.addItem(label, recipe.class_name)
                self.recipe_combo.setItemData(
                    index,
                    self._recipe_details(recipe),
                    Qt.ItemDataRole.ToolTipRole,
                )
            self.recipe_combo.setEnabled(True)
        self.recipe_combo.blockSignals(False)

    def _calculate_plan(self, *_args: Any) -> None:
        if self._plan_loading or self._catalog_loading:
            return
        target_class = self.target_combo.currentData()
        if not target_class or target_class not in self._targets:
            self.status_label.setText("Sélectionnez un produit à fabriquer.")
            return

        options = self._recipes_by_product.get(target_class, ())
        recipe_class = self.recipe_combo.currentData()
        if len(options) > 1:
            if not recipe_class:
                self.status_label.setText(
                    "Plusieurs recettes sont disponibles : choisissez celle à utiliser."
                )
                return
            self._recipe_choices[target_class] = recipe_class
        elif len(options) == 1:
            self._recipe_choices[target_class] = options[0].class_name

        arguments = {
            "target_class_name": target_class,
            "target_rate_per_minute": Decimal(str(self.rate_spin.value())),
            "locale": self._active_locale,
            "recipe_choices": dict(self._recipe_choices),
            "producer_choices": dict(self._producer_choices),
            "extractor_choices": dict(self._extractor_choices),
            "machine_clock_limits": dict(self._machine_clock_limits),
            "extractor_clock_limits": dict(self._extractor_clock_limits),
        }
        self._plan_loading = True
        self.calculate_button.setEnabled(False)
        self.target_combo.setEnabled(False)
        self.rate_spin.setEnabled(False)
        self.locale_combo.setEnabled(False)
        self.recipe_combo.setEnabled(False)
        for table in (self.machine_table, self.resource_table):
            for row in range(table.rowCount()):
                for column in range(table.columnCount()):
                    widget = table.cellWidget(row, column)
                    if isinstance(widget, (QComboBox, QDoubleSpinBox)):
                        widget.setEnabled(False)
        self.status_label.setText("Calcul de la chaîne de production…")

        worker = _ProductionPlanWorker(self.service, arguments, self)
        self._plan_worker = worker
        worker.completed.connect(self._on_plan_completed)
        worker.finished.connect(self._on_plan_finished)
        worker.finished.connect(worker.deleteLater)
        worker.start()

    def _on_plan_completed(
        self,
        plan: ProductionPlan | None,
        error: Exception | None,
    ) -> None:
        if error is not None:
            self._current_plan = None
            self.results_scroll.setVisible(False)
            if isinstance(
                error,
                (RecipeChoiceRequiredError, ProducerChoiceRequiredError),
            ):
                self._deferred_choice_error = error
                self.status_label.setText(
                    "Le moteur a besoin d'un choix pour poursuivre la simulation."
                )
            else:
                self.status_label.setText(self._format_error(error))
            return
        if plan is None:
            self.status_label.setText("Le moteur n'a retourné aucun résultat.")
            return
        self._current_plan = plan
        self._render_plan(plan)
        self.results_scroll.setVisible(True)
        self.status_label.setText("Simulation calculée avec le catalogue local Satisfactory.")

    def _request_recipe_choice(self, error: RecipeChoiceRequiredError) -> None:
        options = [
            self._recipes_by_class[class_name]
            for class_name in error.recipe_classes
            if class_name in self._recipes_by_class
        ]
        if not options:
            self.status_label.setText(self._format_error(error))
            return

        labels: list[str] = []
        class_by_label: dict[str, str] = {}
        tooltip_by_label: dict[str, str] = {}
        for option_index, recipe in enumerate(options, start=1):
            label = self._recipe_choice_label(recipe)
            if label in class_by_label:
                label = f"Option {option_index} — {label}"
            labels.append(label)
            class_by_label[label] = recipe.class_name
            tooltip_by_label[label] = self._recipe_details(recipe)

        selected, accepted = self._show_choice_dialog(
            title="Choix d'une recette intermédiaire",
            prompt=(
                f"Plusieurs recettes peuvent produire "
                f"{self._display_name_for_class(error.item_class)}. "
                "Survolez une option pour voir ses détails. Laquelle utiliser ?"
            ),
            labels=labels,
            tooltips=tuple(tooltip_by_label[label] for label in labels),
        )
        if not accepted:
            self.status_label.setText("Simulation en attente : aucune recette choisie.")
            return
        self._recipe_choices[error.item_class] = class_by_label[selected]
        self.status_label.setText("Recette sélectionnée. Reprise du calcul…")
        QTimer.singleShot(0, self._calculate_plan)

    def _request_producer_choice(self, error: ProducerChoiceRequiredError) -> None:
        recipe = self._recipes_by_class.get(error.recipe_class or "")
        if recipe is None or not error.producer_classes:
            self.status_label.setText(self._format_error(error))
            return

        producers = {
            producer.class_name: producer
            for producer in recipe.producers
            if producer.producer_type == "manufacturer"
            and producer.class_name in error.producer_classes
        }
        if not producers:
            self.status_label.setText(self._format_error(error))
            return

        label_to_class: dict[str, str] = {}
        tooltip_by_label: dict[str, str] = {}
        labels = []
        ordered_producers = sorted(producers.items())
        display_counts: dict[str, int] = {}
        for _class_name, producer in ordered_producers:
            display_counts[producer.display_name] = display_counts.get(producer.display_name, 0) + 1
        for index, (class_name, producer) in enumerate(ordered_producers, start=1):
            label = producer.display_name
            if display_counts[label] > 1:
                label = f"{label} · option {index}"
            labels.append(label)
            label_to_class[label] = class_name
            tooltip_by_label[label] = (
                f"Fabricant : {producer.display_name}\n"
                f"Description : {producer.description or 'Aucune description fournie.'}\n"
                f"Recette concernée : {recipe.display_name}."
            )

        selected, accepted = self._show_choice_dialog(
            title="Choix d'un fabricant",
            prompt=(
                f"Plusieurs fabricants peuvent exécuter {recipe.display_name}. "
                "Survolez une option pour afficher sa description."
            ),
            labels=labels,
            tooltips=tuple(tooltip_by_label[label] for label in labels),
        )
        if not accepted:
            self.status_label.setText("Simulation en attente : aucun fabricant choisi.")
            return
        self._producer_choices[recipe.class_name] = label_to_class[selected]
        self.status_label.setText("Fabricant sélectionné. Reprise du calcul…")
        QTimer.singleShot(0, self._calculate_plan)

    def _show_choice_dialog(
        self,
        *,
        title: str,
        prompt: str,
        labels: list[str],
        tooltips: tuple[str, ...],
    ) -> tuple[str, bool]:
        """Affiche un choix dont chaque option possède son info-bulle."""

        dialog = QInputDialog(self)
        dialog.setWindowTitle(title)
        dialog.setToolTip(f"{title}. {prompt}")
        dialog.setLabelText(prompt)
        prompt_label = dialog.findChild(QLabel)
        if prompt_label is not None:
            prompt_label.setToolTip(prompt)
        dialog.setComboBoxItems(labels)
        dialog.setComboBoxEditable(False)
        for button in dialog.findChildren(QPushButton):
            button.setToolTip(
                "Confirmer ce choix ou fermer la fenêtre sans appliquer de sélection."
            )
        combo = dialog.findChild(QComboBox)
        if combo is not None:
            combo.setToolTip("Survolez une option pour lire son détail.")
            for index, tooltip in enumerate(tooltips):
                combo.setItemData(index, tooltip, Qt.ItemDataRole.ToolTipRole)
        accepted = dialog.exec() == QDialog.DialogCode.Accepted
        return dialog.textValue(), accepted

    def _on_plan_finished(self) -> None:
        self._plan_loading = False
        self._plan_worker = None
        self.calculate_button.setEnabled(True)
        self.target_combo.setEnabled(self._catalog_loaded)
        self.rate_spin.setEnabled(self._catalog_loaded)
        self.locale_combo.setEnabled(self._catalog_loaded)
        self.recipe_combo.setEnabled(
            self._catalog_loaded
            and len(self._recipes_by_product.get(self.target_combo.currentData(), ())) > 1
        )
        for table in (self.machine_table, self.resource_table):
            for row in range(table.rowCount()):
                for column in range(table.columnCount()):
                    widget = table.cellWidget(row, column)
                    if isinstance(widget, (QComboBox, QDoubleSpinBox)):
                        widget.setEnabled(True)
        if self._deferred_choice_error is not None:
            QTimer.singleShot(0, self._resolve_deferred_choice)

    def _resolve_deferred_choice(self) -> None:
        error = self._deferred_choice_error
        self._deferred_choice_error = None
        if isinstance(error, RecipeChoiceRequiredError):
            self._request_recipe_choice(error)
        elif isinstance(error, ProducerChoiceRequiredError):
            self._request_producer_choice(error)

    @staticmethod
    def _format_error(error: Exception) -> str:
        if isinstance(error, RecipeChoiceRequiredError):
            return f"Choix de recette nécessaire : {error}"
        if isinstance(error, ProductionCalculationError):
            return f"Calcul impossible : {error}"
        if isinstance(error, FileNotFoundError):
            return f"Catalogue indisponible : {error}"
        return f"Erreur pendant la simulation ({type(error).__name__}) : {error}"

    def _render_plan(self, plan: ProductionPlan) -> None:
        target_rate_text = (
            f"{self._format_decimal(plan.target_rate_per_minute)} "
            f"{self._plural_unit(plan.target_unit_label)}/min"
        )
        self.target_metric[1].setText(f"{plan.target_name} · {target_rate_text}")
        self.target_metric[1].setToolTip(
            f"Produit final : {plan.target_name}\n"
            f"Débit demandé : {target_rate_text}\n"
            "Il s'agit de l'objectif de sortie de la chaîne, et non du débit d'une machine isolée."
        )

        machine_count = sum(item.machine_count for item in plan.machine_requirements)
        self.machine_metric[1].setText(str(machine_count))
        machine_breakdown: dict[str, int] = {}
        for requirement in plan.machine_requirements:
            machine_breakdown[requirement.producer_name] = (
                machine_breakdown.get(requirement.producer_name, 0)
                + requirement.machine_count
            )
        breakdown_text = "\n".join(
            f"{name} : {count}" for name, count in sorted(machine_breakdown.items())
        ) or "Aucun fabricant requis."
        self.machine_metric[1].setToolTip(
            f"Total : {machine_count} bâtiment(s) de fabrication.\n"
            "Les extracteurs ne sont pas inclus dans ce compteur.\n\n"
            f"Détail par fabricant :\n{breakdown_text}"
        )

        total_power_text = self._format_power(
            plan.total_power_min_mw,
            plan.total_power_max_mw,
            plan.power_estimate_complete,
        )
        self.power_metric[1].setText(total_power_text)
        production_power_text = self._format_power(
            plan.production_power_min_mw,
            plan.production_power_max_mw,
            True,
        )
        extraction_power_text = self._format_power(
            plan.extraction_power_min_mw,
            plan.extraction_power_max_mw,
            True,
        )
        power_tooltip = (
            f"Puissance totale affichée : {total_power_text}.\n\n"
            f"Fabrication (données disponibles) : {production_power_text}.\n"
            f"Extraction (données disponibles) : {extraction_power_text}.\n\n"
            "Les puissances de fabrication et d'extraction sont additionnées. "
            "Si le catalogue ne renseigne pas la consommation d'un équipement, "
            "le total global peut être indiqué comme indéterminé. Consultez les avertissements."
        )
        self.power_metric[1].setToolTip(power_tooltip)

        self.machine_table.setRowCount(0)
        for requirement in plan.machine_requirements:
            row = self.machine_table.rowCount()
            self.machine_table.insertRow(row)
            values = (
                requirement.recipe_name,
                requirement.producer_name,
                str(requirement.machine_count),
                self._format_decimal(requirement.machine_equivalents),
                "",
                f"{self._format_decimal(requirement.clock_percent)} %",
                self._format_power(
                    requirement.power_min_mw,
                    requirement.power_max_mw,
                    requirement.power_min_mw is not None
                    and requirement.power_max_mw is not None,
                ),
            )
            self._set_table_row(
                self.machine_table,
                row,
                values,
                center_columns={2, 3, 4, 5, 6},
            )
            recipe = self._recipes_by_class.get(requirement.recipe_class)
            recipe_tooltip = (
                self._recipe_details(recipe)
                if recipe is not None
                else f"Recette utilisée : {requirement.recipe_name}."
            )
            machine_power_text = self._format_power(
                requirement.power_min_mw,
                requirement.power_max_mw,
                requirement.power_min_mw is not None
                and requirement.power_max_mw is not None,
            )
            producer_description = ""
            if recipe is not None:
                producer = next(
                    (
                        option
                        for option in recipe.producers
                        if option.class_name == requirement.producer_class
                    ),
                    None,
                )
                if producer is not None and producer.description.strip():
                    producer_description = f"\nDescription : {producer.description.strip()}"
            self._set_row_tooltips(
                self.machine_table,
                row,
                (
                    recipe_tooltip,
                    f"Fabricant : {requirement.producer_name}\n"
                    "Bâtiment qui exécute cette recette."
                    f"{producer_description}",
                    f"{requirement.machine_count} bâtiment(s) physique(s) sont nécessaires "
                    "avec le plafond de cadence choisi.",
                    f"Besoin théorique : {self._format_decimal(requirement.machine_equivalents)} "
                    "machine(s) à 100 %. Cette valeur peut être fractionnaire car elle exprime "
                    "une capacité, pas un nombre de bâtiments à construire.",
                    "Réglez le plafond individuel entre 1 et 250 %. Le moteur recalcule le "
                    "nombre entier de fabricants puis répartit la cadence réelle uniformément.",
                    f"Chaque fabricant fonctionne à "
                    f"{self._format_decimal(requirement.clock_percent)} %. "
                    "Cette cadence réelle est calculée pour atteindre le débit demandé "
                    "sans surplus.",
                    f"Puissance cumulée pour {requirement.machine_count} fabricant(s) : "
                    f"{machine_power_text}. "
                    "La puissance dépend de la cadence réelle et du modèle électrique du bâtiment.",
                ),
            )
            clock_spin = self._create_clock_spin(
                requirement.clock_limit_percent,
                "Plafond maximal de cadence par fabricant (1 à 250 %). Ce n'est pas la "
                "cadence qui sera imposée à chaque bâtiment : après votre réglage, le moteur "
                "recalcule le nombre de fabricants et leur cadence réelle uniforme pour "
                "atteindre exactement le débit demandé.",
            )
            clock_spin.editingFinished.connect(
                lambda key=requirement.recipe_class, spin=clock_spin:
                self._on_machine_clock_limit_changed(key, spin)
            )
            self.machine_table.setCellWidget(row, 4, clock_spin)

        self.resource_table.setRowCount(0)
        for resource in plan.resource_requirements:
            row = self.resource_table.rowCount()
            self.resource_table.insertRow(row)
            self._set_table_item(
                self.resource_table,
                row,
                0,
                resource.display_name,
                tooltip=(
                    f"Ressource : {resource.display_name}.\n"
                    f"Besoin brut de la chaîne : {self._format_decimal(resource.rate_per_minute)} "
                    f"{self._plural_unit(resource.unit_label)}/min.\n"
                    + (
                        "Cette ressource est extraite directement depuis un gisement ou un puits."
                        if resource.is_game_resource
                        else "Cette entrée doit être fournie par une source externe au calcul."
                    )
                ),
            )
            self._set_table_item(
                self.resource_table,
                row,
                1,
                f"{self._format_decimal(resource.rate_per_minute)} "
                f"{self._plural_unit(resource.unit_label)}/min",
                tooltip=(
                    f"Besoin total de {resource.display_name} pour toutes les branches "
                    f"de la chaîne : {self._format_decimal(resource.rate_per_minute)} "
                    f"{self._plural_unit(resource.unit_label)}/min.\n"
                    "Multiplicateur de rendement appliqué : "
                    f"x{self._format_decimal(resource.node_yield_multiplier)}. "
                    "La pureté du gisement n'est pas encore réglable dans cette page."
                ),
                center=True,
            )
            selected_option = next(
                (
                    option
                    for option in resource.extraction_options
                    if option.extractor_class == resource.selected_extractor_class
                ),
                None,
            )
            if resource.extraction_options:
                selector = QComboBox(self.resource_table)
                selector.setObjectName("SimulationInlineSelector")
                selector.setMinimumContentsLength(20)
                selector.setToolTip(
                    "Choisissez le bâtiment qui extrait cette ressource. Chaque option "
                    "indique sa capacité nominale et les contraintes particulières. "
                    "Le nombre de machines, la cadence et la puissance seront recalculés."
                )
                for option in resource.extraction_options:
                    index = selector.count()
                    selector.addItem(option.extractor_name, option.extractor_class)
                    option_lines = [
                        f"Extracteur : {option.extractor_name}",
                        "Capacité nominale à 100 % : "
                        f"{self._format_decimal(option.base_rate_per_minute)} "
                        f"{self._plural_unit(resource.unit_label)}/min.",
                        "Capacité effective par machine : "
                        f"{self._format_decimal(option.effective_rate_per_minute)} "
                        f"{self._plural_unit(resource.unit_label)}/min.",
                        f"Dimensionnement proposé : {option.machine_count} machine(s) à "
                        f"{self._format_decimal(option.clock_percent)} %.",
                        "Puissance cumulée : "
                        + self._format_power(
                            option.power_min_mw,
                            option.power_max_mw,
                            option.power_min_mw is not None and option.power_max_mw is not None,
                        )
                        + ".",
                    ]
                    if option.requires_resource_well:
                        option_lines.append(
                            "Cet extracteur utilise un puits de ressources ; le pressuriseur "
                            "et la capacité globale du puits ne sont pas dimensionnés ici."
                        )
                    selector.setItemData(
                        index,
                        "\n".join(option_lines),
                        Qt.ItemDataRole.ToolTipRole,
                    )
                selected_index = selector.findData(resource.selected_extractor_class)
                selector.setCurrentIndex(max(0, selected_index))
                selector.currentIndexChanged.connect(
                    lambda _index, key=resource.class_name, combo=selector:
                    self._on_extractor_changed(key, combo)
                )
                self.resource_table.setCellWidget(row, 2, selector)

                machine_count_text = str(selected_option.machine_count) if selected_option else "—"
                clock_text = (
                    f"{self._format_decimal(selected_option.clock_percent)} %"
                    if selected_option else "—"
                )
                power_text = (
                    self._format_power(
                        selected_option.power_min_mw,
                        selected_option.power_max_mw,
                        selected_option.power_min_mw is not None
                        and selected_option.power_max_mw is not None,
                    )
                    if selected_option else "Non déterminée"
                )
                if selected_option is not None:
                    clock_spin = self._create_clock_spin(
                        selected_option.clock_limit_percent,
                        "Plafond maximal de cadence par extracteur (1 à 250 %). Ce n'est pas "
                        "la cadence imposée : le moteur recalcule le nombre entier "
                        "d'extracteurs et leur cadence réelle uniforme pour couvrir le besoin. "
                        "Un plafond plus élevé peut réduire le nombre de bâtiments nécessaires.",
                    )
                    clock_spin.editingFinished.connect(
                        lambda key=resource.class_name, spin=clock_spin:
                        self._on_extractor_clock_limit_changed(key, spin)
                    )
                    self.resource_table.setCellWidget(row, 4, clock_spin)
            else:
                self._set_table_item(
                    self.resource_table,
                    row,
                    2,
                    "À fournir / externe",
                    tooltip=(
                        "Aucun profil d'extracteur compatible n'est disponible dans le catalogue. "
                        "Cette matière est considérée comme une entrée externe à fournir."
                    ),
                )
                self._set_table_item(
                    self.resource_table,
                    row,
                    4,
                    "—",
                    tooltip="Aucun extracteur n'est dimensionné pour cette entrée externe.",
                    center=True,
                )
                machine_count_text = "—"
                clock_text = "—"
                power_text = "—"
            self._set_table_item(
                self.resource_table,
                row,
                3,
                machine_count_text,
                tooltip=(
                    f"Nombre entier d'extracteurs sélectionnés pour fournir "
                    f"{self._format_decimal(resource.rate_per_minute)} "
                    f"{self._plural_unit(resource.unit_label)}/min."
                ),
                center=True,
            )
            # La cellule cadence réelle a déjà été créée ; son info-bulle est spécifique.
            self._set_table_item(
                self.resource_table,
                row,
                5,
                clock_text,
                tooltip=(
                    "Cadence uniforme réellement appliquée à chaque extracteur. "
                    "Elle est calculée à partir du besoin, du nombre d'extracteurs "
                    "et du plafond maximum réglé."
                ),
                center=True,
            )
            self._set_table_item(
                self.resource_table,
                row,
                6,
                power_text,
                tooltip=(
                    f"Puissance électrique cumulée des extracteurs affectés à "
                    f"{resource.display_name}. Valeur : {power_text}."
                ),
                center=True,
            )

        self.byproduct_table.setRowCount(0)
        for product in plan.byproducts:
            row = self.byproduct_table.rowCount()
            self.byproduct_table.insertRow(row)
            self._set_table_row(
                self.byproduct_table,
                row,
                (
                    product.display_name,
                    f"{self._format_decimal(product.rate_per_minute)} "
                    f"{self._plural_unit(product.unit_label)}/min",
                ),
                center_columns={1},
            )
            self._set_row_tooltips(
                self.byproduct_table,
                row,
                (
                    f"Coproduit : {product.display_name}\n"
                    "Produit secondaire généré par une recette qui possède plusieurs sorties.",
                    f"Débit de coproduit : {self._format_decimal(product.rate_per_minute)} "
                    f"{self._plural_unit(product.unit_label)}/min. Il est comptabilisé séparément "
                    "et ne réduit pas automatiquement les besoins d'autres branches.",
                ),
            )
        if not plan.byproducts:
            self.byproduct_table.insertRow(0)
            self._set_table_item(
                self.byproduct_table,
                0,
                0,
                "Aucun coproduit déclaré",
                tooltip="Aucune recette sélectionnée ne déclare de produit secondaire.",
            )
            self._set_table_item(
                self.byproduct_table,
                0,
                1,
                "—",
                tooltip="Aucun débit de coproduit à afficher pour cette simulation.",
            )

        self.warning_label.setText(
            "\n".join(f"• {warning}" for warning in plan.warnings)
            if plan.warnings else "Aucun avertissement pour cette simulation."
        )
        for table in (self.machine_table, self.resource_table, self.byproduct_table):
            table.resizeRowsToContents()

    @staticmethod
    def _create_clock_spin(value: Decimal, tooltip: str) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setObjectName("SimulationClockSpin")
        spin.setRange(1.0, 250.0)
        spin.setDecimals(1)
        spin.setSingleStep(5.0)
        spin.setKeyboardTracking(False)
        spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        spin.setSuffix(" %")
        spin.setValue(float(value))
        spin.setToolTip(tooltip)
        spin.setMinimumWidth(105)
        return spin

    def _on_machine_clock_limit_changed(
        self,
        recipe_class: str,
        spin: QDoubleSpinBox,
    ) -> None:
        self._machine_clock_limits[recipe_class] = Decimal(str(spin.value()))
        self._calculate_plan()

    def _on_extractor_clock_limit_changed(
        self,
        resource_class: str,
        spin: QDoubleSpinBox,
    ) -> None:
        self._extractor_clock_limits[resource_class] = Decimal(str(spin.value()))
        self._calculate_plan()

    def _on_extractor_changed(self, resource_class: str, selector: QComboBox) -> None:
        selected = selector.currentData()
        if selected:
            self._extractor_choices[resource_class] = selected
            self._calculate_plan()

    def _clear_results(self) -> None:
        self._current_plan = None
        self.results_scroll.setVisible(False)
        self.status_label.setText(
            "Choisissez un produit et un débit, puis lancez le calcul."
        )

    def _set_controls_enabled(self, enabled: bool) -> None:
        self.target_combo.setEnabled(enabled)
        self.rate_spin.setEnabled(enabled)
        self.locale_combo.setEnabled(enabled)
        options = self._recipes_by_product.get(self.target_combo.currentData(), ())
        self.recipe_combo.setEnabled(enabled and len(options) > 1)
        self.calculate_button.setEnabled(enabled and self._catalog_loaded)

    def shutdown(self) -> None:
        """Attend la fin d'un éventuel chargement avant la fermeture de l'application."""

        for worker in (self._catalog_worker, self._plan_worker):
            if worker is not None and worker.isRunning():
                worker.wait()

    @staticmethod
    def _set_row_tooltips(
        table: QTableWidget,
        row: int,
        tooltips: tuple[str, ...],
    ) -> None:
        for column, tooltip in enumerate(tooltips):
            item = table.item(row, column)
            if item is not None and tooltip:
                item.setToolTip(tooltip)

    @staticmethod
    def _set_table_item(
        table: QTableWidget,
        row: int,
        column: int,
        text: str,
        tooltip: str = "",
        *,
        center: bool = False,
    ) -> None:
        item = QTableWidgetItem(text)
        if tooltip:
            item.setToolTip(tooltip)
        alignment = Qt.AlignmentFlag.AlignVCenter
        alignment |= (
            Qt.AlignmentFlag.AlignHCenter
            if center
            else Qt.AlignmentFlag.AlignLeft
        )
        item.setTextAlignment(alignment)
        table.setItem(row, column, item)

    @classmethod
    def _set_table_row(
        cls,
        table: QTableWidget,
        row: int,
        values: tuple[str, ...],
        *,
        center_columns: set[int] | None = None,
    ) -> None:
        centered = center_columns or set()
        for column, value in enumerate(values):
            cls._set_table_item(
                table,
                row,
                column,
                value,
                center=column in centered,
            )

    def _display_name_for_class(self, class_name: str) -> str:
        """Retourne un nom localisé sans exposer l'identifiant technique."""

        target = self._targets.get(class_name)
        if target is not None:
            return target.display_name
        for recipe in self._recipes_by_class.values():
            for component in (*recipe.ingredients, *recipe.products):
                if component.class_name == class_name:
                    return component.display_name
        return "ce composant"

    def _target_tooltip(self, profile: ItemProfile) -> str:
        """Construit une aide de sélection du produit final."""

        lines = [
            f"Produit : {profile.display_name}",
            f"Unité de sortie : {profile.unit_label}/min.",
        ]
        if profile.description.strip():
            lines.extend(("", profile.description.strip()))
        recipes = self._recipes_by_product.get(profile.class_name, ())
        lines.extend(("", f"Recettes automatisées disponibles : {len(recipes)}."))
        if len(recipes) > 1:
            lines.append("Un choix de recette sera nécessaire avant le calcul.")
        return "\n".join(lines)

    @classmethod
    def _component_choice_label(cls, component: RecipeComponent) -> str:
        amount = cls._format_decimal(component.amount)
        unit = "m³" if component.is_fluid else "objets"
        return f"{amount} {unit} {component.display_name}"

    @classmethod
    def _recipe_details(cls, recipe: Recipe) -> str:
        def describe_components(components: tuple[RecipeComponent, ...]) -> str:
            if not components:
                return "Aucun"
            descriptions = []
            for component in components:
                line = cls._component_choice_label(component)
                if component.description.strip():
                    line += f" — {component.description.strip()}"
                descriptions.append(line)
            return "\n  • ".join(descriptions)

        producers = "\n  • ".join(recipe.producer_names) or "Fabricant non précisé"
        recipe_type = {
            "default": "Standard",
            "alternate": "Alternative",
        }.get(recipe.recipe_type.casefold(), recipe.recipe_type or "Non précisé")
        lines = [
            f"Recette : {recipe.display_name}",
            f"Durée d'un cycle : {cls._format_decimal(recipe.duration_seconds)} s.",
            f"Fabricants compatibles :\n  • {producers}",
            f"Ingrédients consommés par cycle :\n  • {describe_components(recipe.ingredients)}",
            f"Produits obtenus par cycle :\n  • {describe_components(recipe.products)}",
            f"Type de recette : {recipe_type}",
        ]
        if recipe.description.strip():
            lines.insert(1, f"Description : {recipe.description.strip()}")
        return "\n\n".join(lines)

    @classmethod
    def _recipe_choice_label(cls, recipe: Recipe) -> str:
        ingredients = " + ".join(
            cls._component_choice_label(component)
            for component in recipe.ingredients
        ) or "Aucun ingrédient"
        products = " + ".join(
            cls._component_choice_label(component)
            for component in recipe.products
        ) or "Aucun produit"
        producers = ", ".join(recipe.producer_names)
        producer_part = f" — {producers}" if producers else ""
        return f"{recipe.display_name}{producer_part} | {ingredients} → {products}"

    @staticmethod
    def _plural_unit(unit_label: str) -> str:
        return "objets" if unit_label == "objet" else unit_label

    @staticmethod
    def _format_decimal(value: Decimal) -> str:
        rounded = value.quantize(Decimal("0.01"))
        text = format(rounded, "f").rstrip("0").rstrip(".")
        return text or "0"

    @staticmethod
    def _format_power_value(value: Decimal) -> str:
        return f"{value.quantize(Decimal('0.01')):.2f} MW"

    @classmethod
    def _format_power(
        cls,
        minimum: Decimal | None,
        maximum: Decimal | None,
        complete: bool,
    ) -> str:
        if minimum is None or maximum is None:
            return "Non déterminée"
        if not complete:
            return f"≥ {cls._format_decimal(minimum)} MW · estimation partielle"
        if minimum == maximum:
            return cls._format_power_value(minimum)
        return f"{cls._format_power_value(minimum)}–{cls._format_power_value(maximum)}"
