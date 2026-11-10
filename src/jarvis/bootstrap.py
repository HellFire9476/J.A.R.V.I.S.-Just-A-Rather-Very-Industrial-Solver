
import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from jarvis.app.main_window import MainWindow
from jarvis.config.paths import (
    APP_FULL_NAME,
    APP_NAME,
    APP_VERSION,
    MAIN_STYLESHEET,
)


def main() -> int:
    app = QApplication(sys.argv)

    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(
        f"{APP_NAME} — {APP_FULL_NAME}"
    )
    app.setApplicationVersion(APP_VERSION)

    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))

    # Chargement du thème graphique
    if MAIN_STYLESHEET.exists():
        stylesheet = MAIN_STYLESHEET.read_text(encoding="utf-8")
        app.setStyleSheet(stylesheet)
    else:
        print(f"Attention : feuille de style introuvable : {MAIN_STYLESHEET}")

    window = MainWindow()
    window.show()

    return app.exec()
