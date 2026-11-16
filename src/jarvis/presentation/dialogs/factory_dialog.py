from uuid import UUID

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QTextEdit,
    QVBoxLayout,
)

from jarvis.application.services.factory_service import FactoryService
from jarvis.application.services.park_service import ParkService
from jarvis.domain.entities.factory import Factory
from jarvis.domain.entities.park import Park
from jarvis.domain.entities.production import ProductionPlan
from jarvis.domain.entities.project import Project
from jarvis.presentation.numeric_format import format_decimal


class FactoryDialog(QDialog):
    """Formulaire de création ou de renommage d'une usine."""

    def __init__(self, factory: Factory | None = None, parent=None) -> None:
        super().__init__(parent)
        self.factory = factory
        self.setWindowTitle("Renommer l'usine" if factory else "Nouvelle usine")
        self.setMinimumWidth(460)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(14)

        title = QLabel("Identité de l'usine")
        title.setObjectName("DialogTitle")
        subtitle = QLabel(
            "Une usine appartient à un seul parc. Les calculs enregistrés y resteront associés."
        )
        subtitle.setObjectName("PageSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        form = QFormLayout()
        form.setSpacing(12)
        self.name_input = QLineEdit()
        self.name_input.setObjectName("FormInput")
        self.name_input.setMaxLength(100)
        self.name_input.setPlaceholderText("Ex. : Usine de plaques de fer")
        self.description_input = QTextEdit()
        self.description_input.setObjectName("FormInput")
        self.description_input.setMaximumHeight(90)
        self.description_input.setPlaceholderText("Fonction ou remarques sur cette usine…")
        form.addRow("Nom :", self.name_input)
        form.addRow("Description :", self.description_input)
        layout.addLayout(form)

        if factory is not None:
            self.name_input.setText(factory.name)
            self.description_input.setPlainText(factory.description)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.button(QDialogButtonBox.StandardButton.Save).setText(
            "Enregistrer" if factory else "Créer l'usine"
        )
        self.buttons.accepted.connect(self._validate)
        self.buttons.rejected.connect(self.reject)
        layout.addStretch()
        layout.addWidget(self.buttons)

    def _validate(self) -> None:
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "Nom manquant", "Le nom de l'usine est obligatoire.")
            self.name_input.setFocus()
            return
        self.accept()

    def get_values(self) -> dict[str, str]:
        return {
            "name": self.name_input.text().strip(),
            "description": self.description_input.toPlainText().strip(),
        }


