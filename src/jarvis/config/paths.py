
from pathlib import Path

# Racine du projet
PROJECT_ROOT = Path(__file__).resolve().parents[3]

# Ressources
RESOURCES_DIR = PROJECT_ROOT / "resources"
STYLES_DIR = RESOURCES_DIR / "styles"
ASSETS_DIR = PROJECT_ROOT / "assets"

# Icônes
ICONS_DIR = ASSETS_DIR / "icons"
NAVIGATION_ICONS_DIR = ICONS_DIR / "navigation"

# Feuille de style
MAIN_STYLESHEET = STYLES_DIR / "main.qss"

# Identité
APP_NAME = "J.A.R.V.I.S."
APP_FULL_NAME = "Just A Rather Very Industrial Solver"
APP_VERSION = "2.0.0a1"
