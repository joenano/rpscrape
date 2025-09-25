import re


def clean_string(s: str) -> str:
    if not s:
        return ''
    s = s.strip()
    for char in [',', '"', "'", '\x80', '\\x80']:
        s = s.replace(char, '')
    s = re.sub(r'\s+', ' ', s)
    s = s.replace('((', '(')
    return s


def normalize_name(name: str, title_case: bool = True) -> str:
    if not name:
        return ''
    name = name.split('(')[0].strip()
    name = re.sub(r'\s+(i|ii)$', '', name, flags=re.IGNORECASE)
    name = name.replace('.', ' ').replace("'", '')
    name = re.sub(r'\s+', ' ', name)
    if title_case:
        name = name.lower().title()
    return name


def normalize_name_region(name: str, region: str) -> str:
    name = normalize_name(name)
    if region == 'AUS':
        if '.' in name:
            name = name.split('.', 1)[1].strip()
    return name
