#!/usr/bin/env python3
#
# Scrapes results and saves them in csv format

import os
import sys
import json
import requests
from lxml import html
from re import search
from time import sleep


class Completer:

    def __init__(self, options):
        self.options = sorted(options)

    def complete(self, text, state):
        if state == 0:
            if text:
                self.matches = [s for s in self.options if s and s.startswith(text)]
            else:
                self.matches = self.options[:]
        try: 
            return self.matches[state]
        except IndexError:
            return None


def show_options(opt='help'):
    opts =  '\n'.join([
            '       regions              List all available region codes',
            '       regions [search]     Search for specific country code',
            '',
            '       courses              List all courses',
            '       courses [search]     Search for specific course',
            '       courses [region]     List courses in region - e.g courses ire'
            ])

    if opt == 'help':
        print(
            '\n'.join([
            '  Usage:',
            '       ~$ ./rpscrape.py'
            '       [rpscrape]> [region|course] [year|range] [flat|jumps]',
            '',
            '       Regions have alphabetic codes.',
            '       Courses have numeric codes.',
            '',
            '  Examples:',
            '       [rpscrape]> ire 1999 flat',
            '       [rpscrape]> gb 2015-2018 jumps',
            '       [rpscrape]> 533 1998-2018 flat',
            '',
            '  Options:',
            '{}'.format(opts),
            '',
            '  More info:',
            '       help           Show help',
            '       options        Show options',
            '       cls, clear     Clear screen',
            '       q, quit        Quit',
            ''
        ]))
    else:
        print(opts)


def get_courses(region='all'):
    with open(f'../courses/{region}_course_ids', 'r') as courses:
        for course in courses:
            yield (course.split('-')[0].strip(), ' '.join(course.split('-')[1::]).strip())
         

def get_course_name(code):
    if code.isalpha():
        return code
    for course in get_courses():
        if course[0] == code:
            return course[1].replace('()', '').replace(' ', '-')


def course_search(term):
    for course in get_courses():
        if term.lower() in course[1].lower():
            print_course(course[0], course[1])


def print_course(key, course):
    if len(key) == 5:
        print(f'     CODE: {key}| {course}')
    elif len(key) == 4:
        print(f'     CODE: {key} | {course}')
    elif len(key) == 3:
        print(f'     CODE: {key}  | {course}')
    elif len(key) == 2:
        print(f'     CODE: {key}   | {course}')
    else:
        print(f'     CODE: {key}    | {course}')


def print_courses(region='all'):
    for course in get_courses(region):
        print_course(course[0], course[1])


def validate_course(course_id):
    return course_id in [course[0] for course in get_courses()]


def x_y():
    from base64 import b64decode
    return b64decode('aHR0cHM6Ly93d3cucmFjaW5ncG9zdC5jb206NDQzL3Byb2ZpbGUvY291cnNlL2ZpbHRlci9yZXN1bHRz')\
    .decode('utf-8'), b64decode('aHR0cHM6Ly93d3cucmFjaW5ncG9zdC5jb20vcmVzdWx0cw==').decode('utf-8')


def get_regions():
    with open('../courses/_countries', 'r') as regions:
        return json.load(regions)


def region_search(term):
    for key, region in get_regions().items():
        if term.lower() in region.lower():
            print_region(key, region)


def print_region(key, region):
    if len(key) == 3:
        print(f'     CODE: {key} | {region}')
    else:
        print(f'     CODE: {key}  | {region}')


def print_regions():
    for key, region in get_regions().items():
        print_region(key, region)


def validate_region(region):
    return region in get_regions().keys()


def validate_years(years):
    if years:
        return all(year.isdigit() and int(year) > 1995 and int(year) < 2019 for year in years)
    else:
        return False


def fraction_to_decimal(fractional_odds):
	decimal_odds = []
	for fraction in fractional_odds:
		if(fraction.lower() == 'evens'):
			decimal_odds.append('2.00')
		else:
			decimal_odds.append('{0:.2f}'.format(float(fraction.split('/')[0]) / float(fraction.split('/')[1]) + 1.00))

	return decimal_odds


