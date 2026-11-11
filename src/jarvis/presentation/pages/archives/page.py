"""Interface du centre d'archives de J.A.R.V.I.S."""

from __future__ import annotations

import json
from datetime import datetime
from html import escape
from pathlib import Path
from uuid import UUID

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from jarvis.application.services.archive_service import ArchiveService
from jarvis.config.paths import PROJECTS_DIR, USER_DATA_DIR
from jarvis.domain.entities.archive_record import ArchiveRecord


class ArchivesPage(QWidget):
    """Consulte, restaure et supprime définitivement les archives."""

    CATEGORY_LABELS = {
        "project": "Projet",
        "park": "Parc industriel",
        "factory": "Usine",
        "machine": "Machine",
        "extractor": "Extracteur",
        "generator": "Générateur",
        "power_grid": "Réseau électrique",
        "transfer": "Transfert",
    }

    CATEGORY_ICONS = {
        "project": "▤",
        "park": "▦",
        "factory": "⚙",
        "machine": "⚙",
        "extractor": "⌁",
        "generator": "ϟ",
        "power_grid": "ϟ",
        "transfer": "⇄",
    }

    MAX_TREE_ITEMS = 4000
    MAX_JSON_BYTES = 2 * 1024 * 1024

    def __init__(
        self,
        service: ArchiveService | None = None,
        parent=None,
    ):
        super().__init__(parent)

        self.setObjectName("ArchivesPage")
        self.service = service or ArchiveService()
        self._all_records: list[ArchiveRecord] = []
        self._visible_records: list[ArchiveRecord] = []
        self._selected_record: ArchiveRecord | None = None

        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 28, 30, 25)
        root.setSpacing(17)

        # En-tête et choix du niveau de détail.
        header = QHBoxLayout()
        title_area = QVBoxLayout()
        title_area.setSpacing(5)

        title = QLabel("Centre d'archives")
        title.setObjectName("PageTitle")

        subtitle = QLabel(
            "Retrouvez vos projets et installations archivés, "
            "puis restaurez-les si nécessaire."
        )
        subtitle.setObjectName("PageSubtitle")
        subtitle.setWordWrap(True)

        title_area.addWidget(title)
        title_area.addWidget(subtitle)
        header.addLayout(title_area)
        header.addStretch()

        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)

        self.simple_mode_button = QPushButton("Vue simplifiée")
        self.simple_mode_button.setObjectName("ArchiveModeButton")
        self.simple_mode_button.setCheckable(True)
        self.simple_mode_button.setChecked(True)
        self.simple_mode_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.simple_mode_button.clicked.connect(self.show_simple_view)
        self.mode_group.addButton(self.simple_mode_button)
        header.addWidget(self.simple_mode_button)

        self.advanced_mode_button = QPushButton("Vue avancée")
        self.advanced_mode_button.setObjectName("ArchiveModeButton")
        self.advanced_mode_button.setCheckable(True)
        self.advanced_mode_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.advanced_mode_button.clicked.connect(self.show_advanced_view)
        self.mode_group.addButton(self.advanced_mode_button)
        header.addWidget(self.advanced_mode_button)

        self.refresh_button = QPushButton("Actualiser")
        self.refresh_button.setObjectName("SecondarySmallButton")
        self.refresh_button.setMinimumHeight(38)
        self.refresh_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_button.clicked.connect(self.refresh)
        header.addWidget(self.refresh_button)
        root.addLayout(header)

        # Indicateurs synthétiques.
        metrics = QHBoxLayout()
        metrics.setSpacing(12)

        self.total_value = self._create_metric_card(
            metrics,
            "TOTAL DES ARCHIVES",
        )
        self.projects_value = self._create_metric_card(
            metrics,
            "PROJETS",
        )
        self.parks_value = self._create_metric_card(
            metrics,
            "PARCS INDUSTRIELS",
        )
        root.addLayout(metrics)

        # Recherche et filtres, disponibles dans les deux vues.
        filters = QHBoxLayout()
        filters.setSpacing(10)

        filter_label = QLabel("CATÉGORIE")
        filter_label.setObjectName("SectionLabel")
        filters.addWidget(filter_label)

        self.category_filter = QComboBox()
        self.category_filter.setObjectName("ArchiveFilter")
        self.category_filter.setMinimumWidth(190)
        self.category_filter.addItem("Toutes les catégories", None)
        for entity_type, label in self.CATEGORY_LABELS.items():
            self.category_filter.addItem(label, entity_type)
        self.category_filter.currentIndexChanged.connect(self._apply_filters)
        filters.addWidget(self.category_filter)

        self.search_input = QLineEdit()
        self.search_input.setObjectName("ArchiveSearch")
        self.search_input.setPlaceholderText(
            "Rechercher une archive par son nom ou son emplacement…"
        )
        self.search_input.textChanged.connect(self._apply_filters)
        filters.addWidget(self.search_input, 1)
        root.addLayout(filters)

        # Les deux présentations sont conservées dans la même page.
        self.view_stack = QStackedWidget()
        self.view_stack.setObjectName("ArchiveViewStack")
        self.view_stack.addWidget(self._build_simple_view())
        self.view_stack.addWidget(self._build_advanced_view())
        root.addWidget(self.view_stack, 1)

        # Actions détaillées réservées à la vue avancée.
        actions = QHBoxLayout()
        actions.addStretch()

        self.restore_button = QPushButton("Restaurer")
        self.restore_button.setObjectName("PrimarySmallButton")
        self.restore_button.setMinimumWidth(125)
        self.restore_button.setMinimumHeight(38)
        self.restore_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.restore_button.setEnabled(False)
        self.restore_button.clicked.connect(self.restore_selected)

        self.delete_button = QPushButton("Supprimer définitivement")
        self.delete_button.setObjectName("DangerSmallButton")
        self.delete_button.setMinimumHeight(38)
        self.delete_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_button.setEnabled(False)
        self.delete_button.clicked.connect(self.delete_selected)

        actions.addWidget(self.restore_button)
        actions.addWidget(self.delete_button)
        self.advanced_actions = QWidget()
        self.advanced_actions.setLayout(actions)
        root.addWidget(self.advanced_actions)
        self.advanced_actions.hide()

    def _build_simple_view(self) -> QWidget:
        """Construit la présentation en cartes, destinée à l'usage courant."""

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        heading = QHBoxLayout()
        self.simple_count_label = QLabel("ARCHIVES DISPONIBLES")
        self.simple_count_label.setObjectName("SectionLabel")
        heading.addWidget(self.simple_count_label)
        heading.addStretch()
        layout.addLayout(heading)

        self.simple_scroll_area = QScrollArea()
        self.simple_scroll_area.setObjectName("ArchiveSimpleScrollArea")
        self.simple_scroll_area.setWidgetResizable(True)
        self.simple_scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        self.simple_container = QWidget()
        self.simple_container.setObjectName("ArchiveSimpleContainer")
        self.simple_layout = QVBoxLayout(self.simple_container)
        self.simple_layout.setContentsMargins(0, 5, 8, 10)
        self.simple_layout.setSpacing(12)

        self.simple_scroll_area.setWidget(self.simple_container)
        layout.addWidget(self.simple_scroll_area, 1)
        return page

    def _build_advanced_view(self) -> QWidget:
        """Construit la table et l'inspecteur technique des fichiers archivés."""

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("ArchiveSplitter")
        splitter.setChildrenCollapsible(False)

        list_panel = QFrame()
        list_panel.setObjectName("ArchivePanel")
        list_layout = QVBoxLayout(list_panel)
        list_layout.setContentsMargins(14, 13, 14, 14)
        list_layout.setSpacing(10)

        list_heading = QHBoxLayout()
        list_title = QLabel("ÉLÉMENTS ARCHIVÉS")
        list_title.setObjectName("SectionLabel")
        list_heading.addWidget(list_title)
        list_heading.addStretch()

        self.results_label = QLabel("0 élément")
        self.results_label.setObjectName("ArchiveMutedLabel")
        list_heading.addWidget(self.results_label)
        list_layout.addLayout(list_heading)

        self.archive_table = QTableWidget(0, 3)
        self.archive_table.setObjectName("ArchiveTable")
        self.archive_table.setHorizontalHeaderLabels(
            ["Nom", "Catégorie", "Date d'archivage"]
        )
        self.archive_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.archive_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.archive_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.archive_table.setShowGrid(False)
        self.archive_table.verticalHeader().setVisible(False)
        self.archive_table.verticalHeader().setDefaultSectionSize(39)
        self.archive_table.horizontalHeader().setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.Stretch,
        )
        self.archive_table.horizontalHeader().setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        self.archive_table.horizontalHeader().setSectionResizeMode(
            2,
            QHeaderView.ResizeMode.ResizeToContents,
        )
        self.archive_table.itemSelectionChanged.connect(self._on_archive_selected)
        list_layout.addWidget(self.archive_table, 1)

        self.advanced_empty_label = QLabel(
            "Aucune archive ne correspond à votre recherche."
        )
        self.advanced_empty_label.setObjectName("ArchiveEmptyLabel")
        self.advanced_empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.advanced_empty_label.setWordWrap(True)
        self.advanced_empty_label.hide()
        list_layout.addWidget(self.advanced_empty_label)

        inspector = QFrame()
        inspector.setObjectName("ArchivePanel")
        inspector_layout = QVBoxLayout(inspector)
        inspector_layout.setContentsMargins(15, 13, 15, 14)
        inspector_layout.setSpacing(10)

        inspector_title = QLabel("INSPECTION DE L'ARCHIVE")
        inspector_title.setObjectName("SectionLabel")
        inspector_layout.addWidget(inspector_title)

        self.archive_info = QLabel(
            "Sélectionnez une archive pour afficher ses informations."
        )
        self.archive_info.setObjectName("ArchiveInfo")
        self.archive_info.setWordWrap(True)
        self.archive_info.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        inspector_layout.addWidget(self.archive_info)

        self.preview_tabs = QTabWidget()
        self.preview_tabs.setObjectName("ArchivePreviewTabs")

        self.summary_label = QLabel(
            "Sélectionnez un projet ou un parc pour consulter son contenu."
        )
        self.summary_label.setObjectName("ArchiveSummary")
        self.summary_label.setWordWrap(True)
        self.summary_label.setTextFormat(Qt.TextFormat.RichText)
        self.summary_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        self.summary_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self.summary_scroll = QScrollArea()
        self.summary_scroll.setObjectName("ArchiveSummaryScroll")
        self.summary_scroll.setWidgetResizable(True)
        self.summary_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.summary_scroll.setWidget(self.summary_label)
        self.preview_tabs.addTab(self.summary_scroll, "Contenu")

        self.archive_tree = QTreeWidget()
        self.archive_tree.setObjectName("ArchiveTree")
        self.archive_tree.setHeaderHidden(True)
        self.archive_tree.itemClicked.connect(self._on_tree_item_clicked)
        self.preview_tabs.addTab(self.archive_tree, "Arborescence")

        self.json_preview = QPlainTextEdit()
        self.json_preview.setObjectName("ArchiveJsonPreview")
        self.json_preview.setReadOnly(True)
        self.json_preview.setPlaceholderText(
            "Sélectionnez un fichier JSON dans l'arborescence pour le consulter."
        )
        self.preview_tabs.addTab(self.json_preview, "Aperçu JSON")
        inspector_layout.addWidget(self.preview_tabs, 1)

        splitter.addWidget(list_panel)
        splitter.addWidget(inspector)
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 6)
        splitter.setSizes([520, 620])
        layout.addWidget(splitter, 1)
        return page

    @staticmethod
    def _create_metric_card(layout: QHBoxLayout, label: str) -> QLabel:
        card = QFrame()
        card.setObjectName("ArchiveMetricCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(15, 11, 15, 11)
        card_layout.setSpacing(3)

        label_widget = QLabel(label)
        label_widget.setObjectName("ArchiveMetricLabel")

        value = QLabel("0")
        value.setObjectName("ArchiveMetricValue")

        card_layout.addWidget(label_widget)
        card_layout.addWidget(value)
        layout.addWidget(card, 1)
        return value

    def show_simple_view(self) -> None:
        """Affiche les archives sous forme de cartes lisibles."""

        self.simple_mode_button.setChecked(True)
        self.view_stack.setCurrentIndex(0)
        self.advanced_actions.hide()

    def show_advanced_view(self) -> None:
        """Affiche le tableau et l'inspecteur de fichiers."""

        self.advanced_mode_button.setChecked(True)
        self.view_stack.setCurrentIndex(1)
        self.advanced_actions.show()

    def refresh(self) -> None:
        """Recharge toutes les métadonnées depuis le dépôt central."""

        try:
            self._all_records = self.service.get_archives()
        except Exception as error:
            QMessageBox.critical(
                self,
                "Chargement des archives impossible",
                f"Le centre d'archives n'a pas pu être chargé :\n{error}",
            )
            self._all_records = []

        self.total_value.setText(str(len(self._all_records)))
        self.projects_value.setText(
            str(sum(record.entity_type == "project" for record in self._all_records))
        )
        self.parks_value.setText(
            str(sum(record.entity_type == "park" for record in self._all_records))
        )

        self._apply_filters()

    def _apply_filters(self, *_args) -> None:
        """Applique la catégorie et la recherche textuelle."""

        category = self.category_filter.currentData()
        query = self.search_input.text().strip().casefold()

        records = []
        for record in self._all_records:
            if category and record.entity_type != category:
                continue

            searchable = " ".join(
                (
                    record.entity_name,
                    str(record.entity_id),
                    str(record.archive_id),
                    record.original_location,
                )
            ).casefold()

            if query and query not in searchable:
                continue

            records.append(record)

        self._visible_records = records
        self._populate_cards()
        self._populate_table()

    def _populate_cards(self) -> None:
        """Actualise la vue simplifiée avec une carte par archive."""

        while self.simple_layout.count():
            item = self.simple_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        count = len(self._visible_records)
        self.simple_count_label.setText(
            f"ARCHIVES DISPONIBLES  ·  {count}"
        )

        if not count:
            empty_card = QFrame()
            empty_card.setObjectName("EmptyProjectsCard")
            empty_layout = QVBoxLayout(empty_card)
            empty_layout.setContentsMargins(30, 35, 30, 35)
            empty_layout.setSpacing(10)

            icon = QLabel("▤")
            icon.setObjectName("EmptyProjectIcon")
            title = QLabel("Aucune archive trouvée")
            title.setObjectName("SectionTitle")
            description = QLabel(
                "Les projets et installations que tu choisiras d'archiver "
                "apparaîtront ici."
            )
            description.setObjectName("PageSubtitle")
            description.setWordWrap(True)

            empty_layout.addWidget(icon)
            empty_layout.addWidget(title)
            empty_layout.addWidget(description)
            self.simple_layout.addWidget(empty_card)
            self.simple_layout.addStretch()
            return

        for record in self._visible_records:
            self.simple_layout.addWidget(self._create_archive_card(record))

        self.simple_layout.addStretch()

    def _create_archive_card(self, record: ArchiveRecord) -> QFrame:
        """Construit une carte d'archive proche des cartes de projets actifs."""

        card = QFrame()
        card.setObjectName("ArchiveCard")

        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(20, 17, 20, 17)
        card_layout.setSpacing(18)

        icon = QLabel(self.CATEGORY_ICONS.get(record.entity_type, "▤"))
        icon.setObjectName("ArchiveCardIcon")
        icon.setFixedWidth(36)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(icon)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(5)

        name = QLabel(record.entity_name)
        name.setObjectName("ProjectTitle")

        category = self.CATEGORY_LABELS.get(
            record.entity_type,
            record.entity_type,
        )
        description = QLabel(f"{category} archivé")
        description.setObjectName("ProjectDescription")

        archived_at = record.archived_at.astimezone().strftime(
            "%d/%m/%Y à %H:%M"
        )
        metadata = QLabel(
            f"Archivé le {archived_at}    •    "
            "Données conservées dans le centre d'archives"
        )
        metadata.setObjectName("ProjectMetadata")
        metadata.setWordWrap(True)

        info_layout.addWidget(name)
        info_layout.addWidget(description)
        info_layout.addWidget(metadata)
        card_layout.addLayout(info_layout, 1)

        actions = QVBoxLayout()
        actions.setSpacing(7)

        inspect_button = QPushButton("Consulter")
        inspect_button.setObjectName("SecondarySmallButton")
        inspect_button.setCursor(Qt.CursorShape.PointingHandCursor)
        inspect_button.clicked.connect(
            lambda checked=False, archive=record: self._open_advanced_for_archive(
                archive
            )
        )

        restore_button = QPushButton("Restaurer")
        restore_button.setObjectName("PrimarySmallButton")
        restore_button.setCursor(Qt.CursorShape.PointingHandCursor)
        restore_button.clicked.connect(
            lambda checked=False, archive=record: self._restore_record(archive)
        )

        delete_button = QPushButton("Supprimer définitivement")
        delete_button.setObjectName("DangerSmallButton")
        delete_button.setCursor(Qt.CursorShape.PointingHandCursor)
        delete_button.setToolTip("Supprimer définitivement cette archive")
        delete_button.clicked.connect(
            lambda checked=False, archive=record: self._delete_record(archive)
        )

        actions.addWidget(inspect_button)
        actions.addWidget(restore_button)
        actions.addWidget(delete_button)
        card_layout.addLayout(actions)
        return card

    def _open_advanced_for_archive(self, record: ArchiveRecord) -> None:
        """Ouvre l'inspecteur avancé sur l'archive choisie."""

        self.show_advanced_view()
        for row in range(self.archive_table.rowCount()):
            item = self.archive_table.item(row, 0)
            if item is None:
                continue
            archive_id = item.data(Qt.ItemDataRole.UserRole)
            if str(archive_id) == str(record.archive_id):
                self.archive_table.selectRow(row)
                self.archive_table.scrollToItem(item)
                return

    def _restore_record(self, record: ArchiveRecord) -> None:
        self._selected_record = record
        self.restore_selected()

    def _delete_record(self, record: ArchiveRecord) -> None:
        self._selected_record = record
        self.delete_selected()

    def _populate_table(self) -> None:
        """Recharge le tableau et active automatiquement une archive visible."""

        previous_archive_id = (
            self._selected_record.archive_id
            if self._selected_record is not None
            else None
        )

        signals_were_blocked = self.archive_table.blockSignals(True)
        self.archive_table.clearSelection()
        self.archive_table.setCurrentCell(-1, -1)
        self.archive_table.setRowCount(len(self._visible_records))

        for row, record in enumerate(self._visible_records):
            name_item = QTableWidgetItem(record.entity_name)
            name_item.setData(
                Qt.ItemDataRole.UserRole,
                str(record.archive_id),
            )
            name_item.setToolTip(record.original_location)

            category_item = QTableWidgetItem(
                self.CATEGORY_LABELS.get(
                    record.entity_type,
                    record.entity_type,
                )
            )

            archived_at = record.archived_at.astimezone().strftime(
                "%d/%m/%Y %H:%M"
            )
            date_item = QTableWidgetItem(archived_at)
            date_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight
                | Qt.AlignmentFlag.AlignVCenter
            )

            self.archive_table.setItem(row, 0, name_item)
            self.archive_table.setItem(row, 1, category_item)
            self.archive_table.setItem(row, 2, date_item)

        count = len(self._visible_records)
        self.results_label.setText(
            f"{count} élément" if count <= 1 else f"{count} éléments"
        )
        self.advanced_empty_label.setVisible(count == 0)
        self.archive_table.setVisible(count > 0)

        selected_row = -1
        if count:
            # Conserve l'archive sélectionnée si elle est toujours visible.
            if previous_archive_id is not None:
                selected_row = next(
                    (
                        row
                        for row, record in enumerate(self._visible_records)
                        if record.archive_id == previous_archive_id
                    ),
                    -1,
                )

            # Après archivage/suppression/restauration, sélectionner le
            # premier élément restant plutôt que laisser un inspecteur vide.
            if selected_row < 0:
                selected_row = 0

            self.archive_table.setCurrentCell(selected_row, 0)
            self.archive_table.selectRow(selected_row)

        self.archive_table.blockSignals(signals_were_blocked)

        if count:
            # La sélection a été effectuée avec les signaux bloqués afin
            # d'éviter plusieurs chargements successifs de l'inspecteur.
            self._on_archive_selected()
        else:
            self._clear_inspector()

    def _clear_inspector(self) -> None:
        self._selected_record = None
        self.archive_info.setText(
            "Sélectionnez une archive pour afficher ses informations."
        )
        self.summary_label.setText(
            "Sélectionnez un projet ou un parc pour consulter son contenu."
        )
        self.archive_tree.clear()
        self.json_preview.clear()
        self.restore_button.setEnabled(False)
        self.delete_button.setEnabled(False)

    def _on_archive_selected(self) -> None:
        current_row = self.archive_table.currentRow()
        if current_row < 0:
            self._clear_inspector()
            return

        name_item = self.archive_table.item(current_row, 0)
        if name_item is None:
            self._clear_inspector()
            return

        archive_id_value = name_item.data(Qt.ItemDataRole.UserRole)
        try:
            archive_id = UUID(str(archive_id_value))
        except (ValueError, TypeError):
            self._clear_inspector()
            return

        record = next(
            (
                item
                for item in self._visible_records
                if item.archive_id == archive_id
            ),
            None,
        )
        if record is None:
            self._clear_inspector()
            return

        self._selected_record = record
        self.restore_button.setEnabled(True)
        self.delete_button.setEnabled(True)
        self._display_record(record)

    def _display_record(self, record: ArchiveRecord) -> None:
        """Affiche les informations compréhensibles de l'archive sélectionnée."""

        archived_at = record.archived_at.astimezone().strftime(
            "%d/%m/%Y à %H:%M:%S"
        )
        parent_project = "Aucun"
        if record.parent_project_id:
            parent_project = (
                self._resolve_project_name(record.parent_project_id)
                or "Projet parent non disponible"
            )

        safe_name = escape(record.entity_name)
        safe_category = escape(
            self.CATEGORY_LABELS.get(record.entity_type, record.entity_type)
        )
        safe_parent = escape(parent_project)

        info_lines = [
            f"<b>{safe_name}</b>",
            f"Catégorie : {safe_category}",
            f"Archivée le : {escape(archived_at)}",
        ]
        if record.parent_project_id:
            info_lines.append(f"Projet associé : {safe_parent}")
        self.archive_info.setText("<br>".join(info_lines))

        self.archive_tree.clear()
        self.json_preview.clear()
        self.preview_tabs.setCurrentIndex(0)

        try:
            payload = self.service.get_archive_content(record.archive_id)
        except Exception as error:
            message = escape(str(error))
            self.summary_label.setText(
                "<h2>Contenu indisponible</h2>"
                f"<p>{message}</p>"
            )
            self.archive_tree.addTopLevelItem(
                QTreeWidgetItem([f"Contenu indisponible : {error}"])
            )
            return

        self._display_human_readable_content(record, payload)

        if payload.is_file():
            root_item = QTreeWidgetItem([payload.name])
            root_item.setData(
                0,
                Qt.ItemDataRole.UserRole,
                str(payload),
            )
            self.archive_tree.addTopLevelItem(root_item)
            root_item.setSelected(True)
            return

        root_item = QTreeWidgetItem([payload.name or "Contenu archivé"])
        root_item.setData(
            0,
            Qt.ItemDataRole.UserRole,
            str(payload),
        )
        self.archive_tree.addTopLevelItem(root_item)

        counter = [0]
        self._populate_tree(root_item, payload, counter, depth=0)
        root_item.setExpanded(True)

    def _read_json_object(self, path: Path) -> tuple[dict | None, str | None]:
        """Lit un objet JSON local sans suivre de lien symbolique."""

        if path.is_symlink() or not path.is_file():
            return None, None

        try:
            if path.stat().st_size > self.MAX_JSON_BYTES:
                return None, "Le fichier dépasse la limite de lecture de 2 Mio."

            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            return None, str(error)

        if not isinstance(data, dict):
            return None, "Le fichier ne contient pas un objet JSON valide."

        return data, None

    @staticmethod
    def _format_summary_date(value) -> str:
        if not isinstance(value, str) or not value.strip():
            return "Non renseignée"

        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is not None:
                parsed = parsed.astimezone()
            return parsed.strftime("%d/%m/%Y à %H:%M")
        except ValueError:
            return value

    @staticmethod
    def _summary_line(label: str, value: str) -> str:
        return (
            "<p style='margin:5px 0;'>"
            f"<b>{escape(label)} :</b> {escape(value)}"
            "</p>"
        )

    def _resolve_project_name(self, project_id: UUID) -> str | None:
        """Retrouve le nom lisible d'un projet actif ou archivé."""

        active_project_file = PROJECTS_DIR / str(project_id) / "project.json"
        active_data, _ = self._read_json_object(active_project_file)
        if active_data and isinstance(active_data.get("name"), str):
            return active_data["name"]

        for project_record in self._all_records:
            if (
                project_record.entity_type != "project"
                or project_record.entity_id != project_id
            ):
                continue

            try:
                project_payload = self.service.get_archive_content(
                    project_record.archive_id
                )
            except Exception:
                continue

            project_data, _ = self._read_json_object(
                project_payload / "project.json"
                if project_payload.is_dir()
                else project_payload
            )
            if project_data and isinstance(project_data.get("name"), str):
                return project_data["name"]
            return project_record.entity_name

        return None

    def _read_project_parks(self, payload: Path, project_id: UUID) -> list[dict]:
        """Charge les noms et emplacements des parcs contenus dans un projet."""

        parks_directory = payload / "parks"
        index_data, _ = self._read_json_object(parks_directory / "index.json")
        if not index_data:
            return []

        park_ids = index_data.get("park_ids", [])
        if not isinstance(park_ids, list):
            return []

        parks = []
        for raw_park_id in park_ids:
            try:
                park_id = UUID(str(raw_park_id))
            except (ValueError, TypeError, AttributeError):
                continue

            park_data, _ = self._read_json_object(
                parks_directory / str(park_id) / "park.json"
            )
            if not park_data:
                continue

            stored_project_id = park_data.get("project_id")
            if stored_project_id and str(stored_project_id) != str(project_id):
                continue

            parks.append(
                {
                    "name": str(park_data.get("name") or "Parc sans nom"),
                    "location": str(
                        park_data.get("location") or "Emplacement non renseigné"
                    ),
                    "description": str(park_data.get("description") or ""),
                }
            )

        return sorted(parks, key=lambda park: park["name"].casefold())

    def _project_summary_html(
        self,
        record: ArchiveRecord,
        payload: Path,
    ) -> str:
        project_file = payload / "project.json" if payload.is_dir() else payload
        project_data, read_error = self._read_json_object(project_file)
        if not project_data:
            detail = escape(read_error or "Le fichier project.json est introuvable.")
            return (
                f"<h2>{escape(record.entity_name)}</h2>"
                "<p>Les informations détaillées de cette partie ne sont pas lisibles.</p>"
                f"<p>{detail}</p>"
                "<p>Les fichiers d'origine restent consultables dans l'onglet Arborescence.</p>"
            )

        name = str(project_data.get("name") or record.entity_name)
        description = str(
            project_data.get("description") or "Aucune description renseignée."
        )
        game_version = str(
            project_data.get("game_version") or "Version non renseignée"
        )
        created_at = self._format_summary_date(project_data.get("created_at"))
        updated_at = self._format_summary_date(project_data.get("updated_at"))

        html = [
            f"<h2 style='color:#F0A044;margin-bottom:5px'>{escape(name)}</h2>",
            "<h3 style='color:#AEBBC8;margin-top:0'>Partie Satisfactory</h3>",
            self._summary_line("Version du jeu", game_version),
            self._summary_line("Créée le", created_at),
            self._summary_line("Modifiée le", updated_at),
            "<h3 style='color:#F0A044;margin-top:18px'>Description</h3>",
            f"<p>{escape(description)}</p>",
        ]

        parks = self._read_project_parks(payload, record.entity_id)
        html.append(
            f"<h3 style='color:#F0A044;margin-top:18px'>Parcs industriels ({len(parks)})</h3>"
        )
        if parks:
            html.append("<ul style='margin-left:18px;'>")
            for park in parks:
                park_line = escape(park["name"])
                if park["location"] != "Emplacement non renseigné":
                    park_line += f" — {escape(park['location'])}"
                html.append(f"<li style='margin:5px 0'>{park_line}</li>")
                if park["description"]:
                    html.append(
                        "<p style='margin:0 0 8px 14px;color:#91A2B2'>"
                        f"{escape(park['description'])}</p>"
                    )
            html.append("</ul>")
        else:
            html.append("<p>Aucun parc industriel enregistré dans cette partie.</p>")

        scenarios_directory = payload / "scenarios"
        if scenarios_directory.is_dir() and not scenarios_directory.is_symlink():
            try:
                scenario_count = sum(
                    1
                    for item in scenarios_directory.iterdir()
                    if not item.is_symlink()
                )
            except OSError:
                scenario_count = 0
        else:
            scenario_count = 0

        network_data, _ = self._read_json_object(payload / "network.json")
        targets_data, _ = self._read_json_object(payload / "targets.json")
        transfers = network_data.get("resource_transfers", []) if network_data else []
        power_grids = network_data.get("power_grids", []) if network_data else []
        targets = targets_data.get("targets", []) if targets_data else []

        def safe_count(value) -> int:
            return len(value) if isinstance(value, list) else 0

        html.append(
            "<h3 style='color:#F0A044;margin-top:18px'>Autres données conservées</h3>"
        )
        html.append("<ul style='margin-left:18px;'>")
        html.append(f"<li>Scénarios enregistrés : {scenario_count}</li>")
        html.append(f"<li>Réseaux électriques : {safe_count(power_grids)}</li>")
        html.append(f"<li>Transferts de ressources : {safe_count(transfers)}</li>")
        html.append(f"<li>Objectifs : {safe_count(targets)}</li>")
        html.append("</ul>")
        html.append(
            "<p style='color:#8293A3;margin-top:18px'>"
            "Cette fiche présente les données actuellement reconnues par J.A.R.V.I.S. "
            "Les fichiers complets restent disponibles dans l'onglet Arborescence.</p>"
        )
        return "".join(html)

    def _park_summary_html(
        self,
        record: ArchiveRecord,
        payload: Path,
    ) -> str:
        park_file = payload / "park.json" if payload.is_dir() else payload
        park_data, read_error = self._read_json_object(park_file)
        if not park_data:
            detail = escape(read_error or "Le fichier park.json est introuvable.")
            return (
                f"<h2>{escape(record.entity_name)}</h2>"
                "<p>Les informations détaillées de ce parc ne sont pas lisibles.</p>"
                f"<p>{detail}</p>"
                "<p>Les fichiers d'origine restent consultables dans l'onglet Arborescence.</p>"
            )

        name = str(park_data.get("name") or record.entity_name)
        description = str(
            park_data.get("description") or "Aucune description renseignée."
        )
        location = str(
            park_data.get("location") or "Emplacement non renseigné"
        )
        created_at = self._format_summary_date(park_data.get("created_at"))
        updated_at = self._format_summary_date(park_data.get("updated_at"))
        parent_name = (
            self._resolve_project_name(record.parent_project_id)
            if record.parent_project_id
            else None
        ) or "Projet parent non disponible"

        html = [
            f"<h2 style='color:#F0A044;margin-bottom:5px'>{escape(name)}</h2>",
            "<h3 style='color:#AEBBC8;margin-top:0'>Parc industriel</h3>",
            self._summary_line("Projet associé", parent_name),
            self._summary_line("Emplacement", location),
            self._summary_line("Créé le", created_at),
            self._summary_line("Modifié le", updated_at),
            "<h3 style='color:#F0A044;margin-top:18px'>Description</h3>",
            f"<p>{escape(description)}</p>",
        ]

        if payload.is_dir():
            try:
                extra_items = [
                    item.name
                    for item in payload.iterdir()
                    if item.name != "park.json" and not item.is_symlink()
                ]
            except OSError:
                extra_items = []
            if extra_items:
                html.append(
                    "<h3 style='color:#F0A044;margin-top:18px'>Autres éléments conservés</h3>"
                )
                html.append("<ul style='margin-left:18px;'>")
                html.extend(
                    f"<li>{escape(item_name)}</li>"
                    for item_name in sorted(extra_items, key=str.casefold)
                )
                html.append("</ul>")

        html.append(
            "<p style='color:#8293A3;margin-top:18px'>"
            "Les fichiers complets du parc restent disponibles dans l'onglet Arborescence.</p>"
        )
        return "".join(html)

    def _display_human_readable_content(
        self,
        record: ArchiveRecord,
        payload: Path,
    ) -> None:
        """Construit la fiche lisible d'un projet, d'un parc ou d'un autre élément."""

        if record.entity_type == "project":
            summary = self._project_summary_html(record, payload)
        elif record.entity_type == "park":
            summary = self._park_summary_html(record, payload)
        else:
            category = self.CATEGORY_LABELS.get(
                record.entity_type,
                record.entity_type,
            )
            summary = (
                f"<h2 style='color:#F0A044'>{escape(record.entity_name)}</h2>"
                f"<h3 style='color:#AEBBC8'>{escape(category)}</h3>"
                "<p>La fiche de consultation simplifiée n'est pas encore disponible "
                "pour cette catégorie.</p>"
                "<p>Tu peux consulter les fichiers conservés dans l'onglet Arborescence.</p>"
            )

        self.summary_label.setText(summary)

    def _populate_tree(
        self,
        parent_item: QTreeWidgetItem,
        directory: Path,
        counter: list[int],
        depth: int,
    ) -> None:
        if depth >= 30:
            parent_item.addChild(
                QTreeWidgetItem(["Profondeur d'affichage limitée"])
            )
            return

        try:
            entries = sorted(
                directory.iterdir(),
                key=lambda path: (not path.is_dir(), path.name.casefold()),
            )
        except OSError as error:
            parent_item.addChild(
                QTreeWidgetItem([f"Lecture impossible : {error}"])
            )
            return

        for entry in entries:
            if counter[0] >= self.MAX_TREE_ITEMS:
                parent_item.addChild(
                    QTreeWidgetItem(
                        [f"Affichage limité à {self.MAX_TREE_ITEMS} éléments"]
                    )
                )
                return

            counter[0] += 1
            if entry.is_symlink():
                child = QTreeWidgetItem(
                    [f"{entry.name}  ·  lien symbolique non suivi"]
                )
                parent_item.addChild(child)
                continue

            child = QTreeWidgetItem([entry.name])
            child.setData(
                0,
                Qt.ItemDataRole.UserRole,
                str(entry),
            )
            parent_item.addChild(child)

            if entry.is_dir():
                self._populate_tree(
                    child,
                    entry,
                    counter,
                    depth + 1,
                )

    def _on_tree_item_clicked(self, item: QTreeWidgetItem, _column: int) -> None:
        path_value = item.data(0, Qt.ItemDataRole.UserRole)
        if not path_value:
            return

        self._preview_path(Path(str(path_value)))

    def _preview_path(self, path: Path) -> None:
        if path.is_symlink():
            self.json_preview.setPlainText(
                "Les liens symboliques ne sont pas suivis par l'aperçu."
            )
            self.preview_tabs.setCurrentIndex(2)
            return

        if not path.is_file():
            self.json_preview.setPlainText(
                "Sélectionnez un fichier .json dans l'arborescence "
                "pour afficher son contenu."
            )
            self.preview_tabs.setCurrentIndex(1)
            return

        if path.suffix.casefold() != ".json":
            self.json_preview.setPlainText(
                "L'aperçu intégré est réservé aux fichiers JSON."
            )
            self.preview_tabs.setCurrentIndex(2)
            return

        try:
            size = path.stat().st_size
            if size > self.MAX_JSON_BYTES:
                self.json_preview.setPlainText(
                    "Ce fichier dépasse la limite d'aperçu de 2 Mio. "
                    "Il reste présent dans l'archive et n'est pas modifié."
                )
                self.preview_tabs.setCurrentIndex(2)
                return

            raw_content = path.read_text(encoding="utf-8")
            parsed_content = json.loads(raw_content)
            pretty_content = json.dumps(
                parsed_content,
                ensure_ascii=False,
                indent=4,
            )
            self.json_preview.setPlainText(pretty_content)

        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            self.json_preview.setPlainText(
                f"Impossible de lire ce JSON :\n{error}"
            )

        self.preview_tabs.setCurrentIndex(2)

    def _restore_destination(self, record: ArchiveRecord) -> Path:
        """Résout l'emplacement relatif en refusant toute sortie du dossier utilisateur."""

        relative_path = Path(record.original_location)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise ValueError(
                "L'emplacement d'origine de cette archive n'est pas sûr."
            )

        user_root = USER_DATA_DIR.resolve()
        destination = (user_root / relative_path).resolve()

        try:
            destination.relative_to(user_root)
        except ValueError as error:
            raise ValueError(
                "La destination de restauration sort du dossier J.A.R.V.I.S."
            ) from error

        if record.entity_type != "project" and record.parent_project_id:
            parent_project_directory = PROJECTS_DIR / str(record.parent_project_id)
            if not (parent_project_directory / "project.json").is_file():
                raise FileNotFoundError(
                    "Le projet parent de cet élément n'est pas présent. "
                    "Restaurez d'abord le projet correspondant."
                )

        return destination

    def restore_selected(self) -> None:
        record = self._selected_record
        if record is None:
            return

        try:
            destination = self._restore_destination(record)
        except (ValueError, FileNotFoundError) as error:
            QMessageBox.warning(
                self,
                "Restauration impossible",
                str(error),
            )
            return

        answer = QMessageBox.question(
            self,
            "Confirmer la restauration",
            f"Restaurer « {record.entity_name} » ?\n\n"
            f"Destination :\n{destination}\n\n"
            "L'archive sera retirée du centre après restauration.",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            if record.entity_type == "park":
                self.service.restore_park_archive(
                    record.archive_id,
                    destination,
                )
            else:
                self.service.restore_archive(
                    record.archive_id,
                    destination,
                )
        except FileExistsError:
            QMessageBox.warning(
                self,
                "Destination déjà utilisée",
                "Un élément existe déjà à cet emplacement. "
                "Aucun fichier n'a été remplacé.",
            )
            return
        except Exception as error:
            QMessageBox.critical(
                self,
                "Restauration échouée",
                f"L'archive n'a pas pu être restaurée :\n{error}",
            )
            return

        self.refresh()
        QMessageBox.information(
            self,
            "Restauration terminée",
            f"« {record.entity_name} » a été restauré.",
        )

    def delete_selected(self) -> None:
        record = self._selected_record
        if record is None:
            return

        answer = QMessageBox.warning(
            self,
            "Suppression définitive",
            f"Voulez-vous supprimer définitivement « {record.entity_name} » ?\n\n"
            "Cette opération détruira les données archivées et ne pourra pas être annulée.",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            self.service.permanently_delete_archive(record.archive_id)
        except Exception as error:
            QMessageBox.critical(
                self,
                "Suppression échouée",
                f"L'archive n'a pas pu être supprimée :\n{error}",
            )
            return

        self.refresh()
