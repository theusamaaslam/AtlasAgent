from pathlib import Path


def test_windows_native_install_path_docs_match_installer() -> None:
    doc = Path("website/docs/user-guide/windows-native.md").read_text()
    install = Path("scripts/install.ps1").read_text()

    assert "%LOCALAPPDATA%\\atlas\\atlas-agent\\venv\\Scripts" in doc
    assert "Get-Command atlas        # should print C:\\Users\\<you>\\AppData\\Local\\atlas\\atlas-agent\\venv\\Scripts\\atlas.exe" in doc
    assert '$atlasBin = "$InstallDir\\venv\\Scripts"' in install
