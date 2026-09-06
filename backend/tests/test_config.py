from app.config import Settings


def test_cors_origins_comma_separated():
    s = Settings(CORS_ORIGINS="https://example.com, https://app.example.com")
    assert s.CORS_ORIGINS == ["https://example.com", "https://app.example.com"]


def test_cors_origins_json_list():
    s = Settings(CORS_ORIGINS='["https://selfstudy.dev", "http://localhost:3000"]')
    assert s.CORS_ORIGINS == ["https://selfstudy.dev", "http://localhost:3000"]


def test_cors_origins_python_list():
    s = Settings(CORS_ORIGINS=["https://selfstudy.dev"])
    assert s.CORS_ORIGINS == ["https://selfstudy.dev"]


def test_environment_setting():
    s = Settings(ENVIRONMENT="production")
    assert s.ENVIRONMENT == "production"
