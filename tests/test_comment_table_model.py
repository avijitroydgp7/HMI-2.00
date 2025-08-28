import pytest
from PyQt6.QtCore import QCoreApplication

from components.comment_table_model import CommentTableModel


@pytest.fixture(scope="module")
def app():
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    return app


def _model_with_values():
    model = CommentTableModel(["col1", "col2"])
    for i in range(5):
        model.insertRow(i)
    model._suspend_history = True
    for i in range(5):
        model.setData(model.index(i, 1), i + 1)
    model._suspend_history = False
    return model


def test_sum_lowercase_function(app):
    model = _model_with_values()
    model._suspend_history = True
    model.setData(model.index(0, 2), "=sum(a1:a5)")
    model._suspend_history = False
    assert model.data(model.index(0, 2)) == 15


def test_sum_mixed_case_function(app):
    model = _model_with_values()
    model._suspend_history = True
    model.setData(model.index(0, 2), "=Sum(A1:A5)")
    model._suspend_history = False
    assert model.data(model.index(0, 2)) == 15
