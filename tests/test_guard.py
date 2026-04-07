import jeff.guard as guard
from jeff.guard import Ruling, classifier_check


def test_classifier_check_is_noop_without_model(monkeypatch):
    monkeypatch.setattr(guard, "is_available", lambda: False)
    assert classifier_check("hello") is None


def test_classifier_check_parses_safe(monkeypatch):
    class Response:
        error = ""
        content = "SAFE"

    monkeypatch.setattr(guard, "is_available", lambda: True)
    monkeypatch.setattr(guard, "list_models", lambda: ["llama-guard3:1b"])
    monkeypatch.setattr(guard, "generate", lambda *args, **kwargs: Response())
    result = classifier_check("hello")
    assert result is not None
    assert result.ruling == Ruling.CLEAN


def test_classifier_check_parses_unsafe(monkeypatch):
    class Response:
        error = ""
        content = "UNSAFE"

    monkeypatch.setattr(guard, "is_available", lambda: True)
    monkeypatch.setattr(guard, "list_models", lambda: ["llama-guard3:1b"])
    monkeypatch.setattr(guard, "generate", lambda *args, **kwargs: Response())
    result = classifier_check("hello")
    assert result is not None
    assert result.ruling == Ruling.DICK_MOVE
