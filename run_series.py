import math
import os
import re
import subprocess
import time

SHOW_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "show.sh")


def natural_key(name: str) -> list[int | str]:
    return [
        int(part) if part.isdigit() else part.lower()
        for part in re.split(r"(\d+)", name)
    ]


def probe_duration(path: str) -> float | None:
    try:
        output = subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                os.path.abspath(path),
            ],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=30,
        )
        duration = float(output.strip())
    except (subprocess.SubprocessError, OSError, ValueError):
        return None
    if not math.isfinite(duration) or duration <= 0:
        return None
    return duration


def list_candidates(directory: str) -> list[str]:
    try:
        entries = os.listdir(directory)
    except OSError:
        return []
    return sorted(
        (
            name
            for name in entries
            if not name.startswith(".")
            and os.path.isfile(os.path.join(directory, name))
        ),
        key=lambda name: (natural_key(name), name),
    )


def show_season(last_series: str) -> bool:
    dirname = os.path.dirname(last_series)
    basename = os.path.basename(last_series)

    candidates = list_candidates(dirname)
    if not candidates:
        print(f"no files to play in {dirname}")
        return False

    if basename in candidates:
        start = candidates.index(basename)
    else:
        print(f"{basename} not found in {dirname}, starting from {candidates[0]}")
        start = 0

    played_any = False
    for name in candidates[start:]:
        path_to_series = os.path.join(dirname, name)
        video_duration = probe_duration(path_to_series)
        if video_duration is None:
            print(f"skipping unreadable file: {path_to_series}")
            continue
        string_to_history = f"{path_to_series}:{time.time()}:{video_duration}"
        with open("history", "w") as f:
            print(string_to_history, file=f)
        print(string_to_history)
        # time.sleep(0.1)
        result = subprocess.run(
            ["bash", SHOW_SCRIPT, path_to_series],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode != 0:
            stderr = getattr(result, "stderr", "") or ""
            if not isinstance(stderr, str):
                stderr = str(stderr)
            stderr_tail = "\n".join(stderr.strip().splitlines()[-5:])
            print(
                f"playback failed for {path_to_series} (exit code {result.returncode})"
            )
            if stderr_tail:
                print(stderr_tail)
            continue
        played_any = True

    return played_any


def change_season(last_series: str) -> str | None:
    dirname = os.path.dirname(last_series)
    season_name = os.path.basename(dirname)

    season_dir = os.path.dirname(dirname)
    try:
        entries = os.listdir(season_dir)
    except OSError as error:
        print(f"cannot list {season_dir}: {error}")
        return None

    candidates = sorted(
        (
            name
            for name in entries
            if not name.startswith(".")
            and os.path.isdir(os.path.join(season_dir, name))
        ),
        key=lambda name: (natural_key(name), name),
    )
    if not candidates:
        print(f"no seasons found in {season_dir}")
        return None

    if season_name in candidates:
        start = candidates.index(season_name)
        ordered = candidates[start + 1 :] + candidates[: start + 1]
    else:
        print(
            f"season {season_name} not found in {season_dir}, starting from {candidates[0]}"
        )
        ordered = candidates

    for name in ordered:
        season_path = os.path.join(season_dir, name)
        for file_name in list_candidates(season_path):
            file_path = os.path.join(season_path, file_name)
            if probe_duration(file_path) is not None:
                print(f"new season starts with: {file_name}")
                return file_path

    print(f"no playable files found in seasons under {season_dir}")
    return None


if __name__ == "__main__":
    with open("history", "r") as f:
        info_string = f.readline().strip().split(":")
        last_series = info_string[0]
    print(f"history: {last_series}")

    consecutive_failed_runs = 0

    while True:
        if show_season(last_series):
            consecutive_failed_runs = 0
        else:
            consecutive_failed_runs += 1
            print(
                f"warning: no episodes played ({consecutive_failed_runs} consecutive failed runs)"
            )
            if consecutive_failed_runs >= 3:
                print("stopping after 3 consecutive failed runs")
                break
            time.sleep(5)
        next_series = change_season(last_series)
        if next_series is None:
            print("no playable episodes left, stopping")
            break
        last_series = next_series
