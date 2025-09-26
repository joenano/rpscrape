import requests
import sys

from datetime import datetime
from jarowinkler import jarowinkler_similarity
from lxml import html
from lxml.html import HtmlElement
from re import search, sub

from models.betfair import BSPMap
from models.race import RaceInfo, RunnerInfo
from utils.header import RandomHeader
from utils.pedigree import Pedigree

from utils.cleaning import clean_race, clean_string, strip_row
from utils.date import convert_date
from utils.going import get_surface
from utils.lxml_funcs import find
from utils.region import get_region

rh = RandomHeader()

regex_class = r'(\(|\s)(C|c)lass (\d|[A-Ha-h])(\)|\s)'
regex_group = r'(\(|\s)((G|g)rade|(G|g)roup) (\d|[A-Ca-c]|I*)(\)|\s)'


class VoidRaceError(Exception):
    pass


class Race:
    def __init__(
        self,
        url: str,
        document: HtmlElement,
        code: str,
        fields: list[str],
        bsp_map: BSPMap | None = None,
    ):
        self.url: str = url
        self.doc: HtmlElement = document
        self.race_info: RaceInfo = RaceInfo()
        self.runner_info: RunnerInfo = RunnerInfo()

        url_split = self.url.split('/')

        date_time_info = self.doc.find('.//main[@data-analytics-race-date-time]')

        while date_time_info is None:
            r = requests.get(self.url, headers=rh.header())
            doc = html.fromstring(r.content)
            date_time_info = doc.find('.//main[@data-analytics-race-date-time]')
            self.doc = doc

        self.race_info.course = date_time_info.attrib['data-analytics-coursename']

        if 'belmont at the big a' in self.race_info.course.lower():
            self.race_info.course_id = '255'
            self.race_info.course = 'Aqueduct'
        else:
            self.race_info.course_id = url_split[4]

        date_time = date_time_info.attrib['data-analytics-race-date-time']
        self.race_info.off = parse_time(date_time)

        self.race_info.date = convert_date(url_split[6])
        self.race_info.region = get_region(self.race_info.course_id)
        self.race_info.race_id = url_split[7]
        self.race_info.going = find(
            self.doc, 'span', 'rp-raceTimeCourseName_condition', property='class'
        )
        self.race_info.surface = get_surface(self.race_info.going)
        self.race_info.race_name = find(self.doc, 'h2', 'rp-raceTimeCourseName__title', property='class')
        self.race_info.r_class = find(
            self.doc, 'span', 'rp-raceTimeCourseName_class', property='class'
        ).strip('()')

        if self.race_info.r_class == '':
            self.race_info.r_class = self.get_race_class()

        self.race_info.pattern = self.get_race_pattern()
        self.race_info.race_name = clean_race(self.race_info.race_name)
        self.race_info.age_band, self.race_info.rating_band = self.parse_race_bands()

        self.race_info.sex_rest = self.sex_restricted()
        (
            self.race_info.dist,
            self.race_info.dist_y,
            self.race_info.dist_f,
            self.race_info.dist_m,
        ) = self.get_race_distances()

        self.race_info.r_type = self.get_race_type(code)
        self.race_info.ran = self.get_num_runners()

        pedigree_info = self.doc.xpath("//tr[@data-test-selector='block-pedigreeInfoFullResults']/td")
        pedigree = Pedigree(pedigree_info)

        self.runner_info.sire_id = pedigree.id_sires
        self.runner_info.sire = pedigree.sires
        self.runner_info.dam_id = pedigree.id_dams
        self.runner_info.dam = pedigree.dams
        self.runner_info.damsire_id = pedigree.id_damsires
        self.runner_info.damsire = pedigree.damsires
        self.runner_info.sex = self.get_sexs(pedigree.pedigrees)
        self.runner_info.comment = self.get_comments()
        self.runner_info.pos = self.get_positions()
        self.runner_info.prize = self.get_prizemoney()
        self.runner_info.draw = self.get_draws()
        self.runner_info.ovr_btn, self.runner_info.btn = self.get_distance_btn()
        self.runner_info.sp = self.get_starting_prices()
        self.runner_info.dec = self.get_decimal_odds()
        self.runner_info.num = self.get_numbers()

        self.race_info.ran = self.race_info.ran if self.race_info.ran else str(len(self.runner_info.num))

        self.runner_info.age = self.get_horse_ages()
        self.runner_info.horse = self.get_names_horse()
        self.runner_info.horse_id = self.get_ids_horse()
        self.runner_info.jockey = self.get_names_jockey()
        self.runner_info.jockey_id = self.get_ids_jockey()
        self.runner_info.trainer = self.get_names_trainer()
        self.runner_info.trainer_id = self.get_ids_trainer()
        self.runner_info.owner = self.get_names_owner()
        self.runner_info.owner_id = self.get_ids_owner()
        self.runner_info.hg = self.get_headgear()
        self.runner_info.wgt, self.runner_info.lbs = self.get_weights()
        self.runner_info.ofr = strip_row(self.doc.xpath('//td[@data-ending="OR"]/text()'))
        self.runner_info.rpr = strip_row(self.doc.xpath('//td[@data-ending="RPR"]/text()'))
        self.runner_info.ts = strip_row(self.doc.xpath('//td[@data-ending="TS"]/text()'))
        self.runner_info.silk_url = self.doc.xpath('//img[@class="rp-horseTable__silk"]/@src')
        self.runner_info.time = self.get_finishing_times()
        self.runner_info.secs = self.time_to_seconds(self.runner_info.time)

        self.clean_non_completions()

        if bsp_map:
            self.join_betfair_data(bsp_map)

        self.csv_data: list[str] = self.create_csv_data(fields)

    def calculate_times(
        self, win_time: float, dist_btn: list[str], going: str, course: str, race_type: str
    ) -> list[str]:
        times: list[str] = []
        going_lower = going.lower()
        course_lower = course.lower()

        if race_type.lower() == 'flat':
            if not going:
                lps_scale = 6.0
            elif going_lower in {'firm', 'standard', 'fast', 'hard', 'slow', 'sloppy'}:
                lps_scale = 5.0 if 'southwell' in course_lower else 6.0
            elif 'good' in going_lower:
                lps_scale = 5.5 if going_lower in {'soft', 'yielding'} else 6.0
            elif going_lower in {'soft', 'heavy', 'yielding', 'holding'}:
                lps_scale = 5.0
            else:
                lps_scale = 5.0
        else:
            if not going:
                lps_scale = 5.0
            elif going_lower in {'firm', 'standard', 'hard', 'fast'}:
                lps_scale = 4.0 if 'southwell' in course_lower else 5.0
            elif 'good' in going_lower:
                lps_scale = 4.5 if going_lower in {'soft', 'yielding'} else 5.0
            elif going_lower in {'soft', 'heavy', 'yielding', 'slow', 'holding'}:
                lps_scale = 4.0
            else:
                lps_scale = 5.0

        for dist in dist_btn:
            try:
                time = win_time + (float(dist) / lps_scale)
                minutes = int(time // 60)
                seconds = time % 60
                times.append(f'{minutes}:{seconds:05.2f}')
            except ValueError:
                times.append('')

        return times

    def clean_non_completions(self):
        for i, pos in enumerate(self.runner_info.pos):
            if not pos.isnumeric() and pos != 'DSQ':
                self.runner_info.time[i] = '-'
                self.runner_info.secs[i] = '-'
                self.runner_info.ovr_btn[i] = '-'
                self.runner_info.btn[i] = '-'

    def create_csv_data(self, fields: list[str]) -> list[str]:
        field_mapping = {'type': 'r_type', 'class': 'r_class', 'or': 'ofr'}

        race_values: list[str] = []
        runner_values: list[list[str]] = []

        for field in fields:
            actual_field = field_mapping.get(field, field)

            if hasattr(self.race_info, actual_field):
                race_values.append(str(getattr(self.race_info, actual_field)))
            elif hasattr(self.runner_info, actual_field):
                runner_values.append([str(v) for v in getattr(self.runner_info, actual_field)])

        race_prefix = ','.join(race_values)
        rows: list[str] = []
        for row in zip(*runner_values, strict=False):
            rows.append(race_prefix + ',' + ','.join(row) if race_prefix else ','.join(row))
        return rows

    def get_comments(self):
        def clean_comment(x: str):
            return x.strip().replace('  ', '').replace(',', ' -').replace('\n', ' ').replace('\r', '')

        coms = self.doc.xpath("//tr[@class='rp-horseTable__commentRow ng-cloak']/td/text()")
        return [clean_comment(com) for com in coms]

    def get_decimal_odds(self):
        odds = [sub('(F|J|C)', '', sp) for sp in self.runner_info.sp]
        return fraction_to_decimal(odds)

    def get_distance_btn(self) -> tuple[list[str], list[str]]:
        btn: list[str] = []
        ovr_btn: list[str] = []

        for element in self.doc.xpath("//span[@class='rp-horseTable__pos__length']"):
            distances: list[HtmlElement] = element.findall('span')

            if len(distances) == 2:
                btn.append(distances[0].text or '0')
                ovr_btn.append((distances[1].text or '0').strip('[]'))
            else:
                text: str = distances[0].text or '0'

                if text == 'dht':
                    btn.append(text)
                    ovr_btn.append(ovr_btn[-1] if ovr_btn else text)
                else:
                    btn.append(text)
                    ovr_btn.append(text)

        try:
            btn = [distance_to_decimal(b) for b in btn]
        except AttributeError as e:
            raise RuntimeError(
                f'Failed to process btn distances for {getattr(self, "url", "unknown")}'
            ) from e

        ovr_btn = [distance_to_decimal(b) for b in ovr_btn]

        num_runners: int = len(self.runner_info.pos)

        if len(ovr_btn) < num_runners:
            ovr_btn.extend('' for _ in range(num_runners - len(ovr_btn)))

        if len(btn) < num_runners:
            btn.extend('' for _ in range(num_runners - len(btn)))

        return ovr_btn, btn

    def get_draws(self) -> list[str]:
        draws = self.doc.xpath("//sup[@class='rp-horseTable__pos__draw']/text()")
        return [draw.replace('\xa0', ' ').strip().strip('()') for draw in draws]
        # return self.doc.xpath("//span[@class='rp-horseTable__pos__draw']/@data-order-draw")

    def get_finishing_times(self):
        # adjust overall distance beaten when margins under a quarter length not accounted for
        # for instance when 2 horses finish with a head between them 4 lengths behind winner
        # both horses are recorded as being beaten 4 lengths overall by RP

        btn_adj: list[str] = []

        for btn, ovr_btn in zip(self.runner_info.btn, self.runner_info.ovr_btn):
            try:
                if float(ovr_btn) > 1 and float(btn) < 0.25:
                    btn_adj.append(str(float(btn) + float(ovr_btn)))
                else:
                    btn_adj.append(ovr_btn)
            except ValueError:
                btn_adj.append(ovr_btn)

        winning_time = self.get_winning_time()

        if winning_time is None:
            return ['-' for _ in range(int(self.race_info.ran))]

        return self.calculate_times(
            winning_time,
            btn_adj,
            self.race_info.going,
            self.race_info.course,
            self.race_info.r_type,
        )

    def get_headgear(self) -> list[str]:
        results: list[str] = []
        for horse in self.doc.xpath("//td[contains(@class, 'rp-horseTable__wgt')]"):
            hg = horse.find('.//span[@class="rp-horseTable__headGear"]')
            if hg is None:
                results.append('')
                continue

            if len(hg) > 1 and hg[1].text:
                results.append((hg.text or '') + hg[1].text.strip())
            else:
                results.append(hg.text or '')
        return results

    def get_horse_ages(self) -> list[str]:
        ages = self.doc.xpath("//td[@data-test-selector='horse-age']/text()")
        return [age.strip() for age in ages]

    def get_ids_horse(self) -> list[str]:
        horse_ids = self.doc.xpath("//a[@data-test-selector='link-horseName']/@href")
        return [horse_id.split('/')[3] for horse_id in horse_ids]

    def get_ids_jockey(self) -> list[str]:
        jockey_ids = self.doc.xpath("//a[@data-test-selector='link-jockeyName']/@href")
        return [jockey_id.split('/')[3] for jockey_id in jockey_ids[::2]]

    def get_ids_owner(self) -> list[str]:
        owner_ids = self.doc.xpath("//a[@data-test-selector='link-silk']/@href")
        return [owner_id.split('/')[3] for owner_id in owner_ids]

    def get_ids_trainer(self) -> list[str]:
        trainer_ids = self.doc.xpath("//a[@data-test-selector='link-trainerName']/@href")
        return [trainer_id.split('/')[3] for trainer_id in trainer_ids[::2]]

    def get_names_horse(self) -> list[str]:
        horses = self.doc.xpath("//a[@data-test-selector='link-horseName']/text()")
        nationalities = self.get_nationalities()
        return [f'{clean_string(horse)} {nat}' for horse, nat in zip(horses, nationalities)]

    def get_names_jockey(self) -> list[str]:
        jockeys = self.doc.xpath("//a[@data-test-selector='link-jockeyName']/text()")
        return [clean_string(jock.strip()) for jock in jockeys[::3]]

    def get_names_owner(self) -> list[str]:
        owners = self.doc.xpath("//a[@data-test-selector='link-silk']/@href")
        return [owner.split('/')[4].replace('-', ' ').title() for owner in owners]

    def get_names_trainer(self) -> list[str]:
        trainers = self.doc.xpath("//a[@data-test-selector='link-trainerName']/text()")
        return [clean_string(trainer.strip()) for trainer in trainers[::2][::2]]

    def get_nationalities(self) -> list[str]:
        nats = self.doc.xpath("//span[@class='rp-horseTable__horse__country']/text()")
        return [(nat.strip() or '(GB)') for nat in nats]

    def get_num_runners(self) -> str:
        ran = find(self.doc, 'span', 'rp-raceInfo__value rp-raceInfo__value_black')
        return ran.replace('ran', '').strip()

    def get_numbers(self) -> list[str]:
        nums = self.doc.xpath("//span[@class='rp-horseTable__saddleClothNo']/text()")
        return [num.strip('.') for num in nums]

    def get_positions(self) -> list[str]:
        positions = self.doc.xpath("//span[@data-test-selector='text-horsePosition']/text()")
        del positions[1::2]
        positions = [pos.strip() for pos in positions]

        if len(positions) > 0 and positions[0] == 'VOI':
            raise VoidRaceError(f'VoidRaceError: {self.url}')

        return positions

    def get_prizemoney(self) -> list[str]:
        prizes = self.doc.xpath("//div[@data-test-selector='text-prizeMoney']/text()")
        prizes = [p.strip().replace(',', '').replace('£', '') for p in prizes]

        if prizes:
            prizes = prizes[1:]
        else:
            prizes = []

        positions: list[str] = self.runner_info.pos

        prizes.extend([''] * (len(positions) - len(prizes)))

        return ['' if p == 'DSQ' else prize for p, prize in zip(positions, prizes)]

    def get_race_class(self) -> str:
        classes = {
            'a': '1',
            'b': '2',
            'c': '3',
            'd': '4',
            'e': '5',
            'f': '6',
            'g': '6',
            'h': '7',
        }

        match = search(regex_class, self.race_info.race_name)

        if match:
            race_class = match.groups()[2].lower()
            if race_class in classes:
                return 'Class ' + classes[race_class]
            return 'Class ' + race_class

        if '(premier handicap)' in self.race_info.race_name:
            return 'Class 2'

        return ''

    def get_race_distances(self) -> tuple[str, str, str, str]:
        dist = find(self.doc, 'span', 'block-distanceInd')
        dist_y = find(self.doc, 'span', 'block-fullDistanceInd').strip('()')

        try:
            dist_f = distance_to_furlongs(dist)
        except ValueError:
            print('ERROR: distance_to_furlongs()')
            print('Race: ', self.url)
            sys.exit()

        dist_m = distance_to_metres(dist_y)

        if dist_m == 0:
            dist_m = round(dist_f * 201.168)

        dist_y = round(dist_m * 1.0936)
        dist_f = str(dist_f).replace('.0', '') + 'f'

        if self.race_info.region not in {'GB', 'IRE', 'USA', 'CAN'}:
            dist_m = float(dist_f.strip('f')) * 200

        return dist, str(int(dist_y)), dist_f, str(int(dist_m))

    def get_race_pattern(self) -> str:
        match = search(regex_group, self.race_info.race_name)

        if match:
            pattern = f'{match.groups()[1]} {match.groups()[4]}'.title()
            return pattern.title()

        if 'Forte Mile' in self.race_info.race_name and '(Group' in self.race_info.race_name:
            return 'Group 2'

        if any(x in self.race_info.race_name.lower() for x in {'listed race', '(listed'}):
            return 'Listed'

        return ''

    def get_race_type(self, code: str) -> str:
        race_type = ''
        race = self.race_info.race_name.lower()

        if code == 'flat' and 'national hunt flat' not in race:
            race_type = 'Flat'
        else:
            fences = find(self.doc, 'span', 'rp-raceTimeCourseName_hurdles')

            if 'hurdle' in fences.lower():
                race_type = 'Hurdle'
            elif 'fence' in fences.lower():
                race_type = 'Chase'

        if race_type == '':
            if int(self.race_info.dist_m) >= 2400:
                if any(x in race for x in {'national hunt flat', 'nh flat race', 'mares flat race'}):
                    race_type = 'NH Flat'
                if any(
                    x in race
                    for x in {'inh bumper', ' sales bumper', 'kepak flat race', 'i.n.h. flat race'}
                ):
                    race_type = 'NH Flat'
                if any(x in race for x in {' hurdle', '(hurdle)'}):
                    race_type = 'Hurdle'
                if any(
                    x in race
                    for x in {
                        ' chase',
                        '(chase)',
                        'steeplechase',
                        'steeple-chase',
                        'steeplchase',
                        'steepl-chase',
                    }
                ):
                    race_type = 'Chase'

        if race_type == '':
            race_type = 'Flat'

        return race_type

    def get_sexs(self, info: list[HtmlElement]) -> list[str]:
        sexs: list[str] = []

        for element in info:
            text_parts = (element.text or '').strip().split()

            if len(text_parts) == 1:
                sexs.append(text_parts[0].upper())
            elif len(text_parts) == 2:
                sexs.append(text_parts[1].upper())
            else:
                raise ValueError(
                    f'Unexpected sex format: {text_parts} (URL: {getattr(self, "url", "unknown")})'
                )

        return sexs

    def get_starting_prices(self) -> list[str]:
        sps = self.doc.xpath("//span[@class='rp-horseTable__horse__price']/text()")
        return [sp.replace('No Odds', '').strip() for sp in sps]

    def get_weights(self) -> tuple[list[str], list[str]]:
        stones = self.doc.xpath("//span[@data-ending='st']/text()")
        pounds = self.doc.xpath("//span[@data-ending='lb']/text()")

        weights = [f'{s}-{p}' for s, p in zip(stones, pounds)]
        lbs = [str(int(s) * 14 + int(p)) for s, p in zip(stones, pounds)]
        wgt = [w.strip() for w in weights]

        return wgt, lbs

    def get_winning_time(self) -> float | None:
        items = self.doc.xpath('//div[@class="rp-raceInfo"]/ul/li')
        if not items:
            raise ValueError(f'No race info found: {self.url}')

        spans = items[0].findall('.//span[@class="rp-raceInfo__value"]')
        if len(spans) not in (2, 3):
            raise ValueError(f'Unexpected number of time spans in {self.url}')

        raw_text = spans[-2].text or ''
        parts = raw_text.split('(')[0].split()

        if parts and parts[0] in {'0.0.00s', '0.00s'}:
            try:
                fast_by = raw_text.split('(')[1].lower()
                parts = fast_by.replace('fast by', '').strip(' )').split()
            except IndexError:
                return None

        if not parts or parts == ['standard', 'time']:
            return None

        try:
            if len(parts) > 1:
                minutes = float(parts[0].replace('m', ''))
                seconds = float(parts[1].rstrip('s'))
                total = minutes * 60 + seconds
            else:
                total = float(parts[0].rstrip('s'))
        except ValueError as e:
            raise ValueError(f'Invalid winning time in {self.url}: {parts}') from e

        return round(total, 2)

    def join_betfair_data(self, bsp_map: BSPMap):
        key = (self.race_info.region, self.race_info.date, self.race_info.off)
        bsp = bsp_map.get(key)

        if not bsp:
            return

        self.runner_info.set_bsp_list_width(len(self.runner_info.horse))

        for i, horse in enumerate(self.runner_info.horse):
            name = horse.split('(')[0].strip().lower()
            for row in bsp:
                if jarowinkler_similarity(name, row.horse) >= 0.77:
                    self.runner_info.bsp[i] = row.bsp or ''
                    self.runner_info.pre_min[i] = row.pre_min or ''
                    self.runner_info.pre_max[i] = row.pre_max or ''
                    self.runner_info.ip_min[i] = row.ip_min or ''
                    self.runner_info.ip_max[i] = row.ip_max or ''
                    self.runner_info.pre_vol[i] = row.pre_vol or ''
                    self.runner_info.ip_vol[i] = row.ip_vol or ''
                    break

    def parse_race_bands(self) -> tuple[str, str]:
        band = find(self.doc, 'span', 'rp-raceTimeCourseName_ratingBandAndAgesAllowed', property='class')
        bands = band.strip('()').split(',')

        band_age = ''
        band_rating = ''

        if len(bands) > 1:
            for x in bands:
                if 'yo' in x:
                    band_age = x.strip()
                elif '-' in x:
                    band_rating = x.strip()
        else:
            if 'yo' in band:
                band_age = band.strip()
            elif '-' in band:
                band_rating = band.strip()

        return band_age.strip('()'), band_rating

    def sex_restricted(self) -> str:
        race_name = self.race_info.race_name.lower()

        patterns = [
            (['entire colts & fillies', 'colts & fillies'], 'C & F'),
            (['fillies & mares', 'filles & mares'], 'F & M'),
            (['colts & geldings', 'colts/geldings', '(c & g)'], 'C & G'),
            (['(mares & geldings)'], 'M & G'),
            (['fillies'], 'F'),
            (['mares'], 'M'),
        ]

        for terms, result in patterns:
            if any(term in race_name for term in terms):
                return result

        return ''

    def time_to_seconds(self, times: list[str]) -> list[str]:
        def convert_time(time_str: str) -> str:
            if time_str == '-':
                return '-'
            try:
                mins, secs = time_str.split(':')
                total_seconds = (int(mins) * 60) + float(secs)
                return f'{total_seconds:.2f}'
            except ValueError:
                raise ValueError(f"Invalid time format: '{time_str}' from {self.url}")

        return [convert_time(t) for t in times]


def distance_to_decimal(dist: str):
    return (
        dist.strip()
        .replace('¼', '.25')
        .replace('½', '.5')
        .replace('¾', '.75')
        .replace('snk', '0.2')
        .replace('nk', '0.3')
        .replace('sht-hd', '0.1')
        .replace('shd', '0.1')
        .replace('hd', '0.2')
        .replace('nse', '0.05')
        .replace('dht', '0')
        .replace('dist', '30')
    )


def distance_to_furlongs(distance: str):
    dist = ''.join(
        [d.strip().replace('¼', '.25').replace('½', '.5').replace('¾', '.75') for d in distance]
    )

    if 'm' in dist:
        if len(dist) > 2:
            dist = int(dist.split('m')[0]) * 8 + float(dist.split('m')[1].strip('f'))
        else:
            dist = int(dist.split('m')[0]) * 8
    else:
        dist = dist.strip('f')

    return float(dist)


def distance_to_metres(distance: str) -> int:
    dist = distance.lower()
    metres = 0

    if 'm' in dist:
        metres += int(dist.split('m')[0]) * 1609.34

    if 'f' in dist:
        metres += int(dist.split('f')[0][-1]) * 201.168

    if 'yds' in dist:
        if 'f' in dist:
            metres += int(dist.split('f')[1].strip('yds')) * 0.914
        elif 'm' in dist:
            metres += int(dist.split('m')[1].strip('yds')) * 0.914

    return round(metres)


def fraction_to_decimal(fractions: list[str]) -> list[str]:
    decimal: list[str] = []

    for fraction in fractions:
        if fraction in {'', 'No Odds', '&'}:
            decimal.append('')
        elif fraction.lower() in {'evens', 'evs'}:
            decimal.append('2.00')
        else:
            num, den = fraction.split('/')
            decimal.append(f'{float(num) / float(den) + 1.00:.2f}')

    return decimal


def parse_time(date_time: str):
    time = datetime.fromisoformat(date_time).time()
    return f'{time.strftime("%H:%M")}'
