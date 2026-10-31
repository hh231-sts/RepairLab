from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "sqlite:///./data/repairlab.db"
    data_root: Path = Path("data")
    repository_root: Path = Path("fixtures/repos")
    task_root: Path = Path("fixtures/tasks")
    model_calls_enabled: bool = False
    embedding_enabled: bool = False
    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-flash"
    input_cny_per_million: float = Field(0, ge=0)
    output_cny_per_million: float = Field(0, ge=0)
    price_snapshot: str = "unconfigured"
    embedding_model: str = "intfloat/multilingual-e5-small"
    embedding_revision: str = "fd1525a9fd15316a2d503bf26ab031a61d056e98"
    api_token: str = "local-dev-change-me"
    lease_seconds: int = Field(30, ge=3)
    tool_timeout: int = Field(60, ge=1, le=300)
    poll_seconds: float = 0.5
    global_budget_cny: float = Field(2000, gt=0, le=2000)
    sandbox_image: str = "repairlab-sandbox:local"
    cors_origin: str = "http://localhost:5173"

    def public_model_config(self) -> dict:
        key_present = bool(self.deepseek_api_key.strip())
        prices_present = (
            self.price_snapshot != "unconfigured"
            and self.input_cny_per_million > 0
            and self.output_cny_per_million > 0
        )
        reason = (
            "model_disabled"
            if not self.model_calls_enabled
            else "api_key_missing"
            if not key_present
            else "price_snapshot_missing"
            if not prices_present
            else None
        )
        return {
            "model_calls_enabled": self.model_calls_enabled,
            "model_ready": reason is None,
            "api_key_configured": key_present,
            "price_configured": prices_present,
            "model": self.deepseek_model,
            "default_source": "deepseek" if self.model_calls_enabled else "scripted",
            "reason": reason,
            "global_budget_cny": self.global_budget_cny,
            "embedding_enabled": self.embedding_enabled and self.model_calls_enabled,
        }

    def prepare(self) -> None:
        self.data_root.mkdir(parents=True, exist_ok=True)
        for name in ("artifacts", "workspaces", "snapshots", "verifiers"):
            (self.data_root / name).mkdir(exist_ok=True)
