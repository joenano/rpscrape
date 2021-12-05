import sys

from re import search, sub

from utils.pedigree import Pedigree

from utils.date import convert_date
from utils.lxml_funcs import find, xpath
from utils.region import get_region


regex_class = '(\(|\s)(C|c)lass (\d|[A-Ha-h])(\)|\s)'
regex_group = '(\(|\s)((G|g)rade|(G|g)roup) (\d|[A-Ca-c]|I*)(\)|\s)'


class VoidRaceError(Exception):
    pass


class Race:

    def __init__(self, document, code, fields):
        self.url = document[0]
        self.doc = document[1]
        self.race_info = {}
        self.runner_info = {}

        url_split = self.url.split('/')
        
        self.race_info['code'] = code
        self.race_info['date'] = convert_date(url_split[6])
        self.race_info['course'] = self.get_course(url_split[5])
        self.race_info['course_id'] = url_split[4]
        self.race_info['region'] = get_region(url_split[4])
        self.race_info['race_id'] = url_split[7]

        self.race_info['going'] = find(self.doc, 'span', 'rp-raceTimeCourseName_condition', property='class')
        self.race_info['off'] = find(self.doc, 'span', 'text-raceTime')
        self.race_info['race_name'] = find(self.doc, 'h2', 'rp-raceTimeCourseName__title', property='class')
        self.race_info['class'] = find(self.doc, 'span', 'rp-raceTimeCourseName_class', property='class').strip('()')
        self.race_info['race_name'] = self.clean(self.race_info['race_name'])
        
        if self.race_info['class'] == '':
            self.race_info['class'] = self.get_race_class()

        self.race_info['pattern'] = self.get_race_pattern()
        self.race_info['race_name'] = self.clean_race_name(self.race_info['race_name'])
        self.race_info['age_band'], self.race_info['rating_band'] = self.parse_race_bands()

        if self.race_info['class'] == '' and self.race_info['rating_band'] != '':
            self.race_info['class'] = self.get_class_from_rating()

        self.race_info['sex_rest'] = self.sex_restricted()
        self.race_info['dist'], self.race_info['dist_y'],\
        self.race_info['dist_f'], self.race_info['dist_m'] = self.get_race_distances()
        self.race_info['type'] = self.get_race_type()
        self.race_info['ran'] = self.get_num_runners()

        pedigree = Pedigree(xpath(self.doc, 'tr', 'block-pedigreeInfoFullResults', fn='/td'))

        self.runner_info['sire_id'] = pedigree.id_sires
        self.runner_info['sire'] = pedigree.sires
        self.runner_info['dam_id'] = pedigree.id_dams
        self.runner_info['dam'] = pedigree.dams
        self.runner_info['damsire_id'] = pedigree.id_damsires
        self.runner_info['damsire'] = pedigree.damsires
        self.runner_info['sex'] = self.get_sexs(pedigree.pedigrees)
        self.runner_info['comment'] = self.get_comments()
        self.runner_info['pos'] = self.get_positions()     
        self.runner_info['prize'] = self.get_prizemoney()
        self.runner_info['draw'] = self.get_draws()
        self.runner_info['ovr_btn'], self.runner_info['btn'] = self.get_distance_btn()
        self.runner_info['sp'] = self.get_starting_prices()
        self.runner_info['dec'] = self.get_decimal_odds()
        self.runner_info['num'] = self.get_numbers()
        
        if not self.race_info['ran']:
            self.race_info['ran'] = len(self.runner_info['num'])
        else:
            self.race_info['ran'] = int(self.race_info['ran'])
        
        self.runner_info['age'] = self.get_horse_ages()
        self.runner_info['horse'] = self.get_names_horse()
        self.runner_info['horse_id'] = self.get_ids_horse()
        self.runner_info['jockey'] = self.get_names_jockey()
        self.runner_info['jockey_id'] = self.get_ids_jockey()
        self.runner_info['trainer'] = self.get_names_trainer()
        self.runner_info['trainer_id'] = self.get_ids_trainer()
        self.runner_info['owner'] = self.get_names_owner()
        self.runner_info['owner_id'] = self.get_ids_owner()
        self.runner_info['hg'] = self.get_headgear()

        self.runner_info['wgt'], self.runner_info['lbs'] = self.get_weights()
        self.runner_info['or'] = xpath(self.doc, 'td', 'OR', 'data-ending', fn='/text()')
        self.runner_info['rpr'] = xpath(self.doc, 'td', 'RPR', 'data-ending', fn='/text()')
        self.runner_info['ts'] = xpath(self.doc, 'td', 'TS', 'data-ending', fn='/text()')
        self.runner_info['silk_url'] = xpath(self.doc, 'img', 'rp-horseTable__silk', 'class', fn='/@src')

        self.runner_info['time'] = self.get_finishing_times()
        self.runner_info['secs'] = self.time_to_seconds(self.runner_info['time'])
        
        self.clean_non_completions()
        
        self.csv_data = self.create_csv_data(fields)
        
    def calculate_times(self, win_time, dist_btn, going, course, race_type):
        times = []

        if race_type.lower() == 'flat':
            if going == '':
                lps_scale = 6
            elif going in {'firm', 'standard', 'fast', 'hard', 'slow', 'sloppy'}:
                if 'southwell' in course.lower():
                    lps_scale = 5
                else:
                    lps_scale = 6
            elif 'good' in going:
                if going in {'soft', 'yielding'}:
                    lps_scale = 5.5
                else:
                    lps_scale = 6
            elif going in {'soft', 'heavy', 'yielding', 'holding'}:
                lps_scale = 5
            else:
                lps_scale = 5
        else:
            if going == '':
                lps_scale = 5
            elif going in {'firm', 'standard', 'hard', 'fast'}:
                if 'southwell' in course.lower():
                    lps_scale = 4
                else:
                    lps_scale = 5
            elif 'good' in going:
                if going in {'soft', 'yielding'}:
                    lps_scale = 4.5
                else:
                    lps_scale = 5
            elif going in {'soft', 'heavy', 'yielding', 'slow', 'holding'}:
                lps_scale = 4
            else:
                lps_scale = 5

        for dist in dist_btn:
            try:
                time = (win_time + (float(dist) / lps_scale))
                times.append('{}:{:2.2f}'.format(int(time // 60), time % 60))
            except ValueError:
                times.append('')

        return times
                
    def clean(self, string):
        return string.strip().replace(',', ' ').replace('"', '').replace('\x80', '')\
            .replace('\\x80', '').replace('  ', ' ').replace("'", '')
            
    def clean_non_completions(self):
        for i, pos in enumerate(self.runner_info['pos']):
            if not pos.isnumeric() and pos != 'DSQ':
                self.runner_info['time'][i] = '-'
                self.runner_info['secs'][i] = '-'
                self.runner_info['ovr_btn'][i] = '-'
                self.runner_info['btn'][i] = '-'

    def clean_race_name(self, race_name):
        clean_name = lambda race, x: race.replace(x, '').strip()

        if 'class' in race_name.lower():
            match = search(regex_class, race_name)
            if match: return clean_name(race_name, match.group())

        if 'Forte Mile Guaranteed Minimum Value £60000 (Group' in race_name:
            return 'Sandown Mile'

        if any(x in race_name.lower() for x in {'group', 'grade'}):
            match = search(regex_group, race_name)
            if match: return clean_name(race_name, match.group())

        if 'Listed' in race_name:
            return race_name.replace('Listed Race', '').replace('(Listed)', '')

        return self.clean(race_name)
    
    def create_csv_data(self, fields):
        csv_race_info = ''
        
        for field in fields:
            if field in self.race_info:
                csv_race_info += f'{self.race_info[field]},'
            
        runner_info = []
        
        for field in fields:
            if field in self.runner_info:
                runner_info.append(self.runner_info[field])
        
        csv = []
        
        for row in zip(*runner_info):
            csv.append(csv_race_info + ','.join(str(x) for x in row))
        
        return csv

    def distance_to_decimal(self, dist):
        return (
            dist.strip().replace('¼', '.25').replace('½', '.5').replace('¾', '.75').replace('snk', '0.2')
            .replace('nk', '0.3').replace('sht-hd', '0.1').replace('shd', '0.1').replace('hd', '0.2')
            .replace('nse', '0.05').replace('dht', '0').replace('dist', '30')
        )

    def distance_to_furlongs(self, distance):
        dist = ''.join([d.strip().replace('¼', '.25').replace('½', '.5').replace('¾', '.75') for d in distance])

        if 'm' in dist:
            if len(dist) > 2:
                dist = int(dist.split('m')[0]) * 8 + float(dist.split('m')[1].strip('f'))
            else:
                dist = int(dist.split('m')[0]) * 8
        else:
            dist = dist.strip('f')

        return float(dist)

    def distance_to_metres(self, distance):
        dist = distance.lower()
        metres = 0

        if 'm' in dist:
            metres += int(dist.split('m')[0]) * 1609.34

        if 'f' in dist:
            metres += int(dist.split('f')[0][-1]) * 201.168

        if 'yds' in dist:
            if 'f' in dist:
                metres += int(dist.split('f')[1].strip('yds')) * .914
            elif 'm' in dist:
                metres += int(dist.split('m')[1].strip('yds')) * .914

        return round(metres)
    
    def fraction_to_decimal(self, fractions):
        decimal = []
        for fraction in fractions:
            if fraction in {'', 'No Odds', '&'}:
                decimal.append('')
            elif fraction.lower() in {'evens', 'evs'}:
                decimal.append('2.00')
            else:
                num, den = fraction.split('/')
                decimal.append(f'{float(num) / float(den) + 1.00:.2f}')

        return decimal

    def get_class_from_rating(self):
        try:
            upper_rating = int(self.race_ratings.split('-')[1])
        except:
            return ''
        
        race_class = ''

        if self.race_info['code'] == 'flat':
            if upper_rating >= 100:
                race_class = 'Class 2'
            if upper_rating >= 90:
                race_class = 'Class 3'
            if upper_rating >= 80:
                race_class = 'Class 4'
            if upper_rating >= 70:
                race_class = 'Class 5'
            if upper_rating >= 60:
                race_class = 'Class 6'
            if upper_rating >= 40:
                race_class = 'Class 7'
        else:
            if upper_rating >= 140:
                race_class = 'Class 2'
            if upper_rating >= 120:
                race_class = 'Class 3'
            if upper_rating >= 100:
                race_class = 'Class 4'
            if upper_rating >= 85:
                race_class = 'Class 5'

        return race_class

    def get_comments(self):
        clean_comment = lambda x: x.strip().replace('  ', '').replace(',', ' -').replace('\n', ' ').replace('\r', '')
        coms = self.doc.xpath("//tr[@class='rp-horseTable__commentRow ng-cloak']/td/text()")
        return [clean_comment(com) for com in coms]
    
    def get_course(self, course_url):
        course = find(self.doc, 'h1', 'RC-courseHeader__name')
        if course == '':
            try:
                course = self.doc.xpath("//a[contains(@class, 'rp-raceTimeCourseName__name')]/text()")[0].strip()
            except IndexError:
                course = course_url.title() 
        
        return course
        
    def get_decimal_odds(self):
        odds = [sub('(F|J|C)', '', sp) for sp in self.runner_info['sp']]
        return self.fraction_to_decimal(odds)

    def get_distance_btn(self):
        btn = []
        ovr_btn = []
        
        for x in xpath(self.doc, 'span', 'rp-horseTable__pos__length', 'class'):
            distances = x.findall('span')

            if len(distances) == 2:
                if distances[0].text is None:
                    btn.append('0')
                else:
                    btn.append(distances[0].text)
                if distances[1].text is None:
                    ovr_btn.append('0')
                else:
                    ovr_btn.append(distances[1].text.strip('[]'))
            else:
                if distances[0].text is None:
                    btn.append('0')
                    ovr_btn.append('0')
                else:
                    if distances[0].text == 'dht':
                        btn.append(distances[0].text)
                        try:
                            ovr_btn.append(ovr_btn[-1])
                        except IndexError:
                            ovr_btn.append(btn[-1])
                    else:
                        btn.append(distances[0].text)
                        ovr_btn.append(distances[0].text)

        try:
            btn = [self.distance_to_decimal(b) for b in btn]
        except AttributeError:
            print('btn error: ', self.url)
            sys.exit()

        ovr_btn = [self.distance_to_decimal(b) for b in ovr_btn]

        num_runners = len(self.runner_info['pos'])

        if len(ovr_btn) < num_runners:
            ovr_btn.extend(['' for x in range(num_runners - len(ovr_btn))])

        if len(btn) < num_runners:
            btn.extend(['' for x in range(num_runners - len(btn))])
            
        return ovr_btn, btn

    def get_draws(self):
        draws = xpath(self.doc, 'sup', 'rp-horseTable__pos__draw','class', fn='/text()')
        return [draw.replace(u'\xa0', u' ').strip().strip("()") for draw in draws]
    
    def get_finishing_times(self):
        # adjust overall distance beaten when margins under a quarter length not accounted for
        # for instance when 2 horses finish with a head between them 4 lengths behind winner
        # both horses are recorded as being beaten 4 lengths overall by RP
        
        btn_adj = []

        for btn, ovr_btn in zip(self.runner_info['btn'], self.runner_info['ovr_btn']):
            try:
                if float(ovr_btn) > 1 and float(btn) < .25:
                    btn_adj.append(str(float(btn) + float(ovr_btn)))
                else:
                    btn_adj.append(ovr_btn)
            except ValueError:
                btn_adj.append(ovr_btn)
                
        winning_time = self.get_winning_time()
        
        if winning_time is None:
            return ['-' for i in range(self.race_info['ran'])]
        
        return self.calculate_times(
            winning_time,
            btn_adj,
            self.race_info['going'],
            self.race_info['course'],
            self.race_info['type']
        )
    
    def get_headgear(self):
        headgear = []
        
        for horse in self.doc.xpath("//td[contains(@class, 'rp-horseTable__wgt')]"):
            hg = horse.find('span[@class="rp-horseTable__headGear"]')
            if hg is not None:
                try:
                    headgear.append(headgear.text + hg[1].text.strip())
                except:
                    headgear.append(hg.text)
            else:
                headgear.append('')
        
        return headgear
    
    def get_horse_ages(self):
        ages = xpath(self.doc, 'td', 'horse-age', fn='/text()')
        return [age.strip() for age in ages] 
    
    def get_ids_horse(self):
        horse_ids = xpath(self.doc, 'a', 'link-horseName', fn='/@href')
        return [horse_id.split('/')[3] for horse_id in horse_ids]
    
    def get_ids_jockey(self):
        jockey_ids = xpath(self.doc, 'a', 'link-jockeyName', fn='/@href')
        return [jockey_id.split('/')[3] for jockey_id in jockey_ids[::2]]
    
    def get_ids_owner(self):
        owner_ids = self.doc.xpath("//a[@data-test-selector='link-silk']/@href")
        return [owner_id.split('/')[3] for owner_id in owner_ids]
    
    def get_ids_trainer(self):
        trainer_ids = xpath(self.doc, 'a', 'link-trainerName', fn='/@href')
        return [trainer_id.split('/')[3] for trainer_id in trainer_ids[::2]]
    
    def get_names_horse(self):
        horses = xpath(self.doc, 'a', 'link-horseName', fn='/text()')
        
        joined = []
        
        for horse, nat in zip(horses, self.get_nationaliies()):
            joined.append(f"{self.clean(horse)} {nat}")
            
        return joined
    
    def get_names_jockey(self):
        jockeys = xpath(self.doc, 'a', 'link-jockeyName', fn='/text()')
        return [self.clean(jock.strip()) for jock in jockeys[::2]]
    
    def get_names_owner(self):
        owners = self.doc.xpath("//a[@data-test-selector='link-silk']/@href")
        return [owner.split('/')[4].replace('-', ' ').title() for owner in owners]
    
    def get_names_trainer(self):
        trainers = xpath(self.doc, 'a', 'link-trainerName', fn='/text()')
        return [self.clean(trainer.strip()) for trainer in trainers[::2][::2]]
    
    def get_nationaliies(self):
        nats = xpath(self.doc, 'span', 'rp-horseTable__horse__country', 'class', fn='/text()')
        nationalities = []
        
        for nat in nats:
            if nat.strip() == '':
                nationalities.append('(GB)')
            else:
                nationalities.append(nat.strip())
        
        return nationalities
    
    def get_num_runners(self):
        ran = find(self.doc, 'span', 'rp-raceInfo__value rp-raceInfo__value_black')

        if ran is not None:
            return ran.replace('ran', '').strip()
        
        return None
    
    def get_numbers(self):
        nums = xpath(self.doc, 'span', 'rp-horseTable__saddleClothNo', 'class', fn='/text()')
        return [num.strip('.') for num in nums]

    def get_positions(self):
        positions = xpath(self.doc, 'span', 'text-horsePosition', fn='/text()')
        del positions[1::2]
        positions = [pos.strip() for pos in positions]
        
        try:        
            if positions[0] == 'VOI':
                raise VoidRaceError
        except:
            print(self.url)
            sys.exit()

        return positions
    
    def get_prizemoney(self):
        prizes = xpath(self.doc, 'div', 'text-prizeMoney', fn='/text()')
        prize = [p.strip().replace(",", '').replace('£', '') for p in prizes]
        pos = self.runner_info['pos']

        try:
            del prize[0]
            [prize.append('') for i in range(len(pos) - len(prize))]
        except IndexError:
            prize = ['' for i in range(len(pos))]

        for i, p in enumerate(pos):
            if p == 'DSQ':
                prize.insert(i, '')
                prize.pop()

        return prize

    def get_race_class(self):
        classes = {
            'a': '1', 'b': '2', 'c': '3', 'd': '4', 'e': '5', 'f': '6', 'g': '6', 'h': '7',
        }

        match = search(regex_class, self.race_info['race_name'])

        if match:
            race_class = match.groups()[2].lower()
            if race_class in classes:
                return 'Class ' + classes[race_class]
            return 'Class ' + race_class

        if '(premier handicap)' in self.race_info['race_name']:
            return 'Class 2'

        return ''

    def get_race_distances(self):
        dist = find(self.doc, 'span', 'block-distanceInd')
        dist_y = find(self.doc, 'span', 'block-fullDistanceInd').strip('()')

        try:
            dist_f = self.distance_to_furlongs(dist)
        except ValueError:
            print('ERROR: distance_to_furlongs()')
            print('Race: ', self.url)
            sys.exit()

        dist_m = self.distance_to_metres(dist_y)

        if dist_m == 0:
            dist_m = round(dist_f * 201.168)

        dist_y = round(dist_m * 1.0936)
        dist_f = str(dist_f).replace('.0', '') + 'f'

        if self.race_info['region'] not in {'GB', 'IRE', 'USA', 'CAN'}:
            dist_m = float(dist_f.strip('f')) * 200

        return dist, dist_y, dist_f, dist_m

    def get_race_pattern(self):
        match = search(regex_group, self.race_info['race_name'])

        if match:
            pattern = f'{match.groups()[1]} {match.groups()[4]}'.title()
            return pattern.title()

        if 'Forte Mile' in self.race_info['race_name'] and '(Group' in self.race_info['race_name']:
            return 'Group 2'

        if any(x in self.race_info['race_name'].lower() for x in {'listed race', '(listed'}):
            return 'Listed'
        
        return ''

    def get_race_type(self):
        race_type = ''
        race = self.race_info['race_name'].lower()

        if self.race_info['code'] == 'flat' and 'national hunt flat' not in race:
            race_type = 'Flat'
        else:
            fences = find(self.doc, 'span', 'rp-raceTimeCourseName_hurdles')

            if 'hurdle' in fences.lower():
                race_type = 'Hurdle'
            elif 'fence' in fences.lower():
                race_type = 'Chase'

        if race_type == '':
            if self.race_info['dist_m'] >= 2400:
                if any(x in race for x in {'national hunt flat', 'nh flat race', 'mares flat race'}):
                    race_type = 'NH Flat'
                if any(x in race for x in {'inh bumper', ' sales bumper', 'kepak flat race', 'i.n.h. flat race'}):
                    race_type = 'NH Flat'
                if any(x in race for x in {' hurdle', '(hurdle)'}):
                    race_type = 'Hurdle'
                if any(x in race for x in {' chase', '(chase)', 'steeplechase', 'steeple-chase', 'steeplchase', 'steepl-chase'}):
                    race_type = 'Chase'

        if race_type == '':
            race_type = 'Flat'

        return race_type

    def get_sexs(self, info):
        sexs = []
        for x in info:
            info_sex = x.text.strip().split()
            if len(info_sex) == 2:
                sexs.append(info_sex[1].upper())
            elif len(info_sex) == 1:
                sexs.append(info_sex[0].upper())
            else:
                print('Sex error: ', info_sex)
                print(self.url)
                sys.exit()

        return sexs
    
    def get_starting_prices(self):
        sps = xpath(self.doc, 'span', 'rp-horseTable__horse__price', 'class', fn='/text()')
        return [sp.replace('No Odds', '').strip() for sp in sps]
    
    def get_weights(self):
        st = xpath(self.doc, 'span', 'st', 'data-ending', fn='/text()')
        lb = xpath(self.doc, 'span', 'lb', 'data-ending', fn='/text()')
        
        wgt = [f'{s}-{l}' for s, l in zip(st, lb)]
        lbs = [int(s) * 14 + int(l) for s, l in zip(st, lb)]
        
        return wgt, lbs
        
    def get_winning_time(self):
        result_info = self.doc.xpath('//div[@class="rp-raceInfo"]/ul/li')[0]
        time_info = result_info.findall('.//span[@class="rp-raceInfo__value"]')
        
        n = len(time_info)
        
        if n not in {2, 3}:
            print('Winning Time Error: ' + self.url)
            sys.exit()
            
        winning_time = time_info[n-2].text.split('(')[0].split()
        
        if winning_time[0] in {'0.0.00s', '0.00s'}:
            try:
                fast_by = time_info[n-2].text.split("(")[1].lower()
                winning_time = fast_by.replace('fast by', '').strip().strip(')').split()
            except IndexError:
                winning_time = None
                
        if winning_time is None or winning_time == ['standard', 'time']:
            return None
        
        if len(winning_time) > 1:
            try:
                winning_time = float(winning_time[0].replace("m", '')) * 60 + float(winning_time[1].strip("s"))
                winning_time = round(winning_time, 2)
            except ValueError:
                print('Winning Time Error: ', self.url)
                sys.exit()
        else:
            try:
                winning_time = float(winning_time[0].strip("s"))
                winning_time = round(winning_time, 2)
            except ValueError:
                print('Winning Time Error: ', self.url)
                sys.exit()
                
        return winning_time
    
    def parse_race_bands(self):
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
            
    def sex_restricted(self):
        if any(x in self.race_info['race_name'] for x in {'entire colts & fillies', 'colts & fillies'}):
            return 'C & F'
        elif any(x in self.race_info['race_name'] for x in {'Fillies & Mares', 'Filles & Mares'}):
            return 'F & M'
        elif any(x in self.race_info['race_name'] for x in {'Fillies'}):
            return 'F'
        elif any(x in self.race_info['race_name'] for x in {'Colts & Geldings', 'Colts/Geldings', '(C & G)'}):
            return 'C & G'
        elif '(Mares & Geldings)' in self.race_info['race_name']:
            return 'M & G'
        elif 'Mares' in self.race_info['race_name']:
            return 'M'
        else:
            return ''
        
    def time_to_seconds(self, times):
        seconds = []

        for time in times:
            if time == '-':
                seconds.append('-')
            else:
                try:
                    mins, secs = time.split(':')
                    _secs = (int(mins) * 60) + float(secs)
                    seconds.append(f'{_secs:.2f}')
                except ValueError:
                    print('TimeToSeconds Error: ', self.url)
                    sys.exit()

        return seconds
