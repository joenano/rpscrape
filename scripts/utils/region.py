from orjson import loads

_regions = loads(open('../courses/_regions', 'r').read())


def get_region(course_id: str) -> str:
    courses = loads(open('../courses/_courses', 'r').read())
    courses.pop('all')

    for region, course in courses.items():
        for _id in course.keys():
            if _id == course_id:
                return region.upper()

    return ''


def print_region(code: str, region: str):
    print(f'\tCODE: {code: <4} |  {region}')


def print_regions():
    for code, region in _regions.items():
        print_region(code, region)


def region_search(term: str):
    for code, region in _regions.items():
        if term.lower() in region.lower():
            print_region(code, region)


def valid_region(code: str) -> bool:
    return code in _regions
