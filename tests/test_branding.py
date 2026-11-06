"""Branding changes must retain settings and legacy entry points."""
import gc
import json
import tkinter as tk
from unittest.mock import patch
from pathlib import Path
import re

import pytest

from click.testing import CliRunner
from music_dl import desktop
from music_dl.__main__ import main
from music_dl.__version__ import __title__


def test_brand_and_cli():
    assert __title__ == "dv365-music-downloader"
    result = CliRunner().invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "dv365-music-downloader" in result.output
    assert "dv365-music-downloader -k" in CliRunner().invoke(main, ["--help"]).output


@pytest.mark.parametrize("name", ["README.md", "README.en.md"])
def test_readme_has_no_promotional_images_or_repository_links(name):
    root = Path(__file__).resolve().parents[1]
    content = (root / name).read_text(encoding="utf-8")
    assert not re.search(r"<img\b|!\[", content, re.IGNORECASE)
    assert not re.search(r"https?://[^\s)]*(?:github|shields|codecov|travis)", content, re.IGNORECASE)
    assert (root / "LICENSE").is_file()


def test_settings_migration_and_new_settings_priority(tmp_path):
    new = tmp_path / "dv365-music-downloader"
    legacy = tmp_path / "MusicDLPreview"
    legacy.mkdir()
    old_settings = {"directory": str(tmp_path / "existing-music"), "limit": "20", "lyrics": True}
    legacy_file = legacy / "settings.json"
    legacy_file.write_text(json.dumps(old_settings), encoding="utf-8")
    root = tk.Tk()
    root.withdraw()
    app = None
    try:
        with patch.object(desktop, "DATA_DIR", new), patch.object(desktop, "LEGACY_DATA_DIR", legacy):
            app = desktop.MusicDesktop(root)
            assert root.title() == "dv365-music-downloader · 技术预发布"
            assert app._window_icon.width() == app._window_icon.height() == 1
            assert app._window_icon.transparency_get(0, 0)
            assert app.directory.get() == old_settings["directory"]
            assert app.limit.get() == "20"
            assert app.lyrics.get()
            app.limit.set("50")
            app.save_settings()
            app.limit.set("5")
            app.load_settings()
            assert app.limit.get() == "50"
            assert json.loads(legacy_file.read_text(encoding="utf-8")) == old_settings
    finally:
        root.destroy()
        root.report_callback_exception = lambda *args: None
        del app
        gc.collect()
