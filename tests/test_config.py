from app.config import Settings


def test_settings_loads_required_fields(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("SECRET_KEY", "a" * 64)
    monkeypatch.setenv(
        "DATABASE_URL",
        "mysql+pymysql://u:p@127.0.0.1/db?charset=utf8mb4",
    )
    monkeypatch.setenv("UPLOAD_DIR", "/tmp/uploads")
    monkeypatch.setenv("BACKUP_DIR", "/tmp/backups")
    monkeypatch.setenv("LOG_DIR", "/tmp/logs")
    s = Settings()
    assert s.app_env == "test"
    assert s.secret_key == "a" * 64
    assert s.session_max_age_days == 30  # default
    assert s.max_image_upload_bytes == 10 * 1024 * 1024
    assert s.max_pdf_upload_bytes == 20 * 1024 * 1024


def test_settings_loads_upload_size_limits(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("SECRET_KEY", "a" * 64)
    monkeypatch.setenv(
        "DATABASE_URL",
        "mysql+pymysql://u:p@127.0.0.1/db?charset=utf8mb4",
    )
    monkeypatch.setenv("UPLOAD_DIR", "/tmp/uploads")
    monkeypatch.setenv("BACKUP_DIR", "/tmp/backups")
    monkeypatch.setenv("LOG_DIR", "/tmp/logs")
    monkeypatch.setenv("MAX_IMAGE_UPLOAD_BYTES", "12345")
    monkeypatch.setenv("MAX_PDF_UPLOAD_BYTES", "67890")

    s = Settings()

    assert s.max_image_upload_bytes == 12345
    assert s.max_pdf_upload_bytes == 67890


def test_settings_secret_key_min_length(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("SECRET_KEY", "tooshort")
    monkeypatch.setenv("DATABASE_URL", "mysql+pymysql://u:p@127.0.0.1/db")
    monkeypatch.setenv("UPLOAD_DIR", "/tmp/u")
    monkeypatch.setenv("BACKUP_DIR", "/tmp/b")
    monkeypatch.setenv("LOG_DIR", "/tmp/l")
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        Settings()
