"""Durations as people write them ("1:23:45", "42:10") and as the data stores them (ms)."""


def parse_duration(text: str | None) -> int | None:
    """Parse M:SS or H:MM:SS into milliseconds. None if blank or invalid."""
    parts = (text or "").strip().split(":")
    if len(parts) not in (2, 3):
        return None
    try:
        numbers = [int(p) for p in parts]
    except ValueError:
        return None
    hours, minutes, seconds = ([0] + numbers) if len(numbers) == 2 else numbers
    return ((hours * 60 + minutes) * 60 + seconds) * 1000


def format_duration(ms: int) -> str:
    """Format milliseconds as H:MM:SS, or M:SS under an hour."""
    minutes, seconds = divmod(ms // 1000, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes}:{seconds:02d}"
