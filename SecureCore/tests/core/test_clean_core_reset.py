import unittest
from pathlib import Path

from securecore.app import create_app


class SecureCoreCleanCoreResetTests(unittest.TestCase):
    def test_chat_runtime_is_not_installed(self):
        app = create_app()
        rules = {rule.rule for rule in app.url_map.iter_rules()}

        self.assertFalse(any(rule.startswith("/api/chat") for rule in rules))
        self.assertFalse(hasattr(app, "chat_ledger"))
        self.assertFalse(hasattr(app, "chat_memory"))
        self.assertFalse(hasattr(app, "chat_executor"))
        self.assertFalse(hasattr(app, "canonical_chat_writer"))

        status = getattr(app, "core_runtime_status", {})
        self.assertEqual(status.get("ui_runtime"), "not_installed")
        self.assertEqual(status.get("chat_runtime"), "not_installed")
        self.assertEqual(status.get("memory_runtime"), "not_installed")
        self.assertTrue(status.get("future_port"))

    def test_embedded_model_runtime_is_not_installed(self):
        root = Path(__file__).resolve().parents[2]

        self.assertFalse((root / "securecore" / "llm").exists())
        self.assertFalse((root / "securecore" / "help" / "bot.py").exists())


if __name__ == "__main__":
    unittest.main()
