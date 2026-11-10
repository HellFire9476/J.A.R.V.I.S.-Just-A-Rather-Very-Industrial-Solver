
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)


class DashboardPage(QWidget):

    open_parks_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setObjectName("DashboardPage")

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 28, 30, 28)
        layout.setSpacing(22)

        # En-tête
        header = QHBoxLayout()

        title_area = QVBoxLayout()

        title = QLabel("Tableau de bord")
        title.setObjectName("PageTitle")

        subtitle = QLabel(
            "Supervision de votre infrastructure industrielle."
        )
        subtitle.setObjectName("PageSubtitle")

        title_area.addWidget(title)
        title_area.addWidget(subtitle)

        header.addLayout(title_area)
        header.addStretch()

        # Sélecteur simplifié / avancé
        self.simple_button = QPushButton("Vue simplifiée")
        self.advanced_button = QPushButton("Vue avancée")

        for button in (self.simple_button, self.advanced_button):
            button.setObjectName("ModeButton")
            button.setCheckable(True)
            button.setMinimumHeight(38)

        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)

        self.mode_group.addButton(self.simple_button, 0)
        self.mode_group.addButton(self.advanced_button, 1)

        self.simple_button.setChecked(True)

        self.simple_button.clicked.connect(
            lambda checked=False: self._change_view(0)
        )

        self.advanced_button.clicked.connect(
            lambda checked=False: self._change_view(1)
        )

        header.addWidget(self.simple_button)
        header.addWidget(self.advanced_button)

        layout.addLayout(header)

        # Contenu des deux modes
        self.view_stack = QStackedWidget()

        self.view_stack.addWidget(self._build_simple_view())
        self.view_stack.addWidget(self._build_advanced_view())

        layout.addWidget(self.view_stack)

    def _metric_card(self, name, value, description):
        card = QFrame()
        card.setObjectName("MetricCard")

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 16, 18, 16)
        card_layout.setSpacing(7)

        name_label = QLabel(name)
        name_label.setObjectName("MetricLabel")

        value_label = QLabel(value)
        value_label.setObjectName("MetricValue")

        description_label = QLabel(description)
        description_label.setObjectName("MetricDescription")
        description_label.setWordWrap(True)

        card_layout.addWidget(name_label)
        card_layout.addWidget(value_label)
        card_layout.addWidget(description_label)

        return card

    def _build_simple_view(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(20)

        # Panneau de bienvenue
        welcome = QFrame()
        welcome.setObjectName("WelcomePanel")

        welcome_layout = QVBoxLayout(welcome)
        welcome_layout.setContentsMargins(25, 24, 25, 24)
        welcome_layout.setSpacing(12)

        eyebrow = QLabel("CENTRE DE CONTRÔLE INDUSTRIEL")
        eyebrow.setObjectName("Eyebrow")

        welcome_title = QLabel("Bienvenue dans J.A.R.V.I.S.")
        welcome_title.setObjectName("WelcomeTitle")

        description = QLabel(
            "Organisez vos parcs industriels, gérez vos usines "
            "et optimisez votre production Satisfactory."
        )
        description.setObjectName("WelcomeDescription")
        description.setWordWrap(True)

        open_parks = QPushButton("Accéder aux parcs industriels")
        open_parks.setObjectName("PrimaryButton")
        open_parks.setCursor(Qt.CursorShape.PointingHandCursor)

        open_parks.clicked.connect(
            lambda checked=False: self.open_parks_requested.emit()
        )

        welcome_layout.addWidget(eyebrow)
        welcome_layout.addWidget(welcome_title)
        welcome_layout.addWidget(description)
        welcome_layout.addSpacing(8)
        welcome_layout.addWidget(open_parks, 0, Qt.AlignmentFlag.AlignLeft)

        layout.addWidget(welcome)

        # Indicateurs
        metrics_title = QLabel("VUE GLOBALE")
        metrics_title.setObjectName("SectionLabel")

        layout.addWidget(metrics_title)

        metrics = QGridLayout()
        metrics.setSpacing(14)

        metrics.addWidget(
            self._metric_card(
                "Parcs industriels",
                "—",
                "Aucune partie chargée",
            ), 0, 0
        )

        metrics.addWidget(
            self._metric_card(
                "Production",
                "—",
                "En attente de configuration",
            ), 0, 1
        )

        metrics.addWidget(
            self._metric_card(
                "Énergie",
                "—",
                "Bilan énergétique indisponible",
            ), 0, 2
        )

        layout.addLayout(metrics)
        layout.addStretch()

        return page

    def _build_advanced_view(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(18)

        heading = QLabel("Analyse industrielle avancée")
        heading.setObjectName("SectionTitle")

        description = QLabel(
            "Les visualisations techniques seront disponibles "
            "une fois votre infrastructure configurée."
        )
        description.setObjectName("PageSubtitle")
        description.setWordWrap(True)

        layout.addWidget(heading)
        layout.addWidget(description)

        grid = QGridLayout()
        grid.setSpacing(14)

        analyses = [
            ("Flux de production", "Visualisation des chaînes et débits."),
            ("Réseau industriel", "Connexions et transferts entre parcs."),
            ("Analyse énergétique", "Production et consommation électrique."),
            ("Dépendances", "Relations entre recettes et ressources."),
        ]

        for index, (name, detail) in enumerate(analyses):
            card = QFrame()
            card.setObjectName("MetricCard")

            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(18, 18, 18, 18)

            name_label = QLabel(name)
            name_label.setObjectName("SectionTitle")

            detail_label = QLabel(detail)
            detail_label.setObjectName("MetricDescription")
            detail_label.setWordWrap(True)

            state_label = QLabel("EN ATTENTE DE DONNÉES")
            state_label.setObjectName("Eyebrow")

            card_layout.addWidget(name_label)
            card_layout.addWidget(detail_label)
            card_layout.addStretch()
            card_layout.addWidget(state_label)

            grid.addWidget(card, index // 2, index % 2)

        layout.addLayout(grid)
        layout.addStretch()

        return page

    def _change_view(self, index: int):
        self.view_stack.setCurrentIndex(index)
