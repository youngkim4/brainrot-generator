"""CLI tests."""

import pytest
from click.testing import CliRunner

from brainrot.cli import _validate_video_url, main


@pytest.fixture
def runner():
    return CliRunner()


def test_validate_video_url_accepts_https():
    _validate_video_url("https://youtube.com/watch?v=abc")


def test_validate_video_url_accepts_http():
    _validate_video_url("http://example.com/video.mp4")


def test_validate_video_url_rejects_flag_injection():
    from click import BadParameter

    with pytest.raises(BadParameter, match="must not start with"):
        _validate_video_url("--output=/etc/passwd")


def test_validate_video_url_rejects_non_http():
    from click import BadParameter

    with pytest.raises(BadParameter, match="http://"):
        _validate_video_url("file:///etc/passwd")


def test_validate_video_url_rejects_empty_netloc():
    from click import BadParameter

    with pytest.raises(BadParameter, match="http://"):
        _validate_video_url("https://")


def test_main_group_help(runner):
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "Brainrot video generator" in result.output


def test_generate_command_help(runner):
    result = runner.invoke(main, ["generate", "--help"])
    assert result.exit_code == 0
    assert "--story" in result.output
    assert "--background" in result.output


def test_download_bg_command_help(runner):
    result = runner.invoke(main, ["download-bg", "--help"])
    assert result.exit_code == 0
    assert "URL" in result.output.upper() or "url" in result.output
