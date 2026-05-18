from pathlib import Path
import zipfile

from scripts.assert_fresh_install import _latest_wheel


def test_fresh_install_script_is_packaged_in_sdist_manifest():
    manifest = Path("MANIFEST.in").read_text(encoding="utf-8")
    assert "recursive-include scripts *.py" in manifest
    assert "include tests/test_fresh_install.py" in manifest


def test_latest_wheel_selects_newest_mbs_wheel(tmp_path):
    old = tmp_path / "mbs-0.1.0-py3-none-any.whl"
    new = tmp_path / "mbs-0.1.1-py3-none-any.whl"
    other = tmp_path / "other-1.0.0-py3-none-any.whl"
    for path in [old, new, other]:
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("dummy.txt", "ok")
    old.touch()
    new.touch()

    assert _latest_wheel(tmp_path) == new