def get_races(tracks, names, years, code, xy):
    races = []
    for track, name in zip(tracks, names):
        for year in years:
            r = requests.get(f'{xy[0]}/{track}/{year}/{code}/all-races', headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code == 200:
                try:
                    results = r.json()
                    if results['data']['principleRaceResults'] == None:
                        print(f'No {code} race data for {get_course_name(track)} in {year}.')
                    else:
                        for result in results['data']['principleRaceResults']:
                            races.append(f'{xy[1]}/{track}/{name}/{result["raceDatetime"][:10]}/{result["raceInstanceUid"]}')
                except:
                    pass
            else:
                print(f'Unable to access races from {get_course_name(track)} in {year}')
    return races


def calculate_times(win_time, dist_btn, going, code, course):
    times = []
    if code == 'flat':
        if 'Firm' in going or 'Standard' in going:
            if 'southwell' in course.lower():
                lps_scale = 5
            else:
                lps_scale = 6
        elif 'Good' in going:
            if 'Soft' in going or 'Yielding'in going:
                lps_scale = 5.5
            else:
                lps_scale = 6
        elif 'Soft' in going or 'Heavy' in going or 'Yielding' in going:
            lps_scale = 5
    else:
        if 'Firm' in going or 'Standard' in going:
            if 'southwell' in course.lower():
                lps_scale = 4
            else:
                lps_scale = 5
        elif 'Good' in going:
            if 'Soft' in going or 'Yielding'in going:
                lps_scale = 4.5
            else:
                lps_scale = 5
        elif 'Soft' in going or 'Heavy' or 'Yielding' in going:
            lps_scale = 4
    
    for dist in dist_btn:
        try:
            time = (win_time + (float(dist) / lps_scale))
            times.append('{}:{:2.2f}'.format(int(time // 60), time % 60))
        except ValueError:
            times.append('')

    return times
                

def clean(data):
    return [d.strip().replace('–', '') for d in data]


def scrape_races(races, target, years, code):
    if not os.path.exists('../data'):
        os.makedirs('../data')

    with open(f'../data/{target.lower()}-{years}_{code}.csv', 'w') as csv:
        csv.write(('"date","course","time","race_name","class","band","distance","going","pos","draw","btn","name","sp","dec"'
            '"age","weight","gear","fin_time","jockey","trainer","or","ts","rpr","prize","sire","dam","damsire","comment"\n'))

        for race in races:
            r = requests.get(race, headers={'User-Agent': 'Mozilla/5.0'})
            while r.status_code == 403:
                sleep(5)
                r = requests.get(race, headers={'User-Agent': 'Mozilla/5.0'})

            doc = html.fromstring(r.content)

            course_name = race.split('/')[5]
            try:
                date = doc.xpath("//span[@data-test-selector='text-raceDate']/text()")[0]
            except IndexError:
                date = ''
            try:
                r_time = doc.xpath("//span[@data-test-selector='text-raceTime']/text()")[0]
            except IndexError:
                r_time = ''

            try:
                race = doc.xpath("//h2[@class='rp-raceTimeCourseName__title']/text()")[0].strip().strip('\n').replace(',', ' ').replace('"', '')
            except IndexError:
                race = ''

            if '(Premier Handicap)' in race:
                race_class = 'Class 2'
            elif '(Group' in race:
                race_class = search('(\(Grou..)\w+', race).group(0).strip('(')
                race = race.replace(f'({race_class})', '')
            elif '(Grade' in race:
                race_class = search('(\(Grad..)\w+', race).group(0).strip('(')
                race = race.replace(f'({race_class})', '') 
            elif '(Listed Race)' in race:
                race_class = 'Listed'
                race = race.replace('(Listed Race)', '')
            else:
                try:
                    race_class = doc.xpath("//span[@class='rp-raceTimeCourseName_class']/text()")[0].strip().strip('()')
                except:
                    race_class = ''

            if race_class == '' and 'Maiden' in race:
                race_class = 'Class 4'

            try:
                band = doc.xpath("//span[@class='rp-raceTimeCourseName_ratingBandAndAgesAllowed']/text()")[0].strip().strip('()')
            except:
                band = ''
            if ',' in band:
                split_band = band.split(',')
                race_class = split_band[0]
                band = split_band[1]
            if ('(Entire Colts & Fillies)') in race:
                band = band + ' Colts & Fillies'
                race = race.replace('(Entire Colts & Fillies)', '')
            elif '(Fillies & Mares)' in race:
                band = band + ' Fillies & Mares'
                race = race.replace('(Fillies & Mares)', '')
            elif '(Fillies)' in race or 'Fillies' in race:
                band = band + ' Fillies'
                race = race.replace('(Fillies)', '')
            elif '(Colts & Geldings)' in race or '(C & G)' in race:
                band = band + ' Colts & Geldings'
                race = race.replace('(Colts & Geldings)', '').replace('(C & G)', '')

            try:
                distance = doc.xpath("//span[@class='rp-raceTimeCourseName_distance']/text()")[0].strip()
            except IndexError:
                distance = ''
            dist = ''.join([d.strip().replace('¼', '.25').replace('½', '.5').replace('¾', '.75') for d in distance])

            try:
                going = doc.xpath("//span[@class='rp-raceTimeCourseName_condition']/text()")[0].strip()
            except IndexError:
                going =''

            pedigree = doc.xpath("//a[@class='ui-profileLink ui-link ui-link_marked js-popupLink']/text()")
            del pedigree[-3]

            sires, dams, damsires = [], [], []

            for i in range(0, len(pedigree) - 3, 3):
                sires.append(pedigree[i].strip())
                dams.append(pedigree[i + 1].strip())
                damsires.append(pedigree[i + 2].strip().strip('()'))

            coms = doc.xpath("//tr[@class='rp-horseTable__commentRow ng-cloak']/td/text()")
            com = [x.strip().replace('  ', '').replace(',', ' -') for x in coms]
            possy = doc.xpath("//span[@data-test-selector='text-horsePosition']/text()")
            del possy[1::2]
            pos = [x.strip() for x in possy]
            prizes = doc.xpath("//div[@data-test-selector='text-prizeMoney']/text()")
            prize = [p.strip().replace(",", '') for p in prizes]
            try:
                del prize[0]
                for i in range(len(pos) - len(prize)):
                    prize.append('')
            except IndexError:
                prize = ['' for x in range(len(pos))]    
            draw = clean(doc.xpath("//sup[@class='rp-horseTable__pos__draw']/text()"))
            draw = [d.strip("()") for d in draw]
            beaten = doc.xpath("//span[@class='rp-horseTable__pos__length']/span/text()")
            del beaten[1::2]
            btn = [b.strip().strip("[]").replace('¼', '.25').replace('½', '.5').replace('¾', '.75').replace('nk', '0.33')\
                    .replace('shd', '0.2').replace('hd', '0.25').replace('nse', '0.1').replace('dht', '0') for b in beaten]
            btn.insert(0, '0')
            if len(btn) < len(pos):
                btn.extend(['' for x in range(len(pos) - len(btn))])

            name = clean(doc.xpath("//a[@data-test-selector='link-horseName']/text()"))
            sps = clean(doc.xpath("//span[@class='rp-horseTable__horse__price']/text()"))
            jock = clean(doc.xpath("//a[@data-test-selector='link-jockeyName']/text()"))
            del jock[::2]
            trainer = clean(doc.xpath("//a[@data-test-selector='link-trainerName']/text()"))
            del trainer[::2]
            age = clean(doc.xpath("//td[@data-test-selector='horse-age']/text()"))
            _or = clean(doc.xpath("//td[@data-ending='OR']/text()"))
            ts = clean(doc.xpath("//td[@data-ending='TS']/text()"))
            rpr = clean(doc.xpath("//td[@data-ending='RPR']/text()"))
            st = doc.xpath("//span[@data-ending='st']/text()")
            lb = doc.xpath("//span[@data-ending='lb']/text()")
            wgt = [a.strip() +'-' + b.strip() for a, b in zip(st, lb)]
            headgear = doc.xpath("//td[contains(@class, 'rp-horseTable__wgt')]")
            gear = []
            for h in headgear:
                span = h.find('span[@class="rp-horseTable__headGear"]')
                if span is not None:
                    gear.append(span.text)
                else:
                    gear.append('')

            winning_time = clean(doc.xpath('//span[@class="rp-raceInfo__value"]/text()')[0].split('('))[0].split()
            if len(winning_time) > 1:
                win_time = float(winning_time[0].replace('m', '')) * 60 + float(winning_time[1].strip('s'))
            else:
                win_time = float(winning_time[0].strip('s'))
            
            times = calculate_times(win_time, btn, going, code, course_name)
            dec = fraction_to_decimal([sp.strip('F').strip('J').strip('C') for sp in sps])

            for p, pr, dr, bt, n, sp, dc, time, j, tr, a, o, t, rp, w, g, c, sire, dam, damsire in \
            zip(pos, prize, draw, btn, name, sps, dec, times, jock, trainer, age, _or, ts, rpr, wgt, gear, com, sires, dams, damsires):
                csv.write((f'{date},{course_name},{r_time},{race},{race_class},{band},{dist},{going},{p},{dr},{bt},{n},{sp},'
                            f'{dc},{a},{w},{g},{time},{j},{tr},{o},{t},{rp},{pr},{sire},{dam},{damsire},{c}\n'))

        print(f'\nFinished scraping. {target.lower()}-{years}_{code}.csv saved in rpscrape/data')


def parse_args(args=sys.argv):
    if len(args) == 1:
        if 'help' in args or 'options' in args:
            show_options(args[0])
        elif 'clear' in args:
            os.system('cls' if os.name == 'nt' else 'clear')
        elif 'quit' in args or 'q' in args or 'exit' in args:
            sys.exit()
        elif 'regions' in args:
            print_regions()
        elif 'courses' in args:
            print_courses()
    elif len(args) == 2:
        if args[0] == 'regions':
            region_search(args[1])
        elif args[0] == 'courses':
            if validate_region(args[1]):
                print_courses(args[1])
            else:
                course_search(args[1])
    elif len(args) == 3:
        if validate_region(args[0]):
            region = args[0]
        elif validate_course(args[0]):
            course = args[0]
        else:
            return print('Invalid course or region.')

        if '-' in args[1]:
            try:
                years = [str(x) for x in range(int(args[1].split('-')[0]), int(args[1].split('-')[1]) + 1)]
            except ValueError:
                return print('Invalid year, must be in range 1996-2018.')
        else:
            years = [args[1]]
        if not validate_years(years):
            return print('Invalid year, must be in range 1996-2018.')

        if 'jumps' in args or 'jump' in args or '-j' in args:
            code = 'jumps'
        elif 'flat' in args or '-f' in args:
            code = 'flat'
        else:
            return print('Invalid racing code. -f, flat or -j, jumps.')

        if 'region' in locals():
            tracks = [course[0] for course in get_courses(region)]
            names = [get_course_name(track) for track in tracks]
            scrape_target = region
            print(f'Scraping {code} results from {scrape_target} in {args[1]}...')
        else:
            tracks = [course]
            names = [get_course_name(course)]
            scrape_target = course
            print(f'Scraping {code} results from {get_course_name(scrape_target)} in {args[1]}...')

        races = get_races(tracks, names, years, code, x_y())
        scrape_races(races, get_course_name(scrape_target), args[1], code)
    else:
        show_options()


def main():
    if len(sys.argv) > 1:
        sys.exit(show_options())

    try:
        import readline
        completions = Completer(["courses", "regions", "options", "help", "quit", "exit", "clear", "flat", "jumps"])
        readline.set_completer(completions.complete)
        readline.parse_and_bind('tab: complete')
    except ModuleNotFoundError: # windows
        pass

    while True:
        args = input('[rpscrape]> ').lower().strip()
        parse_args([arg.strip() for arg in args.split()])


if __name__ == '__main__':
    main()
