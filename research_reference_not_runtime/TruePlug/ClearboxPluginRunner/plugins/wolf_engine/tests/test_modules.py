"""
Wolf Engine — Module registry and module loading tests.
"""

from __future__ import annotations

from wolf_engine.modules.base import WolfModule
from wolf_engine.modules.registry import ModuleRegistry


class TestModuleRegistry:
    def test_list_all_modules(self):
        r = ModuleRegistry({})
        modules = r.list_modules()
        assert len(modules) == 5
        for m in modules:
            assert "key" in m
            assert "name" in m
            assert "category" in m
            assert "enabled" in m

    def test_categories_present(self):
        r = ModuleRegistry({})
        cats = {m["category"] for m in r.list_modules()}
        assert "reasoning" in cats

    def test_toggle_enable(self):
        r = ModuleRegistry({})
        result = r.toggle("rsn_window_builder", True)
        assert result["key"] == "rsn_window_builder"
        assert result["enabled"] is True

    def test_toggle_unknown(self):
        r = ModuleRegistry({})
        result = r.toggle("nonexistent", True)
        assert "error" in result

    def test_get_enabled_empty(self):
        r = ModuleRegistry({})
        assert r.get_enabled() == []

    def test_get_enabled_filtered(self):
        cfg = {"modules": {"rsn_window_builder": True}}
        r = ModuleRegistry(config=cfg)
        reasoning = r.get_enabled(category="reasoning")
        assert len(reasoning) == 1
        assert reasoning[0]["key"] == "rsn_window_builder"

    def test_get_instance_disabled(self):
        r = ModuleRegistry({})
        inst = r.get_instance("rsn_window_builder")
        assert inst is None

    def test_get_instance_enabled(self):
        cfg = {"modules": {"rsn_window_builder": True}}
        r = ModuleRegistry(config=cfg)
        inst = r.get_instance("rsn_window_builder")
        assert inst is not None
        assert isinstance(inst, WolfModule)
        assert inst.key == "rsn_window_builder"

    def test_toggle_disable_unloads(self):
        cfg = {"modules": {"rsn_window_builder": True}}
        r = ModuleRegistry(config=cfg)
        r.get_instance("rsn_window_builder")
        r.toggle("rsn_window_builder", False)
        assert r.get_instance("rsn_window_builder") is None


class TestModuleLoading:
    """Verify every module in the catalog can be loaded."""

    def test_all_modules_loadable(self):
        r = ModuleRegistry({})
        modules = r.list_modules()
        cfg = {"modules": {m["key"]: True for m in modules}}
        r2 = ModuleRegistry(config=cfg)
        for m in modules:
            inst = r2.get_instance(m["key"])
            assert inst is not None, f"Failed to load: {m['key']}"
            assert isinstance(inst, WolfModule)

    def test_all_modules_have_info(self):
        r = ModuleRegistry({})
        modules = r.list_modules()
        cfg = {"modules": {m["key"]: True for m in modules}}
        r2 = ModuleRegistry(config=cfg)
        for m in modules:
            inst = r2.get_instance(m["key"])
            info = inst.info()
            assert isinstance(info, dict)
            assert "key" in info
            assert "name" in info

    def test_reasoning_count(self):
        r = ModuleRegistry({})
        rsn = [m for m in r.list_modules() if m["category"] == "reasoning"]
        assert len(rsn) == 5


class TestReasoningModules:
    def test_window_builder_process(self):
        from wolf_engine.modules.reasoning.window_builder import WindowBuilderModule

        m = WindowBuilderModule(config={"context_window_size": 2})
        tokens = [{"norm": "a"}, {"norm": "b"}, {"norm": "c"}, {"norm": "a"}, {"norm": "b"}]
        m.process(tokens)
        counts = m.get_lexicon_counts()
        assert "a" in counts
        assert "b" in counts

    def test_ncv73_builder(self):
        from wolf_engine.modules.reasoning.ncv73_builder import Ncv73Module

        m = Ncv73Module(config={"context_window_size": 2, "max_possibilities_per_slot": 5})
        counts = {"hello": {-1: {"world": 3}, 1: {"there": 2}}}
        lexicon = m.build_lexicon(counts)
        assert "hello" in lexicon
        ncv = m.build_ncv("hello", lexicon)
        assert len(ncv) == 73
