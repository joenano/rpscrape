from json import load


def get_region(course_id):
    courses = load(open('../courses/_courses', 'r'))
    courses.pop('all')

    for region, course in courses.items():
        for id in course.keys():
            if id == course_id:
                return region.upper()


def print_region(code, region):
    print(f'\tCODE: {code: <4} |  {region}')


def print_regions():
    for code, region in regions().items():
        print_region(code, region)
        

def regions():
    return load(open('../courses/_regions', 'r'))


def region_search(term):
    for code, region in regions().items():
        if term.lower() in region.lower():
            print_region(code, region)


def valid_region(code):
    return code in regions().keys()
