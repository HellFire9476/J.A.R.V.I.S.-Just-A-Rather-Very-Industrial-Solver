
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from jarvis.presentation.pages.dashboard.page import DashboardPage
from jarvis.presentation.widgets.sidebar import Sidebar


class PlaceholderPage(QWidget):
    """Page temporaire en attendant le développement du module."""

    def __init__(self, title: str, description: str):
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(35, 35, 35, 35)
        layout.setSpacing(12)

        title_label = QLabel(title)
        title_label.setObjectName("PageTitle")

        description_label = QLabel(description)
        description_label.setObjectName("PageSubtitle")

        status = QLabel("MODULE EN CONSTRUCTION")
        status.setObjectName("Eyebrow")

        layout.addWidget(title_label)
        layout.addWidget(description_label)
        layout.addSpacing(15)
        layout.addWidget(status)
        layout.addStretch()


class MainWindow(QMainWindow):

    PAGE_INFO = {
        "parks": (
            "Parcs industriels",
            "Gestion et organisation de vos parcs.",
        ),
        "network": (
            "Réseau industriel",
            "Gestion des échanges entre vos installations.",
        ),
        "extraction": (
            "Extraction",
            "Gestion des gisements et des foreuses.",
        ),
        "energy": (
            "Énergie",
            "Gestion de votre production énergétique.",
        ),
        "recipes": (
            "Recettes",
            "Catalogue des recettes et de leurs variantes.",
        ),
        "simulations": (
            "Simulations",
            "Analyse des déficits et optimisation industrielle.",
        ),
    }

    def __init__(self):
        super().__init__()

        self.setWindowTitle(
            "J.A.R.V.I.S. — Just A Rather Very Industrial Solver"
        )

        self.resize(1440, 900)
        self.setMinimumSize(1100, 720)

        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Barre supérieure
        topbar = QFrame()
        topbar.setObjectName("TopBar")
        topbar.setFixedHeight(46)

        topbar_layout = QHBoxLayout(topbar)
        topbar_layout.setContentsMargins(22, 0, 22, 0)

        version = QLabel("J.A.R.V.I.S. 2.0  /  ALPHA 1")
        version.setObjectName("TopbarVersion")

        project = QLabel("●  AUCUN PROJET CHARGÉ")
        project.setObjectName("TopbarProject")

        topbar_layout.addWidget(version)
        topbar_layout.addStretch()
        topbar_layout.addWidget(project)

        root_layout.addWidget(topbar)

        # Corps de l'application
        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        self.sidebar = Sidebar()
        self.sidebar.page_requested.connect(self.show_page)

        self.page_stack = QStackedWidget()
        self.pages = {}

        # Tableau de bord
        dashboard = DashboardPage()
        dashboard.open_parks_requested.connect(
            lambda: self.show_page("parks")
        )

        self.pages["dashboard"] = dashboard
        self.page_stack.addWidget(dashboard)

        # Autres modules temporaires
        for page_id, (title, description) in self.PAGE_INFO.items():
            page = PlaceholderPage(title, description)
            self.pages[page_id] = page
            self.page_stack.addWidget(page)

        body_layout.addWidget(self.sidebar)
        body_layout.addWidget(self.page_stack, 1)

        root_layout.addWidget(body, 1)

        self.sidebar.set_active("dashboard")
        self.show_page("dashboard")

    def show_page(self, page_id: str):
        page = self.pages.get(page_id)

        if page is None:
            return

        self.page_stack.setCurrentWidget(page)
        self.sidebar.set_active(page_id)
