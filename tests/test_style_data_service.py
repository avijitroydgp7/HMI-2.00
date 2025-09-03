from PyQt6.QtTest import QSignalSpy

from services.data_context import DataContext
from services.style_data_service import StyleDataService, _QT_DEFAULT_STYLE_ID


def test_init_emits_styles_changed(qapp):
    bus = DataContext()
    spy = QSignalSpy(bus.styles_changed)
    StyleDataService(bus)
    assert len(spy) == 1
    assert spy[0][0]["style_id"] == _QT_DEFAULT_STYLE_ID


def test_default_hover_properties_copy(qapp):
    service = StyleDataService(DataContext())
    default_style = service.get_default_style()
    props = default_style["properties"]
    hover = default_style["hover_properties"]
    assert props == hover
    assert props is not hover
