from collections.abc import Iterator
from orjson import loads


_courses = loads(open('../courses/_courses', 'r').read())


def courses(code: str = 'all') -> Iterator[tuple[str, str]]:
    for course_id, course in _courses[code].items():
        yield course_id, course


def course_name(code: str) -> str:
    if code.isalpha():
        return code
    for course in courses():
        if course[0] == code:
            return course[1].replace(' ', '-')

    return ''


def course_search(term: str):
    term = term.lower()
    for course_id, course_name in _courses['all'].items():
        if term in course_name.lower():
            print_course(course_id, course_name)


def print_course(code: str, course: str):
    print(f'\tCODE: {code: <4} |  {course}')


def print_courses(code: str = 'all'):
    for course_id, course_name in _courses[code].items():
        print_course(course_id, course_name)


def valid_course(code: str) -> bool:
    return any(code in region for region in _courses.values())


def valid_meeting(course: str):
    invalid = ['free to air', 'worldwide stakes', '(arab)']
    return all([x not in course for x in invalid])
