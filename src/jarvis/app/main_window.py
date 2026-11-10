
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from jarvis.app.navigation import PlaceholderPage
from jarvis.domain.entities.project import Project
from jarvis.presentation.pages.dashboard.page import DashboardPage
from jarvis.presentation.pages.projects.page import ProjectPage
from jarvis.presentation.widgets.sidebar import Sidebar


class MainWindow(QMainWindow):
    """Fenêtre principale de J.A.R.V.I.S."""

    PAGE_INFO = {
        "parks": (
            "Parcs industriels",
            "Gestion et organisation de vos parcs.",
        ),
        "network": (
            "Réseau industriel",
            "Gestion des échanges entre installations.",
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

        self.active_project: Project | None = None

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

        self.project_status = QLabel(
            "●  AUCUN PROJET CHARGÉ"
        )
        self.project_status.setObjectName("TopbarProject")

        topbar_layout.addWidget(version)
        topbar_layout.addStretch()
        topbar_layout.addWidget(self.project_status)

        root_layout.addWidget(topbar)

        # Zone principale
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
            self._open_parks_from_dashboard
        )

        self._register_page("dashboard", dashboard)

        # Gestion des projets
        projects_page = ProjectPage()

        projects_page.project_opened.connect(
            self._activate_project
        )

        projects_page.project_updated.connect(
            self._update_active_project
        )

        self._register_page("projects", projects_page)

        self.projects_page = projects_page

        # Modules industriels
        for page_id, (title, description) in self.PAGE_INFO.items():
            page = PlaceholderPage(title, description)
            self._register_page(page_id, page)

        body_layout.addWidget(self.sidebar)
        body_layout.addWidget(self.page_stack, 1)

        root_layout.addWidget(body, 1)

        self.sidebar.set_active("dashboard")
        self.show_page("dashboard")

    def _register_page(self, page_id: str, page: QWidget):
        """Enregistre une page dans la navigation."""

        self.pages[page_id] = page
        self.page_stack.addWidget(page)

    def show_page(self, page_id: str):
        """Affiche la rubrique demandée."""

        page = self.pages.get(page_id)

        if page is None:
            return

        industrial_pages = set(self.PAGE_INFO)

        # Un projet doit être ouvert avant d'accéder
        # aux fonctionnalités industrielles.
        if (
            page_id in industrial_pages
            and self.active_project is None
        ):
            page_id = "projects"
            page = self.pages[page_id]

        self.page_stack.setCurrentWidget(page)
        self.sidebar.set_active(page_id)

        if page_id == "projects":
            self.projects_page.refresh()

    def _open_parks_from_dashboard(self):
        """Dirige vers les parcs ou vers les projets."""

        if self.active_project is None:
            self.show_page("projects")
        else:
            self.show_page("parks")

    def _activate_project(self, project: Project):
        """Définit la partie actuellement ouverte."""

        self.active_project = project

        self.project_status.setText(
            f"●  {project.name.upper()}"
        )

        self.sidebar.set_active_project(project.name)

        self.setWindowTitle(
            f"J.A.R.V.I.S. — {project.name}"
        )

        self.show_page("dashboard")

    def _update_active_project(self, project: Project):
        """Actualise l'affichage après modification."""

        if (
            self.active_project is not None
            and self.active_project.id == project.id
        ):
            self.active_project = project

            self.project_status.setText(
                f"●  {project.name.upper()}"
            )

            self.sidebar.set_active_project(project.name)

            self.setWindowTitle(
                f"J.A.R.V.I.S. — {project.name}"
            )
