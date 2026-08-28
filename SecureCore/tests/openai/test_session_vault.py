import json
import unittest

from securecore.openai_session import OpenAIKeyVault


class OpenAISessionVaultTests(unittest.TestCase):
    def test_login_keeps_key_in_memory_but_never_returns_secret(self):
        vault = OpenAIKeyVault(default_model="gpt-test")

        public = vault.login(user_id="USER1", api_key="sk-test-secret", model="")

        self.assertTrue(public["active"])
        self.assertEqual(public["model"], "gpt-test")
        self.assertEqual(vault.get_api_key("USER1"), "sk-test-secret")
        self.assertNotIn("api_key", public)
        self.assertNotIn("sk-test-secret", json.dumps(public))
        self.assertNotIn("sk-test-secret", json.dumps(vault.status("USER1")))

    def test_logout_clears_session_key(self):
        vault = OpenAIKeyVault(default_model="gpt-test")
        vault.login(user_id="USER1", api_key="sk-test-secret", model="gpt-operator")

        status = vault.logout("USER1")

        self.assertFalse(status["active"])
        self.assertIsNone(vault.get_api_key("USER1"))

    def test_missing_api_key_fails_closed(self):
        vault = OpenAIKeyVault(default_model="gpt-test")

        with self.assertRaises(ValueError):
            vault.login(user_id="USER1", api_key="   ", model="")


if __name__ == "__main__":
    unittest.main()
