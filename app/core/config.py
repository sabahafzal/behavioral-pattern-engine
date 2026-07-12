"""
Application settings, loaded from environment variables (or a local .env
file during development). Never commit real API keys — .env is gitignored.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Comma-separated list of valid API keys. In production, set this via
    # your host's environment variable UI (Railway/Fly.io), not a file.
    api_keys: str = "dev-local-key"

    # Toggle for local development vs. deployed environments
    environment: str = "development"

    @property
    def valid_api_keys(self) -> set[str]:
        return {key.strip() for key in self.api_keys.split(",") if key.strip()}


settings = Settings()
