import pytest

from voxkit.engines import AlignmentEngine, engines


class TestEngineManager:
    def test_list_engines_returns_list(self):
        result = engines.list_engines()
        assert isinstance(result, list)

    def test_list_engines_contains_expected(self):
        result = engines.list_engines()
        assert "W2TGENGINE" in result
        assert "MFAENGINE" in result
        assert "FASTERWHISPERENGINE" in result

    def test_get_engine_success(self):
        engine = engines.get_engine("W2TGENGINE")
        assert isinstance(engine, AlignmentEngine)
        assert engine.id == "W2TGENGINE"

    def test_get_engine_mfa(self):
        engine = engines.get_engine("MFAENGINE")
        assert isinstance(engine, AlignmentEngine)
        assert engine.id == "MFAENGINE"

    def test_get_engine_faster_whisper(self):
        engine = engines.get_engine("FASTERWHISPERENGINE")
        assert isinstance(engine, AlignmentEngine)
        assert engine.id == "FASTERWHISPERENGINE"

    def test_get_engine_not_found(self):
        with pytest.raises(ValueError) as exc_info:
            engines.get_engine("NONEXISTENT")
        assert "No engine with id" in str(exc_info.value)

    def test_get_tool_providers_align(self):
        # ToolType is Literal["train", "align", "transcribe"]
        providers = engines.get_tool_providers("align")
        assert isinstance(providers, dict)
        # At least some engines should provide alignment
        assert len(providers) > 0

    def test_get_tool_providers_transcribe(self):
        providers = engines.get_tool_providers("transcribe")
        assert isinstance(providers, dict)

    def test_get_tool_providers_train(self):
        providers = engines.get_tool_providers("train")
        assert isinstance(providers, dict)

    def test_get_tool_providers_returns_engines(self):
        providers = engines.get_tool_providers("align")
        for engine_id, engine in providers.items():
            assert isinstance(engine, AlignmentEngine)
            assert engine.id == engine_id


class TestEngineManagerCustom:
    def test_empty_manager(self):
        from voxkit.engines import EngineManager

        manager = EngineManager({})
        assert manager.list_engines() == []

        with pytest.raises(ValueError):
            manager.get_engine("anything")

    def test_get_tool_providers_empty(self):
        from voxkit.engines import EngineManager

        manager = EngineManager({})
        providers = manager.get_tool_providers("align")
        assert providers == {}
