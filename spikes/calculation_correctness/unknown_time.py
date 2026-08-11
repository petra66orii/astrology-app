"""Bounded adaptive sampling for the unknown-birth-time behavior contract."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable


MAJOR_ASPECT_ANGLES = {"conjunction": 0.0, "sextile": 60.0, "square": 90.0, "trine": 120.0, "opposition": 180.0}


@dataclass(frozen=True, slots=True)
class SamplePosition:
    longitude: float
    is_retrograde: bool


@dataclass(frozen=True, slots=True)
class SampleFrame:
    instant: datetime
    positions: dict[str, SamplePosition]


@dataclass(frozen=True, slots=True)
class StabilitySummary:
    samples: tuple[SampleFrame, ...]
    sign_invariant: dict[str, bool]
    retrograde_invariant: dict[str, bool]
    longitude_ranges: dict[str, tuple[float, float, bool]]
    stable_aspects: tuple[tuple[str, str, str], ...]
    capped: bool


def _circular_delta(a: float, b: float) -> float:
    return (b - a + 180.0) % 360.0 - 180.0


def _separation(a: float, b: float) -> float:
    delta = abs(_circular_delta(a, b))
    return min(delta, 360.0 - delta)


def _risky(
    left: SampleFrame, middle: SampleFrame, right: SampleFrame,
    interpolation_tolerance: float, boundary_margin: float, aspect_orb: float,
) -> bool:
    for name, midpoint in middle.positions.items():
        start, end = left.positions[name], right.positions[name]
        expected = (start.longitude + _circular_delta(start.longitude, end.longitude) / 2.0) % 360.0
        if abs(_circular_delta(expected, midpoint.longitude)) > interpolation_tolerance:
            return True
        if len({start.is_retrograde, midpoint.is_retrograde, end.is_retrograde}) > 1:
            return True
        longitudes = (start.longitude, midpoint.longitude, end.longitude)
        if len({int(value % 360.0 // 30.0) for value in longitudes}) > 1:
            return True
    names = sorted(middle.positions)
    for index, one in enumerate(names):
        for two in names[index + 1:]:
            values = [_separation(frame.positions[one].longitude, frame.positions[two].longitude) for frame in (left, middle, right)]
            for angle in MAJOR_ASPECT_ANGLES.values():
                distances = [abs(value - angle) for value in values]
                validity = {distance <= aspect_orb for distance in distances}
                variation = max(distances) - min(distances)
                if len(validity) > 1 or min(abs(distance - aspect_orb) for distance in distances) <= variation + boundary_margin:
                    return True
    return False


def adaptive_sample(
    start: datetime, end: datetime, calculate: Callable[[datetime], dict[str, SamplePosition]], *,
    min_step: timedelta = timedelta(minutes=5), max_samples: int = 129,
    interpolation_tolerance: float = 0.01, boundary_margin: float = 0.05,
    aspect_orb: float = 8.0,
) -> StabilitySummary:
    if end <= start:
        raise ValueError("end must be after start")
    fractions = (0.0, 0.25, 0.5, 0.75, 1.0)
    cache = {start + (end - start) * fraction: None for fraction in fractions}
    for instant in cache:
        cache[instant] = SampleFrame(instant, calculate(instant))

    capped = False
    changed = True
    while changed:
        changed = False
        ordered = sorted(cache)
        for left_time, right_time in zip(ordered, ordered[1:]):
            if right_time - left_time <= min_step or len(cache) >= max_samples:
                capped = capped or len(cache) >= max_samples
                continue
            middle_time = left_time + (right_time - left_time) / 2
            middle = SampleFrame(middle_time, calculate(middle_time))
            if _risky(cache[left_time], middle, cache[right_time], interpolation_tolerance, boundary_margin, aspect_orb):
                cache[middle_time] = middle
                changed = True
                if len(cache) >= max_samples:
                    capped = True
                    break

    samples = tuple(cache[instant] for instant in sorted(cache))
    planet_names = sorted(samples[0].positions)
    sign_invariant = {name: len({int(frame.positions[name].longitude % 360 // 30) for frame in samples}) == 1 for name in planet_names}
    retrograde_invariant = {name: len({frame.positions[name].is_retrograde for frame in samples}) == 1 for name in planet_names}
    ranges: dict[str, tuple[float, float, bool]] = {}
    for name in planet_names:
        anchor = samples[0].positions[name].longitude
        unwrapped = [anchor + _circular_delta(anchor, frame.positions[name].longitude) for frame in samples]
        low, high = min(unwrapped), max(unwrapped)
        ranges[name] = (low % 360.0, high % 360.0, low < 0.0 or high >= 360.0)

    stable: list[tuple[str, str, str]] = []
    if not capped:
        for index, one in enumerate(planet_names):
            for two in planet_names[index + 1:]:
                separations = [_separation(frame.positions[one].longitude, frame.positions[two].longitude) for frame in samples]
                for aspect, angle in MAJOR_ASPECT_ANGLES.items():
                    distances = [abs(value - angle) for value in separations]
                    if max(distances) < aspect_orb - boundary_margin:
                        stable.append((one, two, aspect))
    return StabilitySummary(samples, sign_invariant, retrograde_invariant, ranges, tuple(stable), capped)
