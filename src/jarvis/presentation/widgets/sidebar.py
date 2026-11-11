
from PySide6.QtCore import QByteArray, QSize, Qt, Signal
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QButtonGroup,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from jarvis.config.paths import NAVIGATION_ICONS_DIR


class Sidebar(QWidget):
    """Navigation principale de J.A.R.V.I.S."""

    page_requested = Signal(str)

    ICON_INACTIVE = "#AEBBC8"
    ICON_ACTIVE = "#F5B568"

    NAV_ITEMS = [
        ("dashboard", "layout-dashboard", "Tableau de bord"),
        ("parks", "building-factory-2", "Parcs industriels"),
        ("network", "hierarchy-2", "Réseau industriel"),
        ("extraction", "shovel", "Extraction"),
        ("energy", "bolt", "Énergie"),
        ("recipes", "book-2", "Recettes"),
        ("simulations", "flask-2", "Simulations"),
        ("projects", "folder", "Mes projets"),
        ("archives", "folder", "Centre d'archives"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setObjectName("Sidebar")
        self.setFixedWidth(245)

        self.buttons = {}
        self.icon_states = {}

        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)

        self._build_ui()

    @staticmethod
    def _create_svg_icon(icon_name: str, color: str) -> QIcon:
        """Charge un SVG et lui applique une couleur."""

        icon_path = NAVIGATION_ICONS_DIR / f"{icon_name}.svg"

        if not icon_path.is_file():
            raise FileNotFoundError(
                f"Icône introuvable : {icon_path}"
            )

        svg_content = icon_path.read_text(encoding="utf-8")
        svg_content = svg_content.replace(
            "currentColor",
            color,
        )

        renderer = QSvgRenderer(
            QByteArray(svg_content.encode("utf-8"))
        )

        if not renderer.isValid():
            raise ValueError(
                f"Fichier SVG invalide : {icon_path}"
            )

        pixmap = QPixmap(48, 48)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing
        )

        renderer.render(painter)
        painter.end()

        return QIcon(pixmap)

    def _load_icon_pair(self, icon_name: str):
        """Prépare les versions inactive et active d'une icône."""

        return (
            self._create_svg_icon(
                icon_name,
                self.ICON_INACTIVE,
            ),
            self._create_svg_icon(
                icon_name,
                self.ICON_ACTIVE,
            ),
        )

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(17, 25, 17, 18)
        layout.setSpacing(9)

        # Identité
        brand = QLabel("J.A.R.V.I.S.")
        brand.setObjectName("BrandTitle")

        subtitle = QLabel("INDUSTRIAL SOLVER")
        subtitle.setObjectName("BrandSubtitle")

        layout.addWidget(brand)
        layout.addWidget(subtitle)
        layout.addSpacing(35)

        section = QLabel("ESPACE DE TRAVAIL")
        section.setObjectName("SectionLabel")

        layout.addWidget(section)
        layout.addSpacing(8)

        # Navigation
        for page_id, icon_name, title in self.NAV_ITEMS:

            inactive_icon, active_icon = self._load_icon_pair(
                icon_name
            )

            self.icon_states[page_id] = (
                inactive_icon,
                active_icon,
            )

            button = QPushButton(title)
            button.setObjectName("NavButton")
            button.setCheckable(True)
            button.setCursor(
                Qt.CursorShape.PointingHandCursor
            )

            button.setIcon(inactive_icon)
            button.setIconSize(QSize(20, 20))
            button.setMinimumHeight(44)

            button.setToolTip(title)

            self.button_group.addButton(button)
            self.buttons[page_id] = button

            button.toggled.connect(
                lambda checked, key=page_id:
                self._update_icon(key, checked)
            )

            button.clicked.connect(
                lambda checked=False, key=page_id:
                self.page_requested.emit(key)
            )

            layout.addWidget(button)

        layout.addStretch()

        # Projet actif
        project_label = QLabel("PROJET ACTIF")
        project_label.setObjectName("SectionLabel")

        self.project_name_label = QLabel("Aucun projet ouvert")
        self.project_name_label.setObjectName("ProjectName")
        self.project_name_label.setWordWrap(True)

        layout.addWidget(project_label)
        layout.addWidget(self.project_name_label)

    def _update_icon(self, page_id: str, checked: bool):
        """Actualise la couleur de l'icône."""

        button = self.buttons.get(page_id)
        icons = self.icon_states.get(page_id)

        if button is None or icons is None:
            return

        inactive_icon, active_icon = icons

        button.setIcon(
            active_icon if checked else inactive_icon
        )

    def set_active(self, page_id: str):
        """Sélectionne la rubrique active."""

        button = self.buttons.get(page_id)

        if button:
            button.setChecked(True)

    def set_active_project(self, name: str | None):
        """Actualise le nom du projet actif dans la navigation."""

        self.project_name_label.setText(
            name if name else "Aucun projet ouvert"
        )
