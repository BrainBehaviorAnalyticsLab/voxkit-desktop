import pytest

from voxkit.analyzers.default_analyzer import DefaultAnalyzer


class TestDefaultAnalyzerProperties:
    def test_name(self):
        analyzer = DefaultAnalyzer()
        assert analyzer.name == "Default"

    def test_description(self):
        analyzer = DefaultAnalyzer()
        assert "speaker" in analyzer.description.lower()


class TestDefaultAnalyzerAnalyze:
    @pytest.fixture
    def analyzer(self):
        return DefaultAnalyzer()

    @pytest.fixture
    def dataset_with_speakers(self, tmp_path):
        # Create speaker directories with audio files
        speaker1 = tmp_path / "speaker_1"
        speaker1.mkdir()
        (speaker1 / "audio1.wav").touch()
        (speaker1 / "audio2.wav").touch()
        (speaker1 / "audio3.flac").touch()

        speaker2 = tmp_path / "speaker_2"
        speaker2.mkdir()
        (speaker2 / "recording.mp3").touch()

        speaker3 = tmp_path / "speaker_3"
        speaker3.mkdir()
        (speaker3 / "sample1.ogg").touch()
        (speaker3 / "sample2.m4a").touch()
        (speaker3 / "sample3.wav").touch()
        (speaker3 / "sample4.wav").touch()

        return tmp_path

    def test_analyze_returns_list(self, analyzer, dataset_with_speakers):
        result = analyzer.analyze(str(dataset_with_speakers))
        assert isinstance(result, list)

    def test_analyze_correct_speaker_count(self, analyzer, dataset_with_speakers):
        result = analyzer.analyze(str(dataset_with_speakers))
        assert len(result) == 3

    def test_analyze_result_structure(self, analyzer, dataset_with_speakers):
        result = analyzer.analyze(str(dataset_with_speakers))

        for row in result:
            assert "speaker_id" in row
            assert "audio_file_count" in row

    def test_analyze_audio_counts(self, analyzer, dataset_with_speakers):
        result = analyzer.analyze(str(dataset_with_speakers))

        counts_by_speaker = {r["speaker_id"]: r["audio_file_count"] for r in result}

        assert counts_by_speaker["speaker_1"] == 3
        assert counts_by_speaker["speaker_2"] == 1
        assert counts_by_speaker["speaker_3"] == 4

    def test_analyze_empty_directory(self, analyzer, tmp_path):
        result = analyzer.analyze(str(tmp_path))
        assert result == []

    def test_analyze_empty_speaker_directories(self, analyzer, tmp_path):
        (tmp_path / "speaker_empty").mkdir()

        result = analyzer.analyze(str(tmp_path))

        assert len(result) == 1
        assert result[0]["speaker_id"] == "speaker_empty"
        assert result[0]["audio_file_count"] == 0

    def test_analyze_ignores_non_audio_files(self, analyzer, tmp_path):
        speaker = tmp_path / "speaker_1"
        speaker.mkdir()
        (speaker / "audio.wav").touch()
        (speaker / "transcript.txt").touch()
        (speaker / "notes.json").touch()
        (speaker / "config.yaml").touch()

        result = analyzer.analyze(str(tmp_path))

        assert len(result) == 1
        assert result[0]["audio_file_count"] == 1

    def test_analyze_ignores_files_at_root(self, analyzer, tmp_path):
        # Files at root level should not create entries
        (tmp_path / "root_audio.wav").touch()
        (tmp_path / "readme.txt").touch()

        speaker = tmp_path / "speaker_1"
        speaker.mkdir()
        (speaker / "audio.wav").touch()

        result = analyzer.analyze(str(tmp_path))

        # Should only have the speaker directory
        assert len(result) == 1
        assert result[0]["speaker_id"] == "speaker_1"

    def test_analyze_case_insensitive_extensions(self, analyzer, tmp_path):
        speaker = tmp_path / "speaker_1"
        speaker.mkdir()
        (speaker / "audio.WAV").touch()
        (speaker / "audio2.Wav").touch()
        (speaker / "audio3.FLAC").touch()

        result = analyzer.analyze(str(tmp_path))

        assert result[0]["audio_file_count"] == 3

    def test_analyze_nonexistent_path(self, analyzer, tmp_path):
        nonexistent = tmp_path / "does_not_exist"

        result = analyzer.analyze(str(nonexistent))

        assert result == []

    def test_analyze_all_supported_formats(self, analyzer, tmp_path):
        speaker = tmp_path / "speaker_1"
        speaker.mkdir()

        # All supported formats
        (speaker / "file.wav").touch()
        (speaker / "file.flac").touch()
        (speaker / "file.mp3").touch()
        (speaker / "file.ogg").touch()
        (speaker / "file.m4a").touch()

        result = analyzer.analyze(str(tmp_path))

        assert result[0]["audio_file_count"] == 5


class TestDefaultAnalyzerVisualize:
    @pytest.fixture
    def analyzer(self):
        return DefaultAnalyzer()

    def test_visualize_empty_data(self, qtbot, analyzer):
        widget = analyzer.visualize([])
        qtbot.addWidget(widget)
        assert widget is not None

    def test_visualize_with_data(self, qtbot, analyzer):
        data = [
            {"speaker_id": "speaker_1", "audio_file_count": 10},
            {"speaker_id": "speaker_2", "audio_file_count": 5},
        ]
        widget = analyzer.visualize(data)
        qtbot.addWidget(widget)
        assert widget is not None

    def test_visualize_single_speaker(self, qtbot, analyzer):
        data = [{"speaker_id": "only_speaker", "audio_file_count": 100}]
        widget = analyzer.visualize(data)
        qtbot.addWidget(widget)
        assert widget is not None

    def test_visualize_with_zero_counts(self, qtbot, analyzer):
        data = [
            {"speaker_id": "speaker_1", "audio_file_count": 0},
            {"speaker_id": "speaker_2", "audio_file_count": 0},
        ]
        widget = analyzer.visualize(data)
        qtbot.addWidget(widget)
        assert widget is not None

    def test_visualize_handles_missing_keys(self, qtbot, analyzer):
        data = [
            {"speaker_id": "speaker_1"},  # missing audio_file_count
            {"audio_file_count": 5},  # missing speaker_id
        ]
        widget = analyzer.visualize(data)
        qtbot.addWidget(widget)
        assert widget is not None

    def test_visualize_handles_invalid_count(self, qtbot, analyzer):
        data = [
            {"speaker_id": "speaker_1", "audio_file_count": "not_a_number"},
        ]
        widget = analyzer.visualize(data)
        qtbot.addWidget(widget)
        assert widget is not None

    def test_visualize_many_speakers(self, qtbot, analyzer):
        data = [{"speaker_id": f"speaker_{i}", "audio_file_count": i * 10} for i in range(20)]
        widget = analyzer.visualize(data)
        qtbot.addWidget(widget)
        assert widget is not None

    def test_visualize_widget_has_scroll_area(self, qtbot, analyzer):
        from PyQt6.QtWidgets import QScrollArea

        data = [{"speaker_id": "speaker_1", "audio_file_count": 10}]
        widget = analyzer.visualize(data)
        qtbot.addWidget(widget)

        # Find scroll area in children
        scroll_areas = widget.findChildren(QScrollArea)
        assert len(scroll_areas) > 0
