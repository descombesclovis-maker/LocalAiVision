import os
import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from local_app.business_time import business_date


def stamp(value):
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc).timestamp()


class BusinessTimeTests(unittest.TestCase):
    def test_business_midnight_is_not_utc_midnight(self):
        t = stamp('2026-06-30T22:30:00')
        self.assertEqual(str(business_date(t, 'Europe/Paris')), '2026-07-01')
        self.assertEqual(str(business_date(t, 'America/Los_Angeles')), '2026-06-30')

    def test_dst_spring_and_autumn_keep_the_business_day(self):
        for value in ['2026-03-29T00:30:00', '2026-03-29T01:30:00',
                      '2026-10-25T00:30:00', '2026-10-25T01:30:00']:
            self.assertEqual(str(business_date(stamp(value), 'Europe/Paris')), value[:10])

    def test_configuration_and_invalid_zone(self):
        with patch.dict(os.environ, {'LOCALAI_BUSINESS_TIMEZONE': 'Europe/Paris'}):
            self.assertEqual(str(business_date(stamp('2026-01-01T23:30:00'))), '2026-01-02')
            # Persisted quote zone wins over a later configuration change.
            self.assertEqual(str(business_date(stamp('2026-01-01T23:30:00'), 'UTC')), '2026-01-01')
        with self.assertRaises(ValueError):
            business_date(0, 'Not/AZone')

    def test_bundled_data_works_when_windows_has_no_iana_database(self):
        from zoneinfo import ZoneInfo,ZoneInfoNotFoundError
        from local_app import business_time
        class NoSystemDatabase:
            def __new__(cls,name):raise ZoneInfoNotFoundError(name)
            from_file=staticmethod(ZoneInfo.from_file)
        business_time.business_zone.cache_clear()
        self.addCleanup(business_time.business_zone.cache_clear)
        with patch.object(business_time,'ZoneInfo',NoSystemDatabase):
            self.assertEqual(str(business_time.business_date(stamp('2026-06-30T22:30:00'),'Europe/Paris')),'2026-07-01')
            self.assertEqual(str(business_time.business_date(stamp('2026-01-01T00:30:00'),'America/Los_Angeles')),'2025-12-31')
            self.assertEqual(str(business_time.business_date(0,'UTC')),'1970-01-01')
            with self.assertRaises(ValueError):business_time.business_date(0,'Unavailable/Zone')