class SaveSimulationDialog(QDialog):
    """Choisit le parc et l'usine dans lesquels enregistrer un résultat."""

    CREATE_FACTORY = "__create_factory__"

    def __init__(
        self,
        project: Project,
        plan: ProductionPlan,
        park_service: ParkService,
        factory_service: FactoryService,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.project = project
        self.plan = plan
        self.park_service = park_service
        self.factory_service = factory_service
        self._parks: list[Park] = []

        self.setWindowTitle("Enregistrer la simulation")
        self.setMinimumWidth(520)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(14)
        title = QLabel("Enregistrer ce résultat dans une usine")
        title.setObjectName("DialogTitle")
        subtitle = QLabel(
            f"{plan.target_name} · {format_decimal(plan.target_rate_per_minute, max_decimals=3)} "
            f"{plan.target_unit_label}/min · instantané du calcul actuel"
        )
        subtitle.setObjectName("PageSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        form = QFormLayout()
        form.setSpacing(12)
        self.park_combo = QComboBox()
        self.park_combo.setObjectName("FormInput")
        self.factory_combo = QComboBox()
        self.factory_combo.setObjectName("FormInput")
        self.factory_name_input = QLineEdit()
        self.factory_name_input.setObjectName("FormInput")
        self.factory_name_input.setMaxLength(100)
        self.factory_name_input.setText(f"Usine {plan.target_name}")
        self.scenario_name_input = QLineEdit()
        self.scenario_name_input.setObjectName("FormInput")
        self.scenario_name_input.setMaxLength(120)
        self.scenario_name_input.setText(f"Simulation {plan.target_name}")
        self.description_input = QLineEdit()
        self.description_input.setObjectName("FormInput")
        self.description_input.setMaxLength(500)
        self.description_input.setPlaceholderText("Description facultative")
        form.addRow("Parc :", self.park_combo)
        form.addRow("Usine :", self.factory_combo)
        form.addRow("Nom de la nouvelle usine :", self.factory_name_input)
        form.addRow("Nom du scénario :", self.scenario_name_input)
        form.addRow("Description de l'usine :", self.description_input)
        layout.addLayout(form)

        self.park_combo.currentIndexChanged.connect(self._refresh_factories)
        self.factory_combo.currentIndexChanged.connect(self._update_factory_fields)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.button(QDialogButtonBox.StandardButton.Save).setText("Enregistrer le calcul")
        self.buttons.accepted.connect(self._validate)
        self.buttons.rejected.connect(self.reject)
        layout.addStretch()
        layout.addWidget(self.buttons)

        try:
            self._parks = self.park_service.get_all_parks(project.id)
        except Exception as error:
            QMessageBox.critical(
                self,
                "Chargement des parcs impossible",
                str(error),
            )
        for park in self._parks:
            self.park_combo.addItem(park.name, str(park.id))
        if not self._parks:
            self.park_combo.addItem("Aucun parc disponible", "")
            self.park_combo.setEnabled(False)
            self.factory_combo.setEnabled(False)
            self.factory_name_input.setEnabled(False)
            self.buttons.button(QDialogButtonBox.StandardButton.Save).setEnabled(False)
        else:
            self._refresh_factories()

    def _refresh_factories(self, _index: int = -1) -> None:
        park_id_text = self.park_combo.currentData()
        self.factory_combo.blockSignals(True)
        self.factory_combo.clear()
        self.factory_combo.addItem("+ Créer une nouvelle usine", self.CREATE_FACTORY)
        if park_id_text:
            try:
                factories = self.factory_service.list_factories(
                    self.project.id,
                    UUID(str(park_id_text)),
                )
            except Exception as error:
                QMessageBox.critical(self, "Chargement des usines impossible", str(error))
                factories = []
            for factory in factories:
                self.factory_combo.addItem(factory.name, str(factory.id))
        self.factory_combo.blockSignals(False)
        self._update_factory_fields()

    def _update_factory_fields(self, _index: int = -1) -> None:
        is_new = self.factory_combo.currentData() == self.CREATE_FACTORY
        self.factory_name_input.setEnabled(is_new)
        self.description_input.setEnabled(is_new)

    def _validate(self) -> None:
        if not self.park_combo.currentData():
            QMessageBox.warning(self, "Parc manquant", "Sélectionne un parc industriel.")
            return
        if not self.scenario_name_input.text().strip():
            QMessageBox.warning(self, "Nom manquant", "Le nom du scénario est obligatoire.")
            self.scenario_name_input.setFocus()
            return
        if (
            self.factory_combo.currentData() == self.CREATE_FACTORY
            and not self.factory_name_input.text().strip()
        ):
            QMessageBox.warning(
                self,
                "Nom manquant",
                "Le nom de la nouvelle usine est obligatoire.",
            )
            self.factory_name_input.setFocus()
            return
        self.accept()

    def get_values(self) -> dict:
        factory_data = self.factory_combo.currentData()
        return {
            "park_id": UUID(str(self.park_combo.currentData())),
            "factory_id": None if factory_data == self.CREATE_FACTORY else UUID(str(factory_data)),
            "factory_name": (
                self.factory_name_input.text().strip()
                if factory_data == self.CREATE_FACTORY
                else None
            ),
            "factory_description": self.description_input.text().strip(),
            "scenario_name": self.scenario_name_input.text().strip(),
        }
