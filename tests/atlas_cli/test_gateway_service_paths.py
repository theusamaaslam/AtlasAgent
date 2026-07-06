from unittest.mock import patch


def test_service_path_skips_nonexistent_node_modules(tmp_path):
    """Service PATH should not include node_modules/.bin if it doesn't exist."""
    from atlas_cli.gateway import _build_service_path_dirs
    with patch("atlas_cli.gateway.get_atlas_home", return_value=tmp_path / ".atlas"):
        dirs = _build_service_path_dirs(project_root=tmp_path)
    node_modules_bin = str(tmp_path / "node_modules" / ".bin")
    assert node_modules_bin not in dirs


def test_service_path_includes_node_modules_when_present(tmp_path):
    """Service PATH should include node_modules/.bin when it exists."""
    nm_bin = tmp_path / "node_modules" / ".bin"
    nm_bin.mkdir(parents=True)
    from atlas_cli.gateway import _build_service_path_dirs
    with patch("atlas_cli.gateway.get_atlas_home", return_value=tmp_path / ".atlas"):
        dirs = _build_service_path_dirs(project_root=tmp_path)
    assert str(nm_bin) in dirs


def test_service_path_includes_atlas_home_node_modules(tmp_path):
    """Service PATH should include ~/.atlas/node_modules/.bin when it exists."""
    atlas_nm = tmp_path / ".atlas" / "node_modules" / ".bin"
    atlas_nm.mkdir(parents=True)
    from atlas_cli.gateway import _build_service_path_dirs
    with patch("atlas_cli.gateway.get_atlas_home", return_value=tmp_path / ".atlas"):
        dirs = _build_service_path_dirs(project_root=tmp_path)
    assert str(atlas_nm) in dirs
