import pytest

from app import get_flask_runtime_config


def test_runtime_config_uses_safe_local_defaults(monkeypatch):
    monkeypatch.delenv("FLASK_ENV", raising=False)
    monkeypatch.delenv("FLASK_HOST", raising=False)
    monkeypatch.delenv("FLASK_PORT", raising=False)

    assert get_flask_runtime_config() == {
        "host": "127.0.0.1",
        "port": 5001,
        "debug": True,
    }


def test_runtime_config_disables_debug_in_production(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "production")

    assert get_flask_runtime_config()["debug"] is False


def test_runtime_config_enables_debug_only_for_development(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", " DEVELOPMENT ")

    assert get_flask_runtime_config()["debug"] is True


def test_runtime_config_respects_custom_host_and_port(monkeypatch):
    monkeypatch.setenv("FLASK_HOST", "0.0.0.0")
    monkeypatch.setenv("FLASK_PORT", "6001")

    config = get_flask_runtime_config()

    assert config["host"] == "0.0.0.0"
    assert config["port"] == 6001


@pytest.mark.parametrize("invalid_port", ["invalid", "", "0", "65536"])
def test_runtime_config_rejects_invalid_port(monkeypatch, invalid_port):
    monkeypatch.setenv("FLASK_PORT", invalid_port)

    with pytest.raises(ValueError, match="FLASK_PORT"):
        get_flask_runtime_config()
