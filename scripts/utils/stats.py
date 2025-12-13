import sys

from dataclasses import asdict, dataclass
from lxml.html import HtmlElement
from typing import Any

from utils.lxml_funcs import find


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


TRAINER_ROW = 'RC-trainerName__row'
JOCKEY_ROW = 'RC-jockeyName__row'
HORSE_ROW = 'RC-horseName__row'


def get_table_rows(doc: HtmlElement) -> dict[str, list[HtmlElement]]:
    table_rows: dict[str, list[HtmlElement]] = {}

    tables = doc.xpath("//tbody[@class='RC-stats__tableBody']")

    for table in tables:
        rows = table.xpath('.//tr')

        if not rows:
            continue

        first_cell = rows[0].find('td')
        if first_cell is None:
            continue

        row_type = first_cell.attrib.get('data-test-selector', '')

        if row_type == HORSE_ROW:
            table_rows[HORSE_ROW] = rows
        elif row_type == JOCKEY_ROW:
            table_rows[JOCKEY_ROW] = rows
        elif row_type == TRAINER_ROW:
            table_rows[TRAINER_ROW] = rows

    return table_rows


class Stats:
    def __init__(self, doc: HtmlElement):
        self.horses: dict[str, HorseStats] = {}
        self.jockeys: dict[str, dict[str, Any]] = {}
        self.trainers: dict[str, dict[str, Any]] = {}

        rows = get_table_rows(doc)

        self._get_horse_stats(rows[HORSE_ROW])
        self._get_jockey_trainer_stats(rows[JOCKEY_ROW], self.jockeys)
        self._get_jockey_trainer_stats(rows[TRAINER_ROW], self.trainers)

    def _get_horse_stats(self, rows: list[HtmlElement]) -> None:
        for row in rows:
            a = row.find('.//a')
            href = a.attrib.get('href') if a is not None else None
            horse_id = href.split('/')[3] if href is not None else None

            if horse_id is None:
                continue

            going_wins_runs = find(row, 'td', 'RC-goingWinsRuns__row')
            going_wins, going_runs = [x.strip() for x in going_wins_runs.split('-')]

            distance_wins_runs = find(row, 'td', 'RC-distanceWinsRuns__row')
            distance_wins, distance_runs = [x.strip() for x in distance_wins_runs.split('-')]

            course_wins_runs = find(row, 'td', 'RC-courseWinsRuns__row')
            course_wins, course_runs = [x.strip() for x in course_wins_runs.split('-')]

            self.horses[horse_id] = HorseStats(
                course=CourseStats(runs=course_runs, wins=course_wins),
                distance=DistanceStats(runs=distance_runs, wins=distance_wins),
                going=GoingStats(runs=going_runs, wins=going_wins),
            )

    def _get_jockey_trainer_stats(
        self, rows: list[HtmlElement], target: dict[str, dict[str, str]]
    ) -> None:
        for row in rows:
            a = row.find('.//a')
            href = a.attrib.get('href') if a is not None else None
            jockey_trainer_id = href.split('/')[3] if href is not None else None

            if jockey_trainer_id is None:
                continue

            wins_runs = find(row, 'td', 'RC-lastWinsRuns__row')
            wins_runs_ovr = find(row, 'td', 'RC-overallWinsRuns__row')

            wins, runs = [x.strip() for x in wins_runs.split('-')]
            wins_ovr, runs_ovr = [x.strip() for x in wins_runs_ovr.split('-')]

            wins_pct = find(row, 'td', 'RC-lastPercent__row')
            wins_pct_ovr = find(row, 'td', 'RC-overallPercent__row')

            profit = find(row, 'td', 'RC-lastProfit__row')
            profit_ovr = find(row, 'td', 'RC-overallProfit__row')

            target[jockey_trainer_id] = {
                'last_14_runs': runs,
                'last_14_wins': wins,
                'last_14_wins_pct': wins_pct,
                'last_14_profit': profit,
                'ovr_runs': runs_ovr,
                'ovr_wins': wins_ovr,
                'ovr_wins_pct': wins_pct_ovr,
                'ovr_profit': profit_ovr,
            }
