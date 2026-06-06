import os

from bt_dualboot.infrastructure.registry.resolve import resolve_path_ci


class TestResolvePathCi:
    def test_exact_match(self, tmp_path):
        """Exact case match returns the path unchanged."""
        (tmp_path / "Windows" / "System32" / "config").mkdir(parents=True)
        (tmp_path / "Windows" / "System32" / "config" / "SYSTEM").write_text("")

        result = resolve_path_ci(str(tmp_path), "Windows/System32/config/SYSTEM")
        assert os.path.isfile(result)
        assert result.endswith("SYSTEM")

    def test_case_mismatch_in_filename(self, tmp_path):
        """Lowercase filename on disk resolves when querying uppercase."""
        (tmp_path / "Windows" / "System32" / "config").mkdir(parents=True)
        (tmp_path / "Windows" / "System32" / "config" / "system").write_text("")

        result = resolve_path_ci(str(tmp_path), "Windows/System32/config/SYSTEM")
        assert os.path.isfile(result)
        assert result.endswith("system")

    def test_case_mismatch_in_directory(self, tmp_path):
        """All-lowercase directory components resolve."""
        (tmp_path / "windows" / "system32" / "config").mkdir(parents=True)
        (tmp_path / "windows" / "system32" / "config" / "system").write_text("")

        result = resolve_path_ci(str(tmp_path), "Windows/System32/config/SYSTEM")
        assert os.path.isfile(result)
        assert "windows" in result

    def test_missing_segment_returns_original_join(self, tmp_path):
        """Non-existent segment returns os.path.join(base, relative)."""
        (tmp_path / "Windows").mkdir()

        result = resolve_path_ci(str(tmp_path), "Windows/System32/config/SYSTEM")
        assert result == os.path.join(str(tmp_path), "Windows/System32/config/SYSTEM")

    def test_nonexistent_base_returns_original_join(self, tmp_path):
        """Non-existent base returns the original join."""
        result = resolve_path_ci(str(tmp_path / "nope"), "Windows/System32/config/SYSTEM")
        assert result == os.path.join(str(tmp_path / "nope"), "Windows/System32/config/SYSTEM")

    def test_windows_registry_lowercases(self, tmp_path):
        """Full scenario: all-lowercase Windows install on case-sensitive mount."""
        (tmp_path / "windows" / "system32" / "config").mkdir(parents=True)
        (tmp_path / "windows" / "system32" / "config" / "system").write_text("")

        result = resolve_path_ci(str(tmp_path), "Windows/System32/config/SYSTEM")
        assert os.path.isfile(result)
