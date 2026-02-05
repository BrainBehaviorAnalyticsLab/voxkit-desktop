from voxkit.gui.utils import validate_path


class TestValidatePath:
    def test_existing_path(self, tmp_path):
        f = tmp_path / "exists.txt"
        f.write_text("hello")
        assert validate_path(None, str(f)) is True

    def test_missing_path(self, tmp_path):
        assert validate_path(None, str(tmp_path / "nope.txt")) is False

    def test_directory_path(self, tmp_path):
        assert validate_path(None, str(tmp_path)) is True
