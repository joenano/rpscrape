import os
import sys

from datetime import date, datetime
from argparse import ArgumentParser

from utils.region import print_regions, valid_region, region_search
from utils.date import check_date, get_dates, parse_years, valid_years
from utils.course import course_name, course_search, courses, print_courses, valid_course

type ArgDict = (
    dict[str, str | None | list[str] | list[date] | list[tuple[str, str | None]]]
    | dict[str, str | list[date]]
)

HELP_TEXT = (
    'Run:\n'
    '\t./rpscrape.py\n'
    '\t[rpscrape]> [region|course] [year|range] [flat|jumps]\n\n'
    '\tRegions have alphabetic codes\n'
    '\tCourses have numeric codes\n\n'
    'Examples:\n'
    '\t[rpscrape]> ire 1999 flat\n'
    '\t[rpscrape]> gb 2015-2018 jumps\n'
    '\t[rpscrape]> 533 1998-2018 flat\n'
)


OPTIONS_TEXT = (
    f'\t{"regions": <20} List all available region codes\n'
    f'\t{"regions [search]": <20} Search for specific region code\n\n'
    f'\t{"courses": <20} List all courses\n'
    f'\t{"courses [search]": <20} Search for specific course\n'
    f'\t{"courses [region]": <20} List courses in region - e.g courses ire\n\n'
    f'\t{"-d, date": <20} Scrape race by date - e.g -d 2019/12/17 gb\n\n'
    f'\t{"help": <20} Show help\n'
    f'\t{"options": <20} Show options\n'
    f'\t{"cls, clear": <20} Clear screen\n'
    f'\t{"q, quit, exit": <20} Quit\n'
)


INFO = {
    'date': 'Date or date range. Format YYYY/MM/DD - e.g 2008/01/05 or 2020/01/19-2020/05/01',
    'course': 'Course code. 1 to 4 digit code - e.g 20',
    'region': 'Region code. 2 or 3 letter e.g ire',
    'year': 'Year or range of years. Format YYYY - e.g 2018 or 2019-2020',
    'type': 'Race type flat|jumps',
}


ERROR = {
    'arg_len': 'Error: Too many arguments.\n\tUsage:\n\t\t[rpscrape]> [region|course] [year|range] [flat|jumps]',
    'incompatible': 'Arguments incompatible.\n',
    'incompatible_course': 'Choose course or region, not both.',
    'invalid_c_or_r': 'Invalid course or region',
    'invalid_course': 'Invalid Course code.\n\nExamples:\n\t\t-c 20\n\t\t-c 1083',
    'invalid_date': 'Invalid date. Format:\n\t\t-d YYYY/MM/DD\n\nExamples:\n\t\t-d 2020/01/19\n\t\t2020/01/19-2020/01/29',
    'invalid_region': 'Invalid Region code. \n\nExamples:\n\t\t-r gb\n\t\t-r ire',
    'invalid_region_int': 'Invalid Region code. \n\nExamples:\n\t\t2020/01/19 gb\n\t\t2021/07/11 ire',
    'invalid_type': 'Invalid type.\n\nMust be either flat or jumps.\n\nExamples:\n\t\t-t flat\n\t\t-t jumps',
    'invalid_year': 'Invalid year.\n\nFormat:\n\t\tYYYY\n\nExamples:\n\t\t-y 2015\n\t\t-y 2012-2017',
    'invalid_year_int': 'Invalid year. Must be in range 1988-',
}


