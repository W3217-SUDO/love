import json
import logging

from app.logging import setup_logging


def test_logger_emits_json_with_required_fields(capsys):
    setup_logging(level="INFO")
    logger = logging.getLogger("test")
    logger.info("hello", extra={"user_id": 42, "request_id": "abc"})
    captured = capsys.readouterr()
    record = json.loads(captured.err.strip().splitlines()[-1])
    assert record["msg"] == "hello"
    assert record["level"] == "INFO"
    assert record["user_id"] == 42
    assert record["request_id"] == "abc"
    assert "ts" in record


def test_logger_redacts_password_fields(capsys):
    setup_logging(level="INFO")
    logger = logging.getLogger("test")
    logger.info("login", extra={"password": "secret", "token": "tk"})
    captured = capsys.readouterr()
    record = json.loads(captured.err.strip().splitlines()[-1])
    assert record["password"] == "***"
    assert record["token"] == "***"
