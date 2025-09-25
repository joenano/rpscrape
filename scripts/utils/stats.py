from lxml.html import HtmlElement

from utils.lxml_funcs import find, find_element


def clean_name(name: str):
    if name:
        return name.strip().replace("'", '').lower().title()
    else:
        return ''


class Stats:
    def __init__(self, doc: HtmlElement):
        self.horses = {}
        self.jockeys = {}
        self.trainers = {}

        stats = find_element(doc, 'section', 'stats', 'data-accordion-row')
        tables = doc.xpath("//table[@data-test-selector='RC-table']")

        for table in tables:
            rows = table.xpath('.//tr[@class="ui-table__row"]')
            row_type = rows[0].find('td').attrib['data-test-selector']

            if 'horse' in row_type:
                self.get_horse_stats(rows)
            elif 'jockey' in row_type:
                self.get_jockey_stats(rows)
            elif 'trainer' in row_type:
                self.get_trainer_stats(rows)

    def get_horse_stats(self, rows):
        for row in rows:
            name = find(row, 'td', 'RC-horseName__row')
            name = clean_name(name)

            going_wins_runs = find(row, 'td', 'RC-goingWinsRuns__row')
            going_wins, going_runs = [x.strip() for x in going_wins_runs.split('-')]

            distance_wins_runs = find(row, 'td', 'RC-distanceWinsRuns__row')
            distance_wins, distance_runs = [x.strip() for x in distance_wins_runs.split('-')]

            course_wins_runs = find(row, 'td', 'RC-courseWinsRuns__row')
            course_wins, course_runs = [x.strip() for x in course_wins_runs.split('-')]

            self.horses[name] = {
                'course': {
                    'runs': course_runs,
                    'wins': course_wins,
                },
                'going': {
                    'runs': going_runs,
                    'wins': going_wins,
                },
                'distance': {
                    'runs': distance_runs,
                    'wins': distance_wins,
                },
            }

    def get_jockey_stats(self, rows):
        for row in rows:
            name = find(row, 'td', 'RC-jockeyName__row')
            name = clean_name(name)

            wins_runs = find(row, 'td', 'RC-lastWinsRuns__row')
            wins_runs_ovr = find(row, 'td', 'RC-overallWinsRuns__row')

            wins, runs = [x.strip() for x in wins_runs.split('-')]
            wins_ovr, runs_ovr = [x.strip() for x in wins_runs_ovr.split('-')]

            wins_pct = find(row, 'td', 'RC-lastPercent__row')
            wins_pct_ovr = find(row, 'td', 'RC-overallPercent__row')

            profit = find(row, 'td', 'RC-lastProfit__row')
            profit_ovr = find(row, 'td', 'RC-overallProfit__row')

            self.jockeys[name] = {
                'last_14_runs': runs,
                'last_14_wins': wins,
                'last_14_wins_pct': wins_pct,
                'last_14_profit': profit,
                'ovr_runs': runs_ovr,
                'ovr_wins': wins_ovr,
                'ovr_wins_pct': wins_pct_ovr,
                'ovr_profit': profit_ovr,
            }

    def get_trainer_stats(self, rows):
        for row in rows:
            name = find(row, 'td', 'RC-trainerName__row')
            name = clean_name(name)

            wins_runs = find(row, 'td', 'RC-lastWinsRuns__row')
            wins_runs_ovr = find(row, 'td', 'RC-overallWinsRuns__row')

            wins, runs = [x.strip() for x in wins_runs.split('-')]
            wins_ovr, runs_ovr = [x.strip() for x in wins_runs_ovr.split('-')]

            wins_pct = find(row, 'td', 'RC-lastPercent__row')
            wins_pct_ovr = find(row, 'td', 'RC-overallPercent__row')

            profit = find(row, 'td', 'RC-lastProfit__row')
            profit_ovr = find(row, 'td', 'RC-overallProfit__row')

            self.trainers[name] = {
                'last_14_runs': runs,
                'last_14_wins': wins,
                'last_14_wins_pct': wins_pct,
                'last_14_profit': profit,
                'ovr_runs': runs_ovr,
                'ovr_wins': wins_ovr,
                'ovr_wins_pct': wins_pct_ovr,
                'ovr_profit': profit_ovr,
            }
