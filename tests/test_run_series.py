import subprocess
from types import SimpleNamespace
from unittest import mock

import pytest

import run_series


def make_files(directory, names):
    directory.mkdir(parents=True, exist_ok=True)
    paths = {}
    for name in names:
        path = directory / name
        path.write_bytes(b"")
        paths[name] = path
    return paths


# --- natural_key -----------------------------------------------------------


def test_natural_key_orders_episode_numbers_numerically():
    assert run_series.natural_key("episode2") < run_series.natural_key("episode10")

    names = ["episode10.mkv", "episode2.mkv", "episode1.mkv"]
    assert sorted(names, key=run_series.natural_key) == [
        "episode1.mkv",
        "episode2.mkv",
        "episode10.mkv",
    ]


# --- list_candidates -------------------------------------------------------


def test_list_candidates_returns_only_files_sorted_naturally(tmp_path):
    season = tmp_path / "Season 1"
    paths = make_files(season, ["episode10.mkv", "episode2.mkv", "episode1.mkv"])
    (season / ".hidden").write_bytes(b"")
    (season / "subdir").mkdir()
    (season / "subdir" / "nested.mkv").write_bytes(b"")

    assert run_series.list_candidates(str(season)) == [
        "episode1.mkv",
        "episode2.mkv",
        "episode10.mkv",
    ]
    assert set(run_series.list_candidates(str(season))) <= set(paths)


def test_list_candidates_returns_empty_for_missing_directory(tmp_path):
    assert run_series.list_candidates(str(tmp_path / "missing")) == []


# --- probe_duration --------------------------------------------------------


def test_probe_duration_parses_float():
    with mock.patch(
        "run_series.subprocess.check_output", return_value="123.5\n"
    ) as check_output:
        assert run_series.probe_duration("episode1.mkv") == 123.5

    assert check_output.call_count == 1
    args, kwargs = check_output.call_args
    assert args[0][0] == "ffprobe"
    assert kwargs["text"] is True


@pytest.mark.parametrize("output", ["not-a-number\n", "", "nan\n", "0\n", "-5\n"])
def test_probe_duration_returns_none_for_unusable_output(output):
    with mock.patch("run_series.subprocess.check_output", return_value=output):
        assert run_series.probe_duration("episode1.mkv") is None


@pytest.mark.parametrize(
    "error",
    [
        subprocess.CalledProcessError(1, ["ffprobe"]),
        subprocess.TimeoutExpired(["ffprobe"], 30),
        FileNotFoundError("ffprobe"),
        OSError("boom"),
    ],
)
def test_probe_duration_returns_none_on_subprocess_errors(error):
    with mock.patch("run_series.subprocess.check_output", side_effect=error):
        assert run_series.probe_duration("episode1.mkv") is None


# --- show_season -----------------------------------------------------------


