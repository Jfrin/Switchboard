from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"
    gemini_rpm: int = 5  # max requests per minute; 0 disables throttling

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

    confidence_threshold: float = 0.7
    routing_config_path: str = "config/routing.yaml"


@lru_cache
def get_settings() -> Settings:
    return Settings()
