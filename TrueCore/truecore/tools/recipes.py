"""Chain recipes for situational tool selection."""

from __future__ import annotations

from typing import Any


class ChainRecipeError(ValueError):
    """Raised when a chain recipe violates non-executable recipe rules."""


def build_default_chain_recipes() -> dict[str, dict[str, Any]]:
    recipes = {
        "security.incident.leadup.basic": {
            "recipe_id": "security.incident.leadup.basic",
            "description": "Read temporal context, trace relationships, and request a Central Writer report.",
            "capability_sequence": [
                "temporal.read",
                "forge.relationships.trace",
                "central_writer.report_request",
            ],
            "prompt_profile": "truecore.incident_interpreter",
            "runner_executable": False,
        }
    }
    for recipe in recipes.values():
        validate_chain_recipe(recipe)
    return recipes


def validate_chain_recipe(recipe: dict[str, Any]) -> dict[str, Any]:
    for forbidden in ("command", "entrypoint", "adapter_action"):
        if forbidden in recipe:
            raise ChainRecipeError(f"chain recipe cannot contain {forbidden}")
    if not isinstance(recipe.get("recipe_id"), str) or not recipe["recipe_id"].strip():
        raise ChainRecipeError("recipe_id must be a non-empty string")
    if not isinstance(recipe.get("description"), str) or not recipe["description"].strip():
        raise ChainRecipeError("description must be a non-empty string")
    sequence = recipe.get("capability_sequence")
    if not isinstance(sequence, list) or not sequence:
        raise ChainRecipeError("capability_sequence must be a non-empty list")
    if not all(isinstance(item, str) and item.strip() for item in sequence):
        raise ChainRecipeError("capability_sequence must contain only non-empty strings")
    if not isinstance(recipe.get("prompt_profile"), str):
        raise ChainRecipeError("prompt_profile must be a string")
    if recipe.get("runner_executable") is not False:
        raise ChainRecipeError("chain recipe is not executable")
    return dict(recipe)
