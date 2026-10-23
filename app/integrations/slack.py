import logging

import httpx

from app.config import get_settings

log = logging.getLogger(__name__)


def notify(text: str) -> None:
    """Post to Slack; log instead when no webhook is configured."""
    url = get_settings().slack_webhook_url
    if not url:
        log.info("slack (dry run): %s", text)
        return
    httpx.post(url, json={"text": text}, timeout=10).raise_for_status()
