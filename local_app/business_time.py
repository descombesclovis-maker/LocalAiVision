"""Business calendar dates, separate from UTC epoch event timestamps.

LOCALAI_BUSINESS_TIMEZONE accepts an IANA zone (e.g. Europe/Paris). Without a
setting, the OS local timezone is used, including its DST rules at the event.
New quotes persist their zone policy; existing quotes retain the local policy.
An unavailable explicit zone fails clearly, rather than silently using UTC.
"""
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def timezone_name():
    return os.getenv('LOCALAI_BUSINESS_TIMEZONE', '').strip() or 'local'


def business_date(timestamp=None, zone=None):
    name = timezone_name() if zone is None else zone
    instant = datetime.now(timezone.utc) if timestamp is None else datetime.fromtimestamp(float(timestamp), timezone.utc)
    if name == 'local':
        return instant.astimezone().date()
    try:
        return instant.astimezone(ZoneInfo(name)).date()
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError('Fuseau métier indisponible : ' + str(name) + '. Configurer une zone IANA disponible ou utiliser le fuseau local du système.') from exc