class ArgParser:
    def __init__(self):
        self.dates: list[date] = []
        self.tracks: list[tuple[str, str]] = []
        self.years: list[str] = []
        self.parser: ArgumentParser = ArgumentParser()
        self.add_arguments()

    def add_arguments(self):
        _ = self.parser.add_argument('-d', '--date', metavar='', type=str, help=INFO['date'])
        _ = self.parser.add_argument('-c', '--course', metavar='', type=str, help=INFO['course'])
        _ = self.parser.add_argument('-r', '--region', metavar='', type=str, help=INFO['region'])
        _ = self.parser.add_argument('-y', '--year', metavar='', type=str, help=INFO['year'])
        _ = self.parser.add_argument('-t', '--type', metavar='', type=str, help=INFO['type'])

    def parse_args(self, arg_list: list[str]):
        args = self.parser.parse_args(args=arg_list)

        if args.date:
            if any([args.course, args.year]):
                self.parser.error(ERROR['incompatible'])

            if not check_date(args.date):
                self.parser.error(ERROR['invalid_date'])

            self.dates = get_dates(args.date)

        if args.course and args.region:
            self.parser.error(ERROR['incompatible'] + ERROR['incompatible_course'])

        if args.region:
            if not valid_region(args.region):
                self.parser.error(ERROR['invalid_region'])

            self.tracks = [course for course in courses(args.region)]
        else:
            args.region = 'all'

        if args.course:
            course = course_name(args.course)

            if not course or not valid_course(args.course):
                self.parser.error(ERROR['invalid_course'])

            self.tracks = [(args.course, course)]

        if args.year:
            years = parse_years(args.year)

            if not years or not valid_years(years):
                self.parser.error(ERROR['invalid_year'])

            self.years = years

        if args.type and args.type not in {'flat', 'jumps'}:
            self.parser.error(ERROR['invalid_type'])

        if not args.type:
            args.type = ''

        return args

    def parse_args_interactive(self, args: list[str]) -> ArgDict:
        if not args:
            return {}

        cmd = args[0].lower()

        if len(args) == 1:
            self.handle_option(cmd)
            return {}

        if cmd in {'courses', 'regions'}:
            search_term = ' '.join(args[1:])
            region = args[1] if len(args) > 1 else ''
            self.search(cmd, search_term, region)
            return {}

        parsed: ArgDict = {}

        if cmd in {'-d', 'date', 'dates'}:
            return self.parse_date_request(args)

        if len(args) != 3:
            print(ERROR['arg_len'])
            return {}

        target, year_str, type_code = args

        years = self.parse_year(year_str)
        if not years:
            return {}
        parsed['years'] = years

        race_type = self.get_racing_type(type_code)
        if not race_type:
            print(ERROR['invalid_type'])
            return {}
        parsed['type'] = race_type

        if valid_region(target):
            parsed['folder_name'] = f'regions/{target}'
            parsed['file_name'] = year_str
            parsed['tracks'] = [course for course in courses(target)]
        elif valid_course(target):
            course = course_name(target)
            parsed['folder_name'] = f'courses/{course}'
            parsed['file_name'] = year_str
            parsed['tracks'] = [(target, course)]
        else:
            print(ERROR['invalid_c_or_r'])
            return {}

        return parsed

    def get_racing_type(self, code: str) -> str | None:
        mapping = {'j': 'jumps', 'f': 'flat'}
        key = code.lower().lstrip('-')[0]
        return mapping.get(key, None)

    def handle_option(self, option: str):
        dispatch = {
            'help': lambda: print(HELP_TEXT),
            'options': lambda: print(OPTIONS_TEXT),
            'opt': lambda: print(OPTIONS_TEXT),
            '?': lambda: print(OPTIONS_TEXT),
            'clear': lambda: os.system('cls' if os.name == 'nt' else 'clear'),
            'cls': lambda: os.system('cls' if os.name == 'nt' else 'clear'),
            'clr': lambda: os.system('cls' if os.name == 'nt' else 'clear'),
            'q': lambda: sys.exit(),
            'quit': lambda: sys.exit(),
            'exit': lambda: sys.exit(),
            'regions': print_regions,
            'courses': print_courses,
        }

        action = dispatch.get(option)
        if action:
            _ = action()

    def parse_date_request(self, args: list[str]) -> ArgDict:
        parsed: dict[str, str | list[date]] = {}

        if len(args) < 2:
            print(ERROR['invalid_date'])
            return {}

        date_input = args[1]

        if not check_date(date_input):
            print(ERROR['invalid_date'])
            return {}

        parsed['dates'] = get_dates(date_input)
        parsed['folder_name'] = 'dates/'
        parsed['file_name'] = date_input.replace('/', '_')
        parsed['type'] = ''

        if len(args) >= 3:
            region = args[2]
            if valid_region(region):
                parsed['region'] = region
                parsed['folder_name'] += region
            else:
                print(ERROR['invalid_region_int'])
                return {}

        if len(args) >= 4:
            race_type = self.get_racing_type(args[3])
            if race_type:
                parsed['type'] = race_type
            else:
                print(ERROR['invalid_type'])
                return {}

        return parsed

    def parse_year(self, year: str) -> list[str] | None:
        years = parse_years(year)
        current_year = str(datetime.today().year)

        if not years or not valid_years(years):
            print(ERROR['invalid_year_int'] + current_year)
            return None

        return years

    def search(self, search_type: str, search_term: str, region: str):
        if search_type == 'regions':
            region_search(search_term)
        else:
            if valid_region(region):
                print_courses(region)
            else:
                course_search(search_term)
