"""
Unit Tests for Configuration and Secret Key Security.
Tests strict validation of APP_SECRET_KEY, rejection of missing or static default keys,
and acceptance of high-entropy cryptographic secrets.
"""

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config


class TestConfigSecurity(unittest.TestCase):

    def test_tc22_missing_secret_key_rejected(self):
        """TC-CFG-01: Missing or empty APP_SECRET_KEY must be rejected."""
        # Empty string
        with self.assertRaises(ValueError) as ctx:
            config.validate_config("", strict=True)
        self.assertIn("belum disetel", str(ctx.exception).lower())

        # None value
        with self.assertRaises(ValueError) as ctx:
            config.validate_config(None, strict=True)
        # If config.APP_SECRET_KEY is currently set in .env, passing None checks config.APP_SECRET_KEY.
        # But passing an empty string or whitespace tests empty:
        with self.assertRaises(ValueError):
            config.validate_config("   ", strict=True)

    def test_tc23_static_default_secret_key_rejected(self):
        """TC-CFG-02: Known static default keys (e.g. donasikita-secret-key-uts-2026-secure) must be rejected."""
        static_keys = [
            "donasikita-secret-key-uts-2026-secure",
            "secret",
            "changeme",
            "default",
            "password",
            "12345678"
        ]
        for bad_key in static_keys:
            with self.subTest(key=bad_key):
                with self.assertRaises(ValueError) as ctx:
                    config.validate_config(bad_key, strict=True)
                self.assertIn("tidak aman", str(ctx.exception).lower())

    def test_tc24_short_secret_key_rejected(self):
        """TC-CFG-03: APP_SECRET_KEY shorter than 16 characters must be rejected."""
        short_keys = ["a", "1234567", "short_secret", "abcdefghijklmno"]  # 15 chars
        for short_key in short_keys:
            with self.subTest(key=short_key):
                with self.assertRaises(ValueError) as ctx:
                    config.validate_config(short_key, strict=True)
                self.assertIn("terlalu pendek", str(ctx.exception).lower())

    def test_tc25_valid_secret_key_accepted(self):
        """TC-CFG-04: Strong, high-entropy secret key must pass validation."""
        import secrets
        sample_key = secrets.token_hex(32)
        is_valid, msg = config.validate_config(sample_key, strict=False)
        self.assertTrue(is_valid)
        self.assertIn("valid", msg.lower())

    def test_tc26_current_env_config_valid(self):
        """TC-CFG-05: Currently active local .env configuration must pass all security checks."""
        self.assertIsNotNone(config.APP_SECRET_KEY, "APP_SECRET_KEY must be loaded from .env")
        self.assertNotIn(config.APP_SECRET_KEY, config.INSECURE_SECRET_KEYS, "APP_SECRET_KEY must not use static default")
        self.assertGreaterEqual(len(config.APP_SECRET_KEY), 16, "APP_SECRET_KEY must be at least 16 characters")
        
        # Validating current configuration must succeed without raising
        valid, _ = config.validate_config(strict=True)
        self.assertTrue(valid)


if __name__ == "__main__":
    unittest.main()
