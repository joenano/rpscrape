from collections.abc import Generator
from orjson import loads


def courses(code: str = 'all') -> Generator[tuple[str, str]]:
    courses = loads(open('../courses/_courses', 'r').read())

    for id, course in courses[code].items():
        yield id, course


def course_name(code: str) -> str:
    if code.isalpha():
        return code
    for course in courses():
        if course[0] == code:
            return course[1].replace(' ', '-')

    return ''


def course_search(term: str):
    for course in courses():
        if term.lower() in course[1].lower():
            print_course(course[0], course[1])


def print_course(code: str, course: str):
    print(f'\tCODE: {code: <4} |  {course}')


def print_courses(code: str = 'all'):
    for course in courses(code):
        print_course(course[0], course[1])


def valid_course(code: str) -> bool:
    return code in {course[0] for course in courses()}


def valid_meeting(course: str):
    invalid = ['free to air', 'worldwide stakes', '(arab)']
    return all([x not in course for x in invalid])
