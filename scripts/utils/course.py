from orjson import loads


def courses(code='all'):
    courses = loads(open('../courses/_courses', 'r').read())
    
    for id, course in courses[code].items():
        yield id, course
        
        
def course_name(code):
    if code.isalpha():
        return code
    for course in courses():
        if course[0] == code:
            return course[1].replace(' ', '-')


def course_search(term):
    for course in courses():
        if term.lower() in course[1].lower():
            print_course(course[0], course[1])


def print_course(code, course):
    print(f'\tCODE: {code: <4} |  {course}')


def print_courses(code='all'):
    for course in courses(code):
        print_course(course[0], course[1])


def valid_course(code):
    return code in {course[0] for course in courses()}
        