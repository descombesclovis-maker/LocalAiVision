"""Test Studio's local connector storage without network calls or real secrets."""
from __future__ import annotations
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from local_app import studio_credentials


class ConnectionsTests(unittest.TestCase):
    def test_dpapi_envelope_does_not_store_plaintext_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "connections" / "google-api.dpapi"
            secret = "private-test-key-abcdefghijkl"
            with (patch.object(studio_credentials, "_location", return_value=destination),
                  patch.object(studio_credentials, "_protect", side_effect=lambda b, decrypt=False: b[::-1]),
                  patch.dict(studio_credentials.os.environ, {
                      "LOCALAIWEB_GOOGLE_PLACES_API_KEY": "",
                      "LOCALAIWEB_GOOGLE_MAPS_BROWSER_KEY": ""
                  })):
                result = studio_credentials.modify("places_server", "save", secret)
                self.assertTrue(result["places_server"]["configured"])
                self.assertEqual(studio_credentials.read_key("places_server"), secret)
                on_disk = destination.read_text(encoding="utf-8")
                self.assertNotIn(secret, on_disk)
                self.assertNotIn("private-test-key", on_disk)
                self.assertEqual(json.loads(on_disk)["format"], "win-dpapi-1")
                result = studio_credentials.modify("places_server", "clear")
                self.assertFalse(result["places_server"]["configured"])
                self.assertEqual(studio_credentials.read_key("places_server"), "")

    def test_overrides_not_serialized(self):
        with tempfile.TemporaryDirectory() as directory:
            with (patch.object(studio_credentials, "_location", return_value=Path(directory) / "secret.dpapi"),
                  patch.dict(studio_credentials.os.environ, {
                      "LOCALAIWEB_GOOGLE_PLACES_API_KEY": "administrator-configured-key",
                      "LOCALAIWEB_GOOGLE_MAPS_BROWSER_KEY": ""
                  })):
                self.assertEqual(studio_credentials.read_key("places_server"), "administrator-configured-key")
                result = studio_credentials.status()
                self.assertTrue(result["places_server"]["configured"])
                self.assertTrue(result["places_server"]["environment_override"])
                self.assertNotIn("administrator-configured-key", json.dumps(result))

    def test_reject_invalid_provider_and_secret(self):
        with self.assertRaises(ValueError):
            studio_credentials.modify("openai", "save", "abcdefghijklmnop")
        with self.assertRaises(ValueError):
            studio_credentials.modify("maps_browser", "save", "short")
        with self.assertRaises(ValueError):
            studio_credentials.modify("maps_browser", "save", "A" * 300)


if __name__ == "__main__":
    unittest.main()
