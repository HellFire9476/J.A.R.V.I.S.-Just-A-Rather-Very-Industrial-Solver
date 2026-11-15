"""Vérifie que les simulations ne dépendent pas d'une partie active."""

import pytest


def test_simulations_page_is_not_restricted_to_an_active_project() -> None:
    pytest.importorskip("PySide6")

    from jarvis.app.main_window import MainWindow

    assert "simulations" not in MainWindow.PROJECT_REQUIRED_PAGES


def test_simulations_page_has_no_project_binding() -> None:
    pytest.importorskip("PySide6")

    from PySide6.QtWidgets import QApplication

    from jarvis.presentation.pages.simulations.page import SimulationsPage

    app = QApplication.instance() or QApplication([])
    page = SimulationsPage(service=object())

    assert not hasattr(page, "project")
    assert not hasattr(page, "set_project")
    assert page.scope_label.text() == (
        "CALCUL THÉORIQUE · INDÉPENDANT DES PARTIES ET DES PARCS"
    )
    assert "aucun stock" in page.scope_label.toolTip().casefold()

    page.close()
    app.processEvents()
