import sys
import os
import pytest

from PyQt6.QtWidgets import QApplication

from utils.icon_manager import IconManager


@pytest.fixture(scope="session", autouse=True)
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_icon_cache_round_trip(qapp):
    IconManager.clear_cache()
    icon1 = IconManager.create_icon("fa5s.file", size=16, color="#fff", active_color="#000")
    icon2 = IconManager.create_icon("fa5s.file", size=16, color="#fff", active_color="#000")
    assert icon1 is icon2
    IconManager.clear_cache()
    icon3 = IconManager.create_icon("fa5s.file", size=16, color="#fff", active_color="#000")
    assert icon1 is not icon3


def test_pixmap_cache_round_trip(qapp):
    IconManager.clear_cache()
    pix1 = IconManager.create_pixmap("fa5s.file", 16, color="#fff")
    pix2 = IconManager.create_pixmap("fa5s.file", 16, color="#fff")
    assert pix1 is pix2
    IconManager.clear_cache()
    pix3 = IconManager.create_pixmap("fa5s.file", 16, color="#fff")
    assert pix1 is not pix3
