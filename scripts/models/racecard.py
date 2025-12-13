from dataclasses import dataclass, field, asdict
from typing import Any
from orjson import dumps


@dataclass
class Runner:
    age: int | None = None
    breeder: str | None = None
    breeder_id: int | None = None
    claim: int | None = None
    colour: str | None = None
    comment: str | None = None
    dam: str | None = None
    dam_id: int | None = None
    dam_region: str | None = None
    damsire: str | None = None
    damsire_id: int | None = None
    damsire_region: str | None = None
    dob: str | None = None
    draw: int | None = None
    form: str | None = None
    headgear: str | None = None
    headgear_first: bool | None = None
    horse_id: int | None = None
    jockey: str | None = None
    jockey_allowance: int | None = None
    jockey_id: int | None = None
    last_run: int | None = None
    lbs: int | None = None
    medical: list[dict[str, Any]] | None = field(default_factory=list)
    name: str | None = None
    non_runner: bool | None = None
    number: int | None = None
    ofr: int | None = None
    owner: str | None = None
    owner_id: int | None = None
    prev_owners: list[dict[str, Any]] = field(default_factory=list)
    prev_trainers: list[dict[str, Any]] = field(default_factory=list)
    profile: str | None = None
    quotes: list[dict[str, Any]] = field(default_factory=list)
    region: str | None = None
    reserve: bool | None = None
    rpr: int | None = None
    sex: str | None = None
    sex_code: str | None = None
    silk_path: str | None = None
    silk_url: str | None = None
    sire: str | None = None
    sire_id: int | None = None
    sire_region: str | None = None
    spotlight: str | None = None
    stable_tour: list[dict[str, Any]] | None = field(default_factory=list)
    stats: dict[str, dict[str, Any] | None] | None = None
    trainer: str | None = None
    trainer_14_days: dict[str, Any] | None = None
    trainer_id: int | None = None
    trainer_location: str | None = None
    trainer_rtf: str | None = None
    ts: int | None = None
    wind_surgery_first: bool | None = None
    wind_surgery_second: bool | None = None


@dataclass
class Racecard:
    age_band: str | None = None
    course: str | None = None
    course_id: int | None = None
    date: str | None = None
    distance: str | None = None
    distance_f: float | None = None
    distance_y: int | None = None
    distance_round: str | None = None
    field_size: int | None = None
    going: str | None = None
    handicap: bool | None = None
    href: str | None = None
    off_time: str | None = None
    pattern: str | None = None
    prize: str | None = None
    race_class: str | int | None = None
    race_id: int | None = None
    race_name: str | None = None
    race_type: str | None = None
    rating_band: str | None = None
    region: str | None = None
    runners: list[Runner] = field(default_factory=list)
    surface: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return dumps(self.to_dict()).decode('utf-8')
