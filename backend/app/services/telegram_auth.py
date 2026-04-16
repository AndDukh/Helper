from __future__ import annotations

import hashlib
import hmac
import time
from urllib.parse import parse_qsl


def verify_telegram_init_data(init_data: str, bot_token: str, max_age_seconds: int | None = 86400) -> dict[str, str]:
    """
    Validate Telegram Web App initData per official algorithm.
    https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    """
    if not init_data or not bot_token:
        raise ValueError("init_data and bot_token are required")

    parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = parsed.pop("hash", None)
    if not received_hash:
        raise ValueError("hash is missing")

    data_check_parts = [f"{k}={v}" for k, v in sorted(parsed.items())]
    data_check_string = "\n".join(data_check_parts)

    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    computed = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed, received_hash):
        raise ValueError("invalid hash")

    if max_age_seconds is not None:
        auth_date = parsed.get("auth_date")
        if not auth_date or not auth_date.isdigit():
            raise ValueError("auth_date is missing")
        age = int(time.time()) - int(auth_date)
        if age < 0 or age > max_age_seconds:
            raise ValueError("init data is too old or invalid auth_date")

    return parsed
