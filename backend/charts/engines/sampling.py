from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from charts.domain import Aspect, LongitudeRange, PlanetPosition

ZODIAC = (
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
)
MAJOR_ASPECT_ANGLES = {
    "conjunction": 0.0,
    "sextile": 60.0,
    "square": 90.0,
    "trine": 120.0,
    "opposition": 180.0,
}


@dataclass(frozen=True, slots=True)
class SamplePosition:
    longitude: float
    is_retrograde: bool


@dataclass(frozen=True, slots=True)
class SampleFrame:
    instant: datetime
    positions: dict[str, SamplePosition]
    aspects: dict[tuple[str, str, str], Aspect]


@dataclass(frozen=True, slots=True)
class StabilitySummary:
    samples: tuple[SampleFrame, ...]
    planets: tuple[PlanetPosition, ...]
    stable_aspects: tuple[Aspect, ...]
    capped: bool


def _circular_delta(start: float, end: float) -> float:
    return (end - start + 180.0) % 360.0 - 180.0


def _separation(one: float, two: float) -> float:
    return abs(_circular_delta(one, two))


def _is_risky(
    left: SampleFrame,
    middle: SampleFrame,
    right: SampleFrame,
    interpolation_tolerance: float,
    aspect_orb: float,
    boundary_margin: float,
) -> bool:
    for name, midpoint in middle.positions.items():
        start, end = left.positions[name], right.positions[name]
        expected = (start.longitude + _circular_delta(start.longitude, end.longitude) / 2.0) % 360.0
        if abs(_circular_delta(expected, midpoint.longitude)) > interpolation_tolerance:
            return True
        if len({start.is_retrograde, midpoint.is_retrograde, end.is_retrograde}) > 1:
            return True
        if len({int(value.longitude % 360.0 // 30.0) for value in (start, midpoint, end)}) > 1:
            return True
    if not (set(left.aspects) == set(middle.aspects) == set(right.aspects)):
        return True
    names = sorted(middle.positions)
    for index, one in enumerate(names):
        for two in names[index + 1 :]:
            separations = [
                _separation(frame.positions[one].longitude, frame.positions[two].longitude)
                for frame in (left, middle, right)
            ]
            for angle in MAJOR_ASPECT_ANGLES.values():
                distances = [abs(value - angle) for value in separations]
                variation = max(distances) - min(distances)
                if (
                    min(abs(value - aspect_orb) for value in distances)
                    <= variation + boundary_margin
                ):
                    return True
    return False


def adaptive_sample(
    start: datetime,
    end: datetime,
    calculate: Callable[[datetime], SampleFrame],
    *,
    min_step: timedelta = timedelta(minutes=15),
    max_samples: int = 17,
    interpolation_tolerance: float = 0.01,
    aspect_orb: float = 8.0,
    boundary_margin: float = 0.05,
) -> StabilitySummary:
    if end <= start or max_samples < 5:
        raise ValueError("Invalid sampling bounds")
    cache = {}
    for fraction in (0.0, 0.25, 0.5, 0.75, 1.0):
        instant = start + (end - start) * fraction
        cache[instant] = calculate(instant)
    ordered = sorted(cache)
    intervals = list(zip(ordered, ordered[1:], strict=False))
    capped = False
    while intervals:
        left_time, right_time = intervals.pop(0)
        if right_time - left_time <= min_step:
            continue
        if len(cache) >= max_samples:
            capped = True
            break
        midpoint = left_time + (right_time - left_time) / 2
        frame = calculate(midpoint)
        cache[midpoint] = frame
        if _is_risky(
            cache[left_time],
            frame,
            cache[right_time],
            interpolation_tolerance,
            aspect_orb,
            boundary_margin,
        ):
            intervals.extend(((left_time, midpoint), (midpoint, right_time)))
    frames = tuple(cache[value] for value in sorted(cache))
    names = sorted(frames[0].positions)
    planets = []
    for name in names:
        anchor = frames[0].positions[name].longitude
        unwrapped = [
            anchor + _circular_delta(anchor, frame.positions[name].longitude) for frame in frames
        ]
        low, high = min(unwrapped), max(unwrapped)
        sign_indexes = {int(frame.positions[name].longitude % 360.0 // 30.0) for frame in frames}
        retrograde_states = {frame.positions[name].is_retrograde for frame in frames}
        sign_invariant = len(sign_indexes) == 1
        retrograde_invariant = len(retrograde_states) == 1
        planets.append(
            PlanetPosition(
                name=name,
                longitude=None,
                zodiac_sign=ZODIAC[next(iter(sign_indexes))] if sign_invariant else None,
                is_retrograde=next(iter(retrograde_states)) if retrograde_invariant else None,
                house_number=None,
                longitude_range=LongitudeRange(low % 360.0, high % 360.0, low < 0 or high >= 360),
                sign_is_invariant=sign_invariant,
                retrograde_is_invariant=retrograde_invariant,
            )
        )
    stable_aspects = []
    if not capped:
        stable_keys = (
            set.intersection(*(set(frame.aspects) for frame in frames)) if frames else set()
        )
        for key in sorted(stable_keys):
            observed = [frame.aspects[key] for frame in frames]
            stable_aspects.append(
                Aspect(key[0], key[1], key[2], max(item.orb_degrees for item in observed), True)
            )
    return StabilitySummary(frames, tuple(planets), tuple(stable_aspects), capped)
