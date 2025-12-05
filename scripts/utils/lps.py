from utils.going import FLAT_GROUPS, JUMP_GROUPS


def get_lps_scale(race_type: str, going: str) -> float:
    if not going:
        return 6.0 if race_type.lower() == 'flat' else 5.0

    going_lower = going.lower()

    if race_type.lower() == 'flat':
        default = 6.0
        groups = FLAT_GROUPS
    else:
        groups = JUMP_GROUPS
        default = 5.0

    for scale, keywords in groups.items():
        if any(g in going_lower for g in keywords):
            return scale

    return default
