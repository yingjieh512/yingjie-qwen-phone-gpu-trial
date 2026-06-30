from pathlib import Path

from scripts.android.find_probe_apk import find_debug_apks, main, select_best_apk


def test_select_best_apk_prefers_standard_debug_output(tmp_path: Path) -> None:
    standard = tmp_path / "android" / "probe-app" / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"
    odd = tmp_path / "android" / "probe-app" / "elsewhere" / "other-debug.apk"
    standard.parent.mkdir(parents=True)
    odd.parent.mkdir(parents=True)
    odd.write_bytes(b"not a real apk")
    standard.write_bytes(b"not a real apk")

    assert select_best_apk(tmp_path) == standard
    assert find_debug_apks(tmp_path)[0] == standard


def test_find_probe_apk_main_returns_nonzero_when_missing(tmp_path: Path, capsys) -> None:
    assert main(["--root", str(tmp_path)]) == 2
    captured = capsys.readouterr()
    assert "no debug APK found" in captured.err
