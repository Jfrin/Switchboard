from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    gemini_api_key: str = ""
    # Tried in order; a model whose daily quota is spent is skipped until it resets.
    gemini_models: str = "gemini-3.5-flash-lite,gemini-3.1-flash-lite"
    # Optional single ordered list across providers. Entries are plain Gemini model names or
    # "azure:<deployment name>". Empty means use GEMINI_MODELS.
    llm_models: str = ""
    azure_endpoint: str = ""  # e.g. https://<resource>.openai.azure.com/openai/v1/
    azure_api_key: str = ""
    azure_batch_size: int = 20  # eval only: emails per request when Azure is first in line
    azure_rpm: int = 60  # per deployment; 0 disables throttling
    gemini_batch_size: int = 20  # eval only: emails per request when Gemini goes first
    gemini_rpm: int = 15  # max requests per minute PER MODEL; 0 disables throttling

    database_url: str = "sqlite+pysqlite:///./switchboard.db"
    redis_url: str = "redis://localhost:6379/0"

    crm_mode: str = "mock"  # hubspot | mock
    hubspot_token: str = ""
    hubspot_portal_id: str = ""  # only used to build deal links for Slack
    hubspot_pipeline: str = "default"
    hubspot_deal_stage: str = "appointmentscheduled"
    # "alice=123,bob=456" maps a rep to a HubSpot owner id; the default covers any other rep.
    hubspot_owner_ids: str = ""
    hubspot_default_owner_id: str = ""

    enrichment_provider: str = "mock"  # apollo | hunter | mock
    apollo_api_key: str = ""
    hunter_api_key: str = ""

    slack_webhook_url: str = ""

    log_format: str = "json"  # json | text
    log_level: str = "INFO"

    confidence_threshold: float = 0.7
    routing_config_path: str = "config/routing.yaml"


    @property
    def gemini_model_list(self) -> list[str]:
        raw = self.llm_models or self.gemini_models
        return [m.strip() for m in raw.split(",") if m.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
