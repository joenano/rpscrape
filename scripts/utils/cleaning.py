from re import search, sub, IGNORECASE

RE_CLASS = r'(\(|\s)[Cc]lass (\d|[A-Ha-h])(\)|\s)'
RE_GROUP = r'(\(|\s)(?:[Gg]rade|[Gg]roup) (\d|[A-Ca-c]|I*)(\)|\s)'

RE_PATTERNS: list[tuple[str, str]] = [
    ('class', RE_CLASS),
    ('group', RE_GROUP),
    ('grade', RE_GROUP),
]


def clean_string(s: str) -> str:
    if not s:
        return ''

    s = s.strip()

    for char in [',', '"', "'", '\x80', '\\x80']:
        s = s.replace(char, '')

    s = sub(r'\(\s*\)+', '', s)
    s = sub(r'\s+', ' ', s)

    return s.strip()


def clean_race(race_name: str) -> str:
    name = race_name.strip()
    lname = name.lower()

    if 'Forte Mile Guaranteed Minimum Value £60000 (Group' in name:
        return 'Sandown Mile'

    for key, regex in RE_PATTERNS:
        if key in lname:
            if match := search(regex, name):
                return clean_string(name.replace(match.group(), '').strip())

    if 'listed' in lname:
        return clean_string(name.replace('Listed Race', '').replace('(Listed)', '').strip())

    return clean_string(name)


# def normalise_name(name: str, title_case: bool = True) -> str:
#     if not name:
#         return ''
#     name = name.split('(')[0].strip()
#     name = sub(r'\s+(i|ii)$', '', name, flags=IGNORECASE)
#     name = name.replace('.', ' ').replace("'", '')
#     name = sub(r'\s+', ' ', name)
#     if title_case:
#         name = name.lower().title()
#     return name


def strip_row(row: list[str]) -> list[str]:
    return [x.strip() for x in row]
