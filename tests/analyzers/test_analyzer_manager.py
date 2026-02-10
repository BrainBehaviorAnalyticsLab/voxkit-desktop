import pytest

from voxkit.analyzers import ManageAnalyzers
from voxkit.analyzers.base import DatasetAnalyzer


class MockAnalyzer(DatasetAnalyzer):
    @property
    def name(self):
        return "Mock"

    @property
    def description(self):
        return "A mock analyzer for testing"

    def analyze(self, dataset_path):
        return [{"test": "data"}]


class TestAnalyzerManager:
    def test_list_analyzers_returns_list(self):
        result = ManageAnalyzers.list_analyzers()
        assert isinstance(result, list)

    def test_list_analyzers_contains_default(self):
        result = ManageAnalyzers.list_analyzers()
        assert "Default" in result

    def test_get_analyzers_returns_dict(self):
        result = ManageAnalyzers.get_analyzers()
        assert isinstance(result, dict)

    def test_get_analyzers_contains_default(self):
        result = ManageAnalyzers.get_analyzers()
        assert "Default" in result
        assert isinstance(result["Default"], DatasetAnalyzer)

    def test_get_analyzer_success(self):
        analyzer = ManageAnalyzers.get_analyzer("Default")
        assert isinstance(analyzer, DatasetAnalyzer)
        assert analyzer.name == "Default"

    def test_get_analyzer_not_found(self):
        with pytest.raises(ValueError) as exc_info:
            ManageAnalyzers.get_analyzer("NonexistentAnalyzer")

        assert "No analyzer with id" in str(exc_info.value)


class TestAnalyzerManagerWithCustomAnalyzers:
    def test_custom_analyzer_registration(self):
        from voxkit.analyzers import AnalyzerManager

        mock = MockAnalyzer()
        manager = AnalyzerManager({mock.name: mock})

        assert "Mock" in manager.list_analyzers()
        assert manager.get_analyzer("Mock") is mock

    def test_multiple_analyzers(self):
        from voxkit.analyzers import AnalyzerManager
        from voxkit.analyzers.default_analyzer import DefaultAnalyzer

        default = DefaultAnalyzer()
        mock = MockAnalyzer()

        manager = AnalyzerManager(
            {
                default.name: default,
                mock.name: mock,
            }
        )

        analyzers = manager.list_analyzers()
        assert len(analyzers) == 2
        assert "Default" in analyzers
        assert "Mock" in analyzers

    def test_empty_manager(self):
        from voxkit.analyzers import AnalyzerManager

        manager = AnalyzerManager({})

        assert manager.list_analyzers() == []
        assert manager.get_analyzers() == {}

        with pytest.raises(ValueError):
            manager.get_analyzer("anything")
