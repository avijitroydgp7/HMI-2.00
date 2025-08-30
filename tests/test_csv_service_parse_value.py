import pytest

from services.csv_service import csv_service, CsvService


def test_parse_value_bool():
    # True cases
    assert csv_service._parse_value('BOOL', 'true') is True
    assert csv_service._parse_value('BOOL', 'TRUE') is True
    assert csv_service._parse_value('BOOL', '1') is True
    # False cases
    assert csv_service._parse_value('BOOL', 'false') is False
    assert csv_service._parse_value('BOOL', '0') is False
    assert csv_service._parse_value('BOOL', '') is False
    assert csv_service._parse_value('BOOL', None) is False


@pytest.mark.parametrize("dt", ['INT', 'DINT'])
def test_parse_value_int_like(dt):
    assert csv_service._parse_value(dt, '123') == 123
    assert csv_service._parse_value(dt, '  42  ') == 42
    assert csv_service._parse_value(dt, '') == 0
    with pytest.raises(ValueError):
        csv_service._parse_value(dt, 'abc')


def test_parse_value_real():
    assert csv_service._parse_value('REAL', '3.14') == pytest.approx(3.14)
    assert csv_service._parse_value('REAL', '2') == pytest.approx(2.0)
    assert csv_service._parse_value('REAL', '') == pytest.approx(0.0)
    with pytest.raises(ValueError):
        csv_service._parse_value('REAL', 'abc')


def test_parse_value_default_passthrough():
    # STRING and unknown types pass through the original string
    assert csv_service._parse_value('STRING', 'hello') == 'hello'
    assert csv_service._parse_value('SOMETHING_ELSE', 'x') == 'x'