def test_show_season_writes_history_in_expected_format(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    paths = make_files(tmp_path / "Season 1", ["episode1.mkv"])
    monkeypatch.setattr(run_series, "probe_duration", lambda path: 111.5)

    with mock.patch(
        "run_series.subprocess.run",
        return_value=SimpleNamespace(returncode=0),
    ) as run:
        result = run_series.show_season(str(paths["episode1.mkv"]))

    assert result is True
    assert run.call_count == 1
    history = (tmp_path / "history").read_text(encoding="utf-8")
    assert history.endswith("\n")
    path_part, timestamp_part, duration_part = history.strip().split(":")
    assert path_part == str(paths["episode1.mkv"])
    assert float(timestamp_part) > 0
    assert float(duration_part) == 111.5


def test_show_season_skips_file_without_duration(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    paths = make_files(
        tmp_path / "Season 1",
        ["episode1.mkv", "episode2.mkv", "episode10.mkv"],
    )

    def fake_probe(path):
        return None if path.endswith("episode2.mkv") else 50.0

    monkeypatch.setattr(run_series, "probe_duration", fake_probe)

    with mock.patch(
        "run_series.subprocess.run",
        return_value=SimpleNamespace(returncode=0),
    ) as run:
        result = run_series.show_season(str(paths["episode1.mkv"]))

    assert result is True
    played = [call.args[0][-1] for call in run.call_args_list]
    assert played == [
        str(paths["episode1.mkv"]),
        str(paths["episode10.mkv"]),
    ]
    history = (tmp_path / "history").read_text(encoding="utf-8").strip()
    assert history.split(":")[0] == str(paths["episode10.mkv"])
    assert "skipping unreadable file" in capsys.readouterr().out


def test_show_season_continues_after_ffmpeg_error(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    paths = make_files(tmp_path / "Season 1", ["episode1.mkv", "episode2.mkv"])
    monkeypatch.setattr(run_series, "probe_duration", lambda path: 30.0)

    results = [
        SimpleNamespace(returncode=1),
        SimpleNamespace(returncode=0),
    ]
    with mock.patch("run_series.subprocess.run", side_effect=results) as run:
        result = run_series.show_season(str(paths["episode1.mkv"]))

    assert result is True
    assert run.call_count == 2
    history = (tmp_path / "history").read_text(encoding="utf-8").strip()
    assert history.split(":")[0] == str(paths["episode2.mkv"])
    assert "playback failed" in capsys.readouterr().out


def test_show_season_returns_false_for_empty_directory(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "Season 1").mkdir()
    monkeypatch.setattr(run_series, "probe_duration", lambda path: 30.0)

    with mock.patch("run_series.subprocess.run") as run:
        result = run_series.show_season(str(tmp_path / "Season 1" / "episode1.mkv"))

    assert result is False
    run.assert_not_called()
    assert not (tmp_path / "history").exists()
    assert "no files to play" in capsys.readouterr().out


def test_show_season_returns_false_when_all_files_are_skipped(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    paths = make_files(tmp_path / "Season 1", ["episode1.mkv", "episode2.mkv"])
    monkeypatch.setattr(run_series, "probe_duration", lambda path: None)

    with mock.patch("run_series.subprocess.run") as run:
        result = run_series.show_season(str(paths["episode1.mkv"]))

    assert result is False
    run.assert_not_called()
    assert not (tmp_path / "history").exists()
    assert "skipping unreadable file" in capsys.readouterr().out


def test_show_season_returns_false_when_all_ffmpeg_runs_fail(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    paths = make_files(tmp_path / "Season 1", ["episode1.mkv", "episode2.mkv"])
    monkeypatch.setattr(run_series, "probe_duration", lambda path: 30.0)

    with mock.patch(
        "run_series.subprocess.run",
        return_value=SimpleNamespace(returncode=1, stderr=""),
    ) as run:
        result = run_series.show_season(str(paths["episode1.mkv"]))

    assert result is False
    assert run.call_count == 2
    assert capsys.readouterr().out.count("playback failed") == 2


def test_show_season_prints_ffmpeg_stderr_tail_on_failure(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    paths = make_files(tmp_path / "Season 1", ["episode1.mkv"])
    monkeypatch.setattr(run_series, "probe_duration", lambda path: 30.0)

    failed = SimpleNamespace(returncode=1, stderr="line1\nline2\n")
    with mock.patch("run_series.subprocess.run", return_value=failed):
        result = run_series.show_season(str(paths["episode1.mkv"]))

    assert result is False
    out = capsys.readouterr().out
    assert "playback failed" in out
    assert "line1" in out
    assert "line2" in out


def test_show_season_truncates_ffmpeg_stderr_to_last_five_lines(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    paths = make_files(tmp_path / "Season 1", ["episode1.mkv"])
    monkeypatch.setattr(run_series, "probe_duration", lambda path: 30.0)

    stderr = "\n".join(f"err{i}" for i in range(1, 8)) + "\n"
    failed = SimpleNamespace(returncode=1, stderr=stderr)
    with mock.patch("run_series.subprocess.run", return_value=failed):
        run_series.show_season(str(paths["episode1.mkv"]))

    out = capsys.readouterr().out
    assert "err3" in out
    assert "err7" in out
    assert "err1" not in out
    assert "err2" not in out


# --- change_season ---------------------------------------------------------


@pytest.fixture
def show_tree(tmp_path):
    show = tmp_path / "Show"
    make_files(show / "Season 1", ["episode1.mkv", "episode2.mkv"])
    make_files(show / "Season 2", ["bad.mkv", "episode2.mkv"])
    make_files(show / "Season 3", ["episode1.mkv"])
    return show


def test_change_season_returns_first_playable_episode_of_next_season(
    show_tree, monkeypatch
):
    monkeypatch.setattr(
        run_series,
        "probe_duration",
        lambda path: None if path.endswith("bad.mkv") else 10.0,
    )

    result = run_series.change_season(str(show_tree / "Season 1" / "episode1.mkv"))

    assert result == str(show_tree / "Season 2" / "episode2.mkv")


def test_change_season_wraps_from_last_season_to_first(show_tree, monkeypatch):
    monkeypatch.setattr(run_series, "probe_duration", lambda path: 10.0)

    result = run_series.change_season(str(show_tree / "Season 3" / "episode1.mkv"))

    assert result == str(show_tree / "Season 1" / "episode1.mkv")


def test_change_season_returns_none_when_nothing_is_playable(show_tree, monkeypatch):
    monkeypatch.setattr(run_series, "probe_duration", lambda path: None)

    result = run_series.change_season(str(show_tree / "Season 1" / "episode1.mkv"))

    assert result is None


def test_change_season_sorts_season_10_after_season_2(tmp_path, monkeypatch):
    show = tmp_path / "Show"
    make_files(show / "Season 2", ["episode1.mkv"])
    make_files(show / "Season 10", ["episode1.mkv"])
    monkeypatch.setattr(run_series, "probe_duration", lambda path: 10.0)

    # "Season 10" must follow "Season 2" (plain string sort would put it first).
    assert run_series.change_season(str(show / "Season 2" / "episode1.mkv")) == str(
        show / "Season 10" / "episode1.mkv"
    )

    # And wrapping back from the last season reaches "Season 2".
    assert run_series.change_season(str(show / "Season 10" / "episode1.mkv")) == str(
        show / "Season 2" / "episode1.mkv"
    )
