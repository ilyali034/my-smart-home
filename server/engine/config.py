import os
from dataclasses import dataclass
from pathlib import Path


def _read_origins() -> list[str]:
	value = os.getenv("SMART_HOME_CORS_ORIGINS", "http://localhost:3000,http://localhost:5173")
	return [origin.strip() for origin in value.split(",") if origin.strip()]


@dataclass(frozen=True)
class Settings:
	database_path: str = os.getenv("SMART_HOME_DB_PATH", "data/smart_home.db")
	secret_key: str = os.getenv("SMART_HOME_SECRET_KEY", "dev-secret-change-me")
	access_token_ttl_minutes: int = int(os.getenv("SMART_HOME_ACCESS_TOKEN_TTL_MINUTES", "60"))
	cors_origins: list[str] | None = None

	def __post_init__(self) -> None:
		if self.access_token_ttl_minutes <= 0:
			raise ValueError("SMART_HOME_ACCESS_TOKEN_TTL_MINUTES must be positive")

	def prepare_database_directory(self) -> None:
		if self.database_path != ":memory:":
			Path(self.database_path).expanduser().parent.mkdir(parents=True, exist_ok=True)


settings = Settings(cors_origins=_read_origins())
