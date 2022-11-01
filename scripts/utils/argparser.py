import os
import sys

from argparse import ArgumentParser

from utils.course import *
from utils.date import *
from utils.region import *


help = (
    f'Run:\n'
    f'\t./rpscrape.py\n'
    f'\t[rpscrape]> [region|course] [year|range] [flat|jumps]\n\n'
    f'\tRegions have alphabetic codes\n'
    f'\tCourses have numeric codes\n\n'
    f'Examples:\n'
    f'\t[rpscrape]> ire 1999 flat\n'
    f'\t[rpscrape]> gb 2015-2018 jumps\n'
    f'\t[rpscrape]> 533 1998-2018 flat\n'
)


options = (
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
    'invalid_year_int': 'Invalid year. Must be in range 1988-'
}


class ArgParser:

    def __init__(self):
        self.dates = []
        self.tracks = []
        self.years = []
        self.parser = ArgumentParser()
        self.add_arguments()

    def add_arguments(self):
        self.parser.add_argument('-d', '--date',    metavar='', type=str, help=INFO['date'])
        self.parser.add_argument('-c', '--course',  metavar='', type=str, help=INFO['course'])
        self.parser.add_argument('-r', '--region',  metavar='', type=str, help=INFO['region'])
        self.parser.add_argument('-y', '--year',    metavar='', type=str, help=INFO['year'])
        self.parser.add_argument('-t', '--type',    metavar='', type=str, help=INFO['type'])

    def parse_args(self, arg_list):
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
            if not valid_course(args.course):
                self.parser.error(ERROR['invalid_course'])

            self.tracks = [(args.course, course_name(args.course))]

        if args.year:
            self.years = parse_years(args.year)

            if not self.years or not valid_years(self.years):
                self.parser.error(ERROR['invalid_year'])

        if args.type and args.type not in {'flat', 'jumps'}:
            self.parser.error(ERROR['invalid_type'])

        if not args.type:
            args.type = ''

        return args

    def parse_args_interactive(self, args):
        if len(args) == 1:
            self.opts(args[0])
            return

        if args[0] in {'courses', 'regions'}:
            self.search(args[0], ' '.join(args[1:]), args[1])
            return

        parsed = {}

        if args[0] in {'-d', 'date', 'dates'}:
            parsed = self.parse_date_request(args)
        else:
            if len(args) > 3:
                print(ERROR['arg_len'])

            if args[0] not in {'courses', 'regions'} and len(args) != 3:
                return

            year = args[1]
            parsed['years'] = self.parse_year(year)
            parsed['type'] = self.get_racing_type(args[2])

            if not parsed['type']:
                print(ERROR['invalid_type'])

            elif valid_region(args[0]):
                region = args[0]
                parsed['folder_name'] = f'regions/{region}'
                parsed['file_name'] = year
                parsed['tracks'] = [course for course in courses(region)]

            elif valid_course(args[0]):
                course_id = args[0]
                course = course_name(course_id)
                parsed['folder_name'] = f'courses/{course}'
                parsed['file_name'] = year
                parsed['tracks'] = [(course_id, course)]

            else:
                print(ERROR['invalid_c_or_r'])

        return parsed

    def get_racing_type(self, code):
        if code in {'j', '-j', 'jump', 'jumps'}:
            return 'jumps'
        if code in {'f', '-f', 'flat'}:
            return 'flat'
        return ''

    def opts(self, option):
        if option == 'help':
            print(help)
        elif option in {'options', 'opt', '?'}:
            print(options)
        elif option in {'clear', 'cls', 'clr'}:
            os.system('cls' if os.name == 'nt' else 'clear')
        elif option in {'q', 'quit', 'exit'}:
            sys.exit()
        elif option == 'regions':
            print_regions()
        elif option == 'courses':
            print_courses()

    def parse_date_request(self, args):
        parsed = {}

        if check_date(args[1]):
            parsed['dates'] = get_dates(args[1])
            parsed['folder_name'] = 'dates/'
            parsed['file_name'] = args[1].replace('/', '_')
            parsed['type'] = ''

            if len(args) > 2:
                if valid_region(args[2]):
                    parsed['region'] = args[2]
                    parsed['folder_name'] += args[2]
                else:
                    print(ERROR['invalid_region_int'])
                    return {}

            if len(args) > 3:
                parsed['type'] = self.get_racing_type(args[3])
        else:
            print(ERROR['invalid_date'])

        return parsed

    def parse_year(self, year):
        years = parse_years(year)
        current_year = str(datetime.today().year)

        if not valid_years(years):
            print(ERROR['invalid_year_int'] + current_year)

        return years

    def search(self, search_type, search_term, region):
        if search_type == 'regions':
            region_search(search_term)
        else:
            if valid_region(region):
                print_courses(region)
            else:
                course_search(search_term)
