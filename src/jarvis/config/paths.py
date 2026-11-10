
from pathlib import Path

# ==========================================================
# IDENTITE DE L'APPLICATION
# ==========================================================

APP_NAME = "J.A.R.V.I.S."
APP_FULL_NAME = "Just A Rather Very Industrial Solver"
APP_VERSION = "2.0.0a1"


# ==========================================================
# RACINE DU PROJET
# ==========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]


# ==========================================================
# RESSOURCES DE L'APPLICATION
# ==========================================================

RESOURCES_DIR = PROJECT_ROOT / "resources"
STYLES_DIR = RESOURCES_DIR / "styles"
MAIN_STYLESHEET = STYLES_DIR / "main.qss"

ASSETS_DIR = PROJECT_ROOT / "assets"
ICONS_DIR = ASSETS_DIR / "icons"
NAVIGATION_ICONS_DIR = ICONS_DIR / "navigation"


# ==========================================================
# DONNEES UTILISATEUR
# ==========================================================

# Les parties ne sont pas stockées dans le dépôt GitHub.
USER_DATA_DIR = Path.home() / "Documents" / "J.A.R.V.I.S."

PROJECTS_DIR = USER_DATA_DIR / "Projects"
SETTINGS_DIR = USER_DATA_DIR / "Settings"
LOGS_DIR = USER_DATA_DIR / "Logs"

SETTINGS_FILE = SETTINGS_DIR / "settings.json"
