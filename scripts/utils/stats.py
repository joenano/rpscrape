from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class CourseStats:
    runs: str
    wins: str


@dataclass
class DistanceStats:
    runs: str
    wins: str


@dataclass
class GoingStats:
    runs: str
    wins: str


@dataclass
class HorseStats:
    course: CourseStats
    distance: DistanceStats
    going: GoingStats

    def to_dict(self):
        return asdict(self)


def _split_wins_runs(wins_runs: str | None) -> tuple[str, str]:
    """Split a 'wins-runs' string into (wins, runs). Returns ('0', '0') on None/missing."""
    if wins_runs:
        wins, runs = wins_runs.split('-', 1)
        return wins.strip(), runs.strip()
    return '0', '0'


def _parse_segment(segment: dict | None) -> dict[str, Any]:
    """Parse a stats segment (last14Days, overall, twoYo, etc.) into a flat dict."""
    if not segment:
        return {'wins': '0', 'runs': '0', 'strike_rate': None, 'profit': None}
    wins, runs = _split_wins_runs(segment.get('winsRuns'))
    return {
        'wins': wins,
        'runs': runs,
        'strike_rate': segment.get('strikeRate'),
        'profit': segment.get('profit'),
    }


class Stats:
    def __init__(self, data: dict):
        self.horses: dict[str, HorseStats] = {}
        self.jockeys: dict[str, dict[str, Any]] = {}
        self.trainers: dict[str, dict[str, Any]] = {}

        stats = data.get('stats', {})
        self._parse_horses(stats.get('horses', []))
        self._parse_jockeys_trainers(stats.get('jockeys', []), self.jockeys)
        self._parse_jockeys_trainers(stats.get('trainers', []), self.trainers)

    def _parse_horses(self, horses: list[dict]) -> None:
        for horse in horses:
            horse_id = str(horse['id'])
            g_wins, g_runs = _split_wins_runs((horse.get('going') or {}).get('winsRuns'))
            d_wins, d_runs = _split_wins_runs((horse.get('distance') or {}).get('winsRuns'))
            c_wins, c_runs = _split_wins_runs((horse.get('course') or {}).get('winsRuns'))

            self.horses[horse_id] = HorseStats(
                going=GoingStats(wins=g_wins, runs=g_runs),
                distance=DistanceStats(wins=d_wins, runs=d_runs),
                course=CourseStats(wins=c_wins, runs=c_runs),
            )

    def _parse_jockeys_trainers(self, entries: list[dict], target: dict[str, dict[str, Any]]) -> None:
        for entry in entries:
            entity_id = str(entry['id'])
            last14 = _parse_segment(entry.get('last14Days'))
            overall = _parse_segment(entry.get('overall'))

            target[entity_id] = {
                'last_14_runs': last14['runs'],
                'last_14_wins': last14['wins'],
                'last_14_wins_pct': last14['strike_rate'],
                'last_14_profit': last14['profit'],
                'ovr_runs': overall['runs'],
                'ovr_wins': overall['wins'],
                'ovr_wins_pct': overall['strike_rate'],
                'ovr_profit': overall['profit'],
                'two_yo': _parse_segment(entry.get('twoYo')),
                'three_yo': _parse_segment(entry.get('threeYo')),
                'four_yo_plus': _parse_segment(entry.get('fourYoPlus')),
                'hurdle': _parse_segment(entry.get('hurdle')),
                'chase': _parse_segment(entry.get('chase')),
                'nhf': _parse_segment(entry.get('nhf')),
            }
