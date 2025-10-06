import csv
import requests
import time

from datetime import date, timedelta, datetime

from models.betfair import BSP, BSPMap


class Betfair:
    def __init__(self, race_urls: list[str]):
        self.urls: list[tuple[str, str]] = create_urls(race_urls)
        self.data: BSPMap = {}
        self.rows: list[BSP] = []

        for url, region in self.urls:
            rows = get_data(url, region)

            if not rows:
                continue

            self.rows.extend(rows)

            for row in rows:
                key = (row.region, row.date, row.off)

                if key not in self.data:
                    self.data[key] = []

                self.data[key].append(row)


def create_date_range(date_start: str, date_end: str) -> list[date]:
    start = datetime.strptime(date_start, '%Y-%m-%d').date() - timedelta(days=1)
    end = datetime.strptime(date_end, '%Y-%m-%d').date() + timedelta(days=1)

    dates: list[date] = []
    current = start
    while current <= end:
        dates.append(current)
        current += timedelta(days=1)

    return dates


def create_urls(race_urls: list[str]) -> list[tuple[str, str]]:
    url_base = 'https://promo.betfair.com/betfairsp/prices/dwbfprices'
    regions = ['uk', 'ire', 'usa', 'aus', 'fr', 'uae']

    dates = {x.split('/')[6] for x in race_urls}
    date_start, date_end = min(dates), max(dates)

    dates = create_date_range(date_start, date_end)

    urls: list[tuple[str, str]] = []

    for region in regions:
        for d in dates:
            formatted = d.strftime('%d%m%Y')
            urls.append((f'{url_base}{region}win{formatted}.csv', region.upper()))

    return urls


def get_data(url: str, region: str) -> list[BSP] | None:
    resp = requests.get(url)
    for _ in range(4):
        if resp.status_code == 404:
            return None
        if resp.status_code == 429:
            time.sleep(10)
            resp = requests.get(url)
            continue
        if resp.status_code == 200:
            break
        raise RuntimeError(f'HTTP error {resp.status_code} for URL {url}')

    reader = csv.DictReader(resp.content.decode().splitlines())
    rows: list[BSP] = []

    for record in reader:
        bsp = BSP.from_record(record, region)
        if bsp:
            rows.append(bsp)

    return rows
