from jeff.bell import status, summary
from jeff.personality import ask_dont_tell


def test_ask_dont_tell_leaves_questions_alone():
    assert ask_dont_tell("What broke?") == "What broke?"


def test_ask_dont_tell_reframes_flat_statements():
    framed = ask_dont_tell("This architecture is ready.")
    assert "Evaluate this statement critically" in framed
    assert framed.endswith("This architecture is ready.")


def test_bell_reports_live_server_surface():
    bell = status()
    assert bell["implemented"] is True
    assert "stdio" == bell["default_transport"]
    assert "mcp server" in summary().lower()
