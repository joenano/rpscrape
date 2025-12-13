from dataclasses import asdict, dataclass
from lxml.html import HtmlElement

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


@dataclass
class JockeyTrainerStats:
    last_14_profit: str
    last_14_runs: str
    last_14_wins: str
    last_14_wins_pct: str
    ovr_profit: str
    ovr_runs: str
    ovr_wins: str
    ovr_wins_pct: str

    def to_dict(self):
        return asdict(self)


TRAINER_ROW = 'RC-trainerName__row'
JOCKEY_ROW = 'RC-jockeyName__row'
HORSE_ROW = 'RC-horseName__row'


class Stats:
    def __init__(self, doc: HtmlElement):
        self.horses: dict[str, HorseStats] = {}
        self.jockeys: dict[str, JockeyTrainerStats] = {}
        self.trainers: dict[str, JockeyTrainerStats] = {}

        tables = doc.xpath("//table[@data-test-selector='RC-table']")

        for table in tables:
            rows = table.xpath('.//tr[@class="ui-table__row"]')
            if not rows:
                continue

            first_cell = rows[0].find('td')
            if first_cell is None:
                continue

            row_type = first_cell.attrib.get('data-test-selector', '')

            if row_type == HORSE_ROW:
                self._get_horse_stats(rows)
            elif row_type == JOCKEY_ROW:
                self._get_jockey_trainer_stats(rows, self.jockeys)
            elif row_type == TRAINER_ROW:
                self._get_jockey_trainer_stats(rows, self.trainers)

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
        self, rows: list[HtmlElement], target: dict[str, JockeyTrainerStats]
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

            target[jockey_trainer_id] = JockeyTrainerStats(
                last_14_runs=runs,
                last_14_wins=wins,
                last_14_wins_pct=wins_pct,
                last_14_profit=profit,
                ovr_runs=runs_ovr,
                ovr_wins=wins_ovr,
                ovr_wins_pct=wins_pct_ovr,
                ovr_profit=profit_ovr,
            )
