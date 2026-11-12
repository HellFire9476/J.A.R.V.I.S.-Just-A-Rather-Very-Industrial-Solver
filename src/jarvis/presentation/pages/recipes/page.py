"""Explorateur des recettes Satisfactory avec chargement non bloquant."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, QThread, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QScrollArea,
    QSplitter,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from jarvis.application.services.recipe_service import RecipeService
from jarvis.domain.entities.recipe import Recipe, RecipeComponent, RecipeProducer

_INVALID_MODEL_INDEX = QModelIndex()


class _RecipeTableModel(QAbstractTableModel):
    """Modèle virtuel : les cellules sont calculées à la demande par Qt."""

    HEADERS = ("Recette", "Famille", "Produits par cycle", "Cycle")

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._recipes: list[Recipe] = []

    def rowCount(self, parent: QModelIndex = _INVALID_MODEL_INDEX) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._recipes)

    def columnCount(self, parent: QModelIndex = _INVALID_MODEL_INDEX) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self.HEADERS)

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:  # noqa: N802
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal and 0 <= section < len(self.HEADERS):
            return self.HEADERS[section]
        return str(section + 1) if orientation == Qt.Orientation.Vertical else None

    def data(
        self,
        index: QModelIndex,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._recipes)):
            return None

        recipe = self._recipes[index.row()]
        if role == Qt.ItemDataRole.UserRole:
            return recipe.class_name
        if role == Qt.ItemDataRole.TextAlignmentRole and index.column() == 3:
            return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        if role != Qt.ItemDataRole.DisplayRole:
            return None

        if index.column() == 0:
            return recipe.display_name
        if index.column() == 1:
            return RecipesPage.TYPE_LABELS.get(
                recipe.recipe_type,
                RecipesPage.TYPE_LABELS["unknown"],
            )
        if index.column() == 2:
            return RecipesPage._format_components_inline(recipe.products)
        if index.column() == 3:
            return f"{RecipesPage._format_decimal(recipe.duration_seconds)} s"
        return None

    def set_recipes(self, recipes: list[Recipe]) -> None:
        self.beginResetModel()
        self._recipes = recipes
        self.endResetModel()


class _RecipeLoadThread(QThread):
    """Lit et interprète le catalogue hors du thread graphique."""

    loaded = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        service: RecipeService,
        requested_locale: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._service = service
        self._requested_locale = requested_locale

    def run(self) -> None:
        try:
            locales = self._service.list_locales()
            if not locales:
                raise ValueError("Aucune langue n'est installée dans le catalogue.")

            locale = self._requested_locale
            if locale not in locales:
                locale = "fr" if "fr" in locales else (
                    "en-US" if "en-US" in locales else locales[0]
                )

            recipes = self._service.list_recipes(locale)
            summary = self._service.get_catalog_summary()
            self.loaded.emit(
                {
                    "locale": locale,
                    "locales": locales,
                    "recipes": recipes,
                    "summary": summary,
                }
            )
        except Exception as exc:  # l'erreur est remontée dans l'interface, pas bloquée
            self.failed.emit(f"{type(exc).__name__}: {exc}")


class RecipesPage(QWidget):
    """Recherche, filtrage et consultation détaillée des recettes du jeu."""

    TYPE_LABELS = {
        "all": "Tous les types",
        "production": "Fabrication automatisée",
        "construction": "Construction",
        "workshop": "Atelier d'équipement",
        "workbench": "Établi",
        "unknown": "Fabricant non identifié",
    }

    def __init__(
        self,
        service: RecipeService | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.service = service or RecipeService()
        self._all_recipes: list[Recipe] = []
        self._filtered_recipes: list[Recipe] = []
        self._recipes_by_id: dict[str, Recipe] = {}
        self._recipes_cache: dict[str, list[Recipe]] = {}
        self._locales: list[str] = []
        self._locale = "fr"
        self._loading = False
        self._loaded = False
        self._load_error: str | None = None
        self._loading_locale: str | None = None
        self._load_thread: _RecipeLoadThread | None = None

        self._build_ui()
        # Le chargement est volontairement déclenché par MainWindow.show_page()
        # à la première ouverture, jamais pendant la construction de la fenêtre.

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(16)

        title = QLabel("Catalogue des recettes")
        title.setObjectName("PageTitle")

        subtitle = QLabel(
            "Consultez les ingrédients, les produits, les durées de cycle et les "
            "fabricants autorisés. Les liquides et les gaz sont affichés en m³, "
            "jamais en litres internes bruts."
        )
        subtitle.setObjectName("PageSubtitle")
        subtitle.setWordWrap(True)

        root.addWidget(title)
        root.addWidget(subtitle)

        units_note = QLabel(
            "Unités : solides en objets par cycle ; liquides et gaz en m³ par cycle. "
            "Pour les fabrications automatisées, le débit théorique à 100 % est "
            "également indiqué en unités/min ou m³/min."
        )
        units_note.setObjectName("CatalogMuted")
        units_note.setWordWrap(True)
        units_note.setToolTip(
            "Les exports du jeu stockent les fluides en litres internes. "
            "J.A.R.V.I.S. les convertit en mètres cubes (division par 1 000)."
        )
        root.addWidget(units_note)

        summary = QFrame()
        summary.setObjectName("CatalogSummary")
        summary_layout = QHBoxLayout(summary)
        summary_layout.setContentsMargins(16, 10, 16, 10)
        summary_layout.setSpacing(24)

        self.recipe_count_label = QLabel("0 recette")
        self.recipe_count_label.setObjectName("CatalogSummaryValue")
        self.class_count_label = QLabel("Catalogue non chargé")
        self.class_count_label.setObjectName("CatalogSummaryText")
        self.locale_count_label = QLabel("0 langue")
        self.locale_count_label.setObjectName("CatalogSummaryText")

        summary_layout.addWidget(self.recipe_count_label)
        summary_layout.addWidget(self.class_count_label)
        summary_layout.addStretch()
        summary_layout.addWidget(self.locale_count_label)
        root.addWidget(summary)

        toolbar = QFrame()
        toolbar.setObjectName("CatalogToolbar")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(12, 10, 12, 10)
        toolbar_layout.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setObjectName("CatalogSearch")
        self.search_input.setPlaceholderText(
            "Rechercher un nom, une description, un ingrédient ou un fabricant…"
        )
        self.search_input.setToolTip(
            "La recherche porte sur les recettes, les composants, leurs descriptions "
            "et les fabricants compatibles."
        )
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._apply_filters)

        self.type_filter = QComboBox()
        self.type_filter.setObjectName("CatalogFilter")
        self.type_filter.setToolTip(
            "Filtre les recettes par mode de fabrication : machine, construction, "
            "établi ou atelier d'équipement."
        )
        for type_id, label in self.TYPE_LABELS.items():
            self.type_filter.addItem(label, type_id)
        self.type_filter.currentIndexChanged.connect(self._apply_filters)

        self.producer_filter = QComboBox()
        self.producer_filter.setObjectName("CatalogFilter")
        self.producer_filter.setToolTip(
            "Affiche uniquement les recettes réalisables dans le fabricant sélectionné."
        )
        self.producer_filter.addItem("Tous les fabricants", "")
        self.producer_filter.currentIndexChanged.connect(self._apply_filters)

        self.locale_filter = QComboBox()
        self.locale_filter.setObjectName("CatalogFilter")
        self.locale_filter.setToolTip(
            "Langue des noms et descriptions provenant du catalogue Satisfactory."
        )
        self.locale_filter.currentIndexChanged.connect(self._change_locale)

        toolbar_layout.addWidget(self.search_input, 1)
        toolbar_layout.addWidget(self.type_filter)
        toolbar_layout.addWidget(self.producer_filter)
        toolbar_layout.addWidget(self.locale_filter)
        root.addWidget(toolbar)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        table_panel = QFrame()
        table_panel.setObjectName("CatalogPanel")
        table_layout = QVBoxLayout(table_panel)
        table_layout.setContentsMargins(14, 14, 14, 14)
        table_layout.setSpacing(10)

        table_heading = QLabel("RECETTES DISPONIBLES")
        table_heading.setObjectName("SectionLabel")
        table_layout.addWidget(table_heading)

        self.recipe_table = QTableView()
        self.recipe_table.setObjectName("CatalogTable")
        self.recipe_model = _RecipeTableModel(self.recipe_table)
        self.recipe_table.setModel(self.recipe_model)
        self.recipe_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.recipe_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.recipe_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.recipe_table.setAlternatingRowColors(True)
        self.recipe_table.setShowGrid(False)
        self.recipe_table.verticalHeader().setVisible(False)
        self.recipe_table.verticalHeader().setDefaultSectionSize(38)
        self.recipe_table.horizontalHeader().setStretchLastSection(False)
        self.recipe_table.horizontalHeader().setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.Stretch,
        )
        self.recipe_table.horizontalHeader().setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        self.recipe_table.horizontalHeader().setSectionResizeMode(
            2,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        self.recipe_table.horizontalHeader().setSectionResizeMode(
            3,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        self.recipe_table.selectionModel().currentRowChanged.connect(
            self._on_current_row_changed
        )
        table_layout.addWidget(self.recipe_table, 1)

        self.table_status = QLabel("Le catalogue sera chargé à l'ouverture de cette page.")
        self.table_status.setObjectName("CatalogMuted")
        self.table_status.setWordWrap(True)
        table_layout.addWidget(self.table_status)

        detail_panel = QFrame()
        detail_panel.setObjectName("CatalogPanel")
        detail_layout = QVBoxLayout(detail_panel)
        detail_layout.setContentsMargins(18, 18, 18, 18)
        detail_layout.setSpacing(12)

        detail_eyebrow = QLabel("FICHE RECETTE")
        detail_eyebrow.setObjectName("Eyebrow")
        self.detail_title = QLabel("Sélectionnez une recette")
        self.detail_title.setObjectName("CatalogDetailTitle")
        self.detail_title.setWordWrap(True)
        self.detail_class = QLabel("Identifiant interne : —")
        self.detail_class.setObjectName("CatalogMuted")
        self.detail_class.setWordWrap(True)

        self.detail_description_heading = QLabel("RÉSUMÉ TECHNIQUE CALCULÉ")
        self.detail_description_heading.setObjectName("SectionLabel")
        self.detail_description = QLabel(
            "Sélectionnez une recette pour afficher son résumé technique."
        )
        self.detail_description.setObjectName("CatalogDetailText")
        self.detail_description.setWordWrap(True)
        self.detail_description.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self.detail_duration = QLabel("Durée du cycle : —")
        self.detail_duration.setObjectName("CatalogDetailMetric")

        detail_layout.addWidget(detail_eyebrow)
        detail_layout.addWidget(self.detail_title)
        detail_layout.addWidget(self.detail_class)
        detail_layout.addWidget(self.detail_description_heading)
        detail_layout.addWidget(self.detail_description)
        detail_layout.addWidget(self.detail_duration)
        detail_layout.addWidget(self._separator())

        self.ingredients_label = self._add_detail_section(
            detail_layout,
            "INGRÉDIENTS CONSOMMÉS PAR CYCLE",
        )
        detail_layout.addWidget(self._separator())
        self.products_label = self._add_detail_section(
            detail_layout,
            "PRODUITS FABRIQUÉS PAR CYCLE",
        )
        detail_layout.addWidget(self._separator())
        self.producers_label = self._add_detail_section(
            detail_layout,
            "FABRICANTS ET POSTES COMPATIBLES",
        )
        detail_layout.addStretch()

        detail_scroll = QScrollArea()
        detail_scroll.setObjectName("CatalogDetailScroll")
        detail_scroll.setWidgetResizable(True)
        detail_scroll.setFrameShape(QFrame.Shape.NoFrame)
        detail_scroll.setWidget(detail_panel)

        splitter.addWidget(table_panel)
        splitter.addWidget(detail_scroll)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([680, 430])
        root.addWidget(splitter, 1)
        self._set_controls_enabled(False)

    @staticmethod
    def _separator() -> QFrame:
        separator = QFrame()
        separator.setObjectName("CatalogSeparator")
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Plain)
        return separator

    @staticmethod
    def _add_detail_section(layout: QVBoxLayout, heading: str) -> QLabel:
        title = QLabel(heading)
        title.setObjectName("SectionLabel")
        value = QLabel("—")
        value.setObjectName("CatalogDetailText")
        value.setWordWrap(True)
        value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(title)
        layout.addWidget(value)
        return value

    def refresh(self) -> None:
        """Charge le catalogue une seule fois, sans bloquer le thread graphique."""

        if self._loaded or self._loading:
            return
        if not self.service.is_initialized:
            self._set_empty_state(
                "Catalogue Satisfactory introuvable.\n"
                "Importez vos exports JSON avec tools/import_satisfactory_catalog.py."
            )
            return
        self._start_loading(self._locale)

    def _start_loading(self, locale: str) -> None:
        if self._loading:
            return
        self._loading = True
        self._load_error = None
        self._loading_locale = locale
        self.table_status.setText(f"Chargement des recettes ({locale})…")
        self._set_controls_enabled(False)

        worker = _RecipeLoadThread(self.service, locale, self)
        worker.loaded.connect(self._on_load_success)
        worker.failed.connect(self._on_load_error)
        worker.finished.connect(self._on_load_finished)
        worker.finished.connect(worker.deleteLater)
        worker.start()
        self._load_thread = worker

    def _on_load_success(self, payload: dict[str, Any]) -> None:
        locale = str(payload["locale"])
        locales = list(payload["locales"])
        recipes = list(payload["recipes"])
        summary = payload["summary"]

        self._locales = locales
        self._recipes_cache[locale] = recipes
        self._locale = locale
        self._all_recipes = recipes
        self._recipes_by_id = {
            recipe.class_name: recipe for recipe in self._all_recipes
        }
        self._loaded = True

        self._populate_locale_filter(locales, locale)
        self.recipe_count_label.setText(
            f"{len(self._all_recipes):,} recettes".replace(",", " ")
        )
        self.class_count_label.setText(
            f"{summary['class_count']:,} classes · "
            f"{summary['native_class_count']} catégories".replace(",", " ")
        )
        self.locale_count_label.setText(f"{len(locales)} langues disponibles")
        self._populate_producer_filter()
        self._apply_filters()

    def _on_load_error(self, message: str) -> None:
        self._load_error = message

    def _on_load_finished(self) -> None:
        self._loading = False
        self._load_thread = None
        self._set_controls_enabled(True)
        if self._load_error:
            if self._all_recipes:
                # En cas d'échec lors d'un changement de langue, conserver
                # les données précédentes et remettre le sélecteur en accord.
                self.locale_filter.blockSignals(True)
                previous_index = self.locale_filter.findData(self._locale)
                self.locale_filter.setCurrentIndex(max(previous_index, 0))
                self.locale_filter.blockSignals(False)
                self.table_status.setText(
                    f"Impossible de charger {self._loading_locale} : "
                    f"{self._load_error}. Langue conservée : {self._locale}."
                )
            else:
                self._set_empty_state(
                    f"Impossible de lire le catalogue : {self._load_error}"
                )
        elif self._loaded:
            self.table_status.setText(
                f"{len(self._filtered_recipes):,} résultat(s) sur "
                f"{len(self._all_recipes):,}.".replace(",", " ")
            )

    def _set_controls_enabled(self, enabled: bool) -> None:
        for control in (
            self.search_input,
            self.type_filter,
            self.producer_filter,
            self.locale_filter,
        ):
            control.setEnabled(enabled)

    def _populate_locale_filter(self, locales: list[str], selected: str) -> None:
        self.locale_filter.blockSignals(True)
        self.locale_filter.clear()
        for locale in locales:
            self.locale_filter.addItem(locale, locale)
        index = self.locale_filter.findData(selected)
        self.locale_filter.setCurrentIndex(max(index, 0))
        self.locale_filter.blockSignals(False)

    def _populate_producer_filter(self) -> None:
        selected = self.producer_filter.currentData() or ""
        producers = sorted(
            {
                producer.display_name
                for recipe in self._all_recipes
                for producer in recipe.producers
            },
            key=str.casefold,
        )
        self.producer_filter.blockSignals(True)
        self.producer_filter.clear()
        self.producer_filter.addItem("Tous les fabricants", "")
        for producer in producers:
            self.producer_filter.addItem(producer, producer)
        index = self.producer_filter.findData(selected)
        self.producer_filter.setCurrentIndex(max(index, 0))
        self.producer_filter.blockSignals(False)

    def _change_locale(self, _index: int) -> None:
        locale = self.locale_filter.currentData()
        if not locale or locale == self._locale or self._loading:
            return
        cached = self._recipes_cache.get(locale)
        if cached is not None:
            self._apply_loaded_locale(locale, cached)
            return
        self._start_loading(locale)

    def _apply_loaded_locale(self, locale: str, recipes: list[Recipe]) -> None:
        self._locale = locale
        self._all_recipes = recipes
        self._recipes_by_id = {
            recipe.class_name: recipe for recipe in recipes
        }
        self._populate_producer_filter()
        self._apply_filters()

    def _apply_filters(self, *_args: Any) -> None:
        if not hasattr(self, "recipe_model"):
            return

        search = self.search_input.text().strip().casefold()
        recipe_type = self.type_filter.currentData() or "all"
        producer = self.producer_filter.currentData() or ""

        filtered: list[Recipe] = []
        for recipe in self._all_recipes:
            if recipe_type != "all" and recipe.recipe_type != recipe_type:
                continue
            if producer and producer not in recipe.producer_names:
                continue
            if search and not self._matches_search(recipe, search):
                continue
            filtered.append(recipe)

        self._filtered_recipes = filtered
        self.recipe_model.set_recipes(filtered)
        if filtered:
            self.recipe_table.selectRow(0)
            self._show_selected_recipe(filtered[0])
        else:
            self._clear_detail()

        self.table_status.setText(
            f"{len(filtered):,} résultat(s) sur {len(self._all_recipes):,}.".replace(",", " ")
        )

    @staticmethod
    def _matches_search(recipe: Recipe, search: str) -> bool:
        values = [recipe.display_name, recipe.class_name, recipe.description]
        for component in (*recipe.ingredients, *recipe.products):
            values.extend((component.display_name, component.description))
        for producer in recipe.producers:
            values.extend((producer.display_name, producer.description))
        return any(search in value.casefold() for value in values if value)

    def _on_current_row_changed(
        self,
        current: QModelIndex,
        _previous: QModelIndex,
    ) -> None:
        if current.isValid() and 0 <= current.row() < len(self._filtered_recipes):
            self._show_selected_recipe(self._filtered_recipes[current.row()])

    def _show_selected_recipe(self, recipe: Recipe) -> None:
        self.detail_title.setText(recipe.display_name)
        self.detail_class.setText(f"Identifiant interne : {recipe.class_name}")
        has_game_description = bool(recipe.description.strip())
        self.detail_description_heading.setText(
            "DESCRIPTION DU JEU" if has_game_description else "RÉSUMÉ TECHNIQUE CALCULÉ"
        )
        self.detail_description.setText(
            recipe.description.strip() or self._build_technical_summary(recipe)
        )
        self.detail_duration.setText(
            f"Durée d'un cycle : {self._format_decimal(recipe.duration_seconds)} s"
        )
        self.ingredients_label.setText(
            self._format_components(
                recipe.ingredients,
                empty_text="Aucun ingrédient consommé (selon l'export du jeu).",
                duration_seconds=recipe.duration_seconds,
                show_rate=recipe.recipe_type == "production",
            )
        )
        self.products_label.setText(
            self._format_components(
                recipe.products,
                empty_text="Aucun produit déclaré dans l'export.",
                duration_seconds=recipe.duration_seconds,
                show_rate=recipe.recipe_type == "production",
            )
        )
        self.producers_label.setText(
            self._format_producers(recipe.producers)
            if recipe.producers
            else "Aucun fabricant ou poste n'est renseigné dans l'export."
        )

    def _clear_detail(self) -> None:
        self.detail_title.setText("Aucune recette correspondante")
        self.detail_class.setText("Modifiez votre recherche ou vos filtres.")
        self.detail_description_heading.setText("RÉSUMÉ TECHNIQUE")
        self.detail_description.setText("Aucun résumé disponible.")
        self.detail_duration.setText("Durée d'un cycle : —")
        self.ingredients_label.setText("—")
        self.products_label.setText("—")
        self.producers_label.setText("—")

    def _set_empty_state(self, message: str) -> None:
        self._all_recipes = []
        self._filtered_recipes = []
        self._recipes_by_id = {}
        self.recipe_model.set_recipes([])
        self.table_status.setText(message)
        self.recipe_count_label.setText("0 recette")
        self.class_count_label.setText("Catalogue indisponible")
        self.locale_count_label.setText("0 langue")
        self.detail_title.setText("Catalogue indisponible")
        self.detail_class.setText(message)
        self.detail_description_heading.setText("RÉSUMÉ TECHNIQUE")
        self.detail_description.setText("Aucun résumé disponible.")
        self.detail_duration.setText("Durée d'un cycle : —")
        self.ingredients_label.setText("—")
        self.products_label.setText("—")
        self.producers_label.setText("—")

    @classmethod
    def _format_components(
        cls,
        components: tuple[RecipeComponent, ...],
        *,
        empty_text: str,
        duration_seconds: Decimal,
        show_rate: bool,
    ) -> str:
        if not components:
            return empty_text

        lines: list[str] = []
        for component in components:
            unit = component.unit_label
            amount = cls._format_decimal(component.amount)
            if component.is_fluid:
                quantity = f"{amount} m³ / cycle"
            else:
                noun = unit if component.amount == Decimal("1") else f"{unit}s"
                quantity = f"{amount} {noun} / cycle"
            if show_rate and duration_seconds > 0:
                per_minute = component.amount * Decimal("60") / duration_seconds
                rate_unit = "m³/min" if component.is_fluid else "unités/min"
                quantity += (
                    f" · {cls._format_decimal(per_minute)} {rate_unit} à 100 %"
                )

            lines.append(f"{component.display_name} — {quantity}")
            description = cls._clean_description(component.description)
            if description:
                lines.append(f"  {description}")

        return "\n".join(lines)

    @classmethod
    def _format_components_inline(cls, components: tuple[RecipeComponent, ...]) -> str:
        if not components:
            return "—"
        values: list[str] = []
        for component in components:
            amount = cls._format_decimal(component.amount)
            if component.is_fluid:
                values.append(f"{component.display_name} · {amount} m³")
            else:
                values.append(f"{component.display_name} × {amount}")
        return " ; ".join(values)

    @classmethod
    def _build_technical_summary(cls, recipe: Recipe) -> str:
        """Produit un résumé factuel car les exports ne décrivent pas les recettes."""

        inputs = cls._format_summary_components(recipe.ingredients)
        outputs = cls._format_summary_components(recipe.products)
        if inputs:
            input_text = f"Consomme {inputs}."
        else:
            input_text = "Aucun ingrédient consommé n'est déclaré dans l'export."
        if outputs:
            output_text = f"Produit {outputs}."
        else:
            output_text = "Aucun produit n'est déclaré dans l'export."
        cycle_text = (
            f"Durée du cycle : {cls._format_decimal(recipe.duration_seconds)} s."
            if recipe.duration_seconds > 0
            else "Durée du cycle non renseignée."
        )
        return (
            "Aucune description narrative n'est fournie pour cette recette dans "
            "l'export du jeu. Résumé technique calculé : "
            f"{input_text} {output_text} {cycle_text}"
        )

    @classmethod
    def _format_summary_components(
        cls,
        components: tuple[RecipeComponent, ...],
    ) -> str:
        values: list[str] = []
        for component in components:
            amount = cls._format_decimal(component.amount)
            if component.is_fluid:
                values.append(f"{amount} m³ de {component.display_name}")
            else:
                values.append(f"{amount} × {component.display_name}")
        return ", ".join(values)

    @classmethod
    def _format_producers(cls, producers: tuple[RecipeProducer, ...]) -> str:
        lines: list[str] = []
        for producer in producers:
            lines.append(producer.display_name)
            description = cls._clean_description(producer.description)
            if description:
                lines.append(f"  {description}")
        return "\n".join(lines)

    @staticmethod
    def _clean_description(value: str) -> str:
        return "\n".join(
            line.strip()
            for line in value.replace("\r\n", "\n").replace("\r", "\n").split("\n")
            if line.strip()
        )

    @staticmethod
    def _format_decimal(value: Decimal) -> str:
        normalized = format(value.normalize(), "f")
        return normalized.replace(".", ",")
