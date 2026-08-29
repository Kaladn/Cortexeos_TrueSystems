import unittest

from truecore.tools.recipes import ChainRecipeError, build_default_chain_recipes, validate_chain_recipe


class ChainRecipeTests(unittest.TestCase):
    def test_default_incident_recipe_lists_capabilities_not_commands(self):
        recipes = build_default_chain_recipes()
        recipe = recipes["security.incident.leadup.basic"]

        validated = validate_chain_recipe(recipe)

        self.assertEqual(validated["recipe_id"], "security.incident.leadup.basic")
        self.assertEqual(
            validated["capability_sequence"],
            ["temporal.read", "forge.relationships.trace", "central_writer.report_request"],
        )
        self.assertFalse(validated["runner_executable"])

    def test_recipe_with_command_is_rejected(self):
        recipe = {
            "recipe_id": "bad.command",
            "description": "Bad recipe.",
            "capability_sequence": ["temporal.read"],
            "prompt_profile": "none",
            "runner_executable": False,
            "command": ["python", "bad.py"],
        }

        with self.assertRaisesRegex(ChainRecipeError, "command"):
            validate_chain_recipe(recipe)

    def test_prompt_recipe_trying_to_act_like_agent_is_rejected(self):
        recipe = {
            "recipe_id": "bad.prompt_agent",
            "description": "Bad recipe.",
            "capability_sequence": ["temporal.read"],
            "prompt_profile": "investigate",
            "runner_executable": True,
        }

        with self.assertRaisesRegex(ChainRecipeError, "executable"):
            validate_chain_recipe(recipe)


if __name__ == "__main__":
    unittest.main()
