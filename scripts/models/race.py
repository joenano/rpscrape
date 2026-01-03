from dataclasses import dataclass, field


@dataclass
class RaceInfo:
    date: str = ''
    region: str = ''
    course_id: str = ''
    course: str = ''
    course_detail: str | None = None

    race_id: str = ''
    off: str = ''
    race_name: str = ''

    race_type: str = ''
    race_class: str = ''
    pattern: str = ''

    age_band: str = ''
    rating_band: str = ''
    sex_rest: str = ''

    dist: str = ''
    dist_f: str = ''
    dist_m: str = ''
    dist_y: str = ''

    going: str = ''
    surface: str = ''
    ran: str = ''


@dataclass
class RunnerInfo:
    num: list[str] = field(default_factory=list)
    pos: list[str] = field(default_factory=list)
    draw: list[str] = field(default_factory=list)
    ovr_btn: list[str] = field(default_factory=list)
    btn: list[str] = field(default_factory=list)
    horse_id: list[str] = field(default_factory=list)
    horse: list[str] = field(default_factory=list)
    age: list[str] = field(default_factory=list)
    sex: list[str] = field(default_factory=list)
    wgt: list[str] = field(default_factory=list)
    lbs: list[str] = field(default_factory=list)
    hg: list[str] = field(default_factory=list)
    time: list[str] = field(default_factory=list)
    secs: list[str] = field(default_factory=list)
    sp: list[str] = field(default_factory=list)
    dec: list[str] = field(default_factory=list)
    jockey_id: list[str] = field(default_factory=list)
    jockey: list[str] = field(default_factory=list)
    trainer_id: list[str] = field(default_factory=list)
    trainer: list[str] = field(default_factory=list)
    prize: list[str] = field(default_factory=list)
    ofr: list[str] = field(default_factory=list)
    rpr: list[str] = field(default_factory=list)
    ts: list[str] = field(default_factory=list)
    sire_id: list[str] = field(default_factory=list)
    sire: list[str] = field(default_factory=list)
    dam_id: list[str] = field(default_factory=list)
    dam: list[str] = field(default_factory=list)
    damsire_id: list[str] = field(default_factory=list)
    damsire: list[str] = field(default_factory=list)
    owner_id: list[str] = field(default_factory=list)
    owner: list[str] = field(default_factory=list)
    silk_url: list[str] = field(default_factory=list)
    comment: list[str] = field(default_factory=list)

    bsp: list[str] = field(default_factory=list)
    wap: list[str] = field(default_factory=list)
    morning_wap: list[str] = field(default_factory=list)
    pre_min: list[str] = field(default_factory=list)
    pre_max: list[str] = field(default_factory=list)
    ip_min: list[str] = field(default_factory=list)
    ip_max: list[str] = field(default_factory=list)
    morning_vol: list[str] = field(default_factory=list)
    pre_vol: list[str] = field(default_factory=list)
    ip_vol: list[str] = field(default_factory=list)

    def set_bsp_list_width(self, n: int):
        self.bsp = [''] * n
        self.wap = [''] * n
        self.morning_wap = [''] * n
        self.pre_min = [''] * n
        self.pre_max = [''] * n
        self.ip_min = [''] * n
        self.ip_max = [''] * n
        self.morning_vol = [''] * n
        self.pre_vol = [''] * n
        self.ip_vol = [''] * n
