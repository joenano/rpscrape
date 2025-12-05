GOING = {
    'AW': ('Slow', 'Standard', 'Standard To Fast', 'Standard To Slow'),
    'DIRT': ('Fast', 'Muddy', 'Sloppy'),
    'TURF': (
        'Firm',
        'Good',
        'Good To Firm',
        'Good To Soft',
        'Good To Yielding',
        'Hard',
        'Heavy',
        'Holding',
        'Soft',
        'Soft To Heavy',
        'Very Soft',
        'Yielding',
        'Yielding To Soft',
    ),
}

FLAT_GROUPS = {
    6.0: ('good', 'firm', 'standard', 'fast', 'hard', 'slow', 'sloppy'),
    5.0: (
        'soft',
        'heavy',
        'yielding',
        'holding',
    ),
}

JUMP_GROUPS = {
    5.0: ('firm', 'standard', 'hard', 'fast', 'good'),
    4.0: ('soft', 'heavy', 'yielding', 'slow', 'holding'),
}


def get_surface(going: str) -> str:
    if going in GOING['AW']:
        return 'AW'
    if going in GOING['DIRT']:
        return 'Dirt'
    if going in GOING['TURF']:
        return 'Turf'

    return ''
