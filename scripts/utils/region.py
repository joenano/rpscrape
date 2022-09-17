from orjson import loads


def get_region(course_id):
    courses = loads(open('../courses/_courses', 'r').read())
    courses.pop('all')

    for region, course in courses.items():
        for _id in course.keys():
            if _id == course_id:
                return region.upper()


def print_region(code, region):
    print(f'\tCODE: {code: <4} |  {region}')


def print_regions():
    for code, region in regions().items():
        print_region(code, region)


def regions():
    return loads(open('../courses/_regions', 'r').read())


def region_search(term):
    for code, region in regions().items():
        if term.lower() in region.lower():
            print_region(code, region)


def valid_region(code):
    return code in regions().keys()
