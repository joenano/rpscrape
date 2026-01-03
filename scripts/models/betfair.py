from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime
from orjson import dumps
from typing import Any

from utils.cleaning import clean_string

type BSPMap = dict[tuple[str, str, str], list[BSP]]


@dataclass
class BSP:
    date: str
    region: str
    off: str
    horse: str
    bsp: str | None
    wap: str | None
    morning_wap: str | None
    pre_min: str | None
    pre_max: str | None
    ip_min: str | None
    ip_max: str | None
    morning_vol: str | None
    pre_vol: str | None
    ip_vol: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return dumps(self.to_dict()).decode('utf-8')

    @classmethod
    def from_csv(cls, record: dict[str, str]) -> BSP | None:
        try:
            return cls(
                date=record['date'],
                region=record['region'],
                off=record['off'],
                horse=record['horse'],
                bsp=record.get('bsp') or None,
                wap=record.get('wap') or None,
                morning_wap=record.get('morning_wap') or None,
                pre_min=record.get('pre_min'),
                pre_max=record.get('pre_max'),
                ip_min=record.get('ip_min'),
                ip_max=record.get('ip_max'),
                morning_vol=record.get('morning_vol'),
                pre_vol=record.get('pre_vol'),
                ip_vol=record.get('ip_vol'),
            )
        except KeyError:
            return None

    @classmethod
    def from_record(cls, record: dict[str, str], region: str) -> BSP | None:
        event_dt = record.get('event_dt', '')
        if not event_dt:
            return None

        parsed = parse_date_time(event_dt)
        if not parsed:
            return None
        dt, off = parsed

        region_val = 'GB' if region == 'UK' else region
        horse = clean_name(record.get('selection_name', ''), region_val)

        return cls(
            date=dt,
            region=region_val,
            off=off,
            horse=horse.lower(),
            bsp=f'{float(record["bsp"]):.2f}' if record.get('bsp') else None,
            wap=f'{float(record["ppwap"]):.2f}' if record.get('ppwap') else None,
            morning_wap=f'{float(record["morningwap"]):.2f}' if record.get('morningwap') else None,
            pre_max=record.get('ppmax'),
            pre_min=record.get('ppmin'),
            ip_max=record.get('ipmax'),
            ip_min=record.get('ipmin'),
            morning_vol=record.get('morningtradedvol'),
            pre_vol=record.get('pptradedvol'),
            ip_vol=record.get('iptradedvol'),
        )


def clean_name(name: str, region: str) -> str:
    cleaned = name.split('(')[0].lower()
    cleaned = clean_string(cleaned)

    if region == 'AUS':
        dot_pos = cleaned.find('.')
        if dot_pos != -1:
            cleaned = cleaned[dot_pos + 1 :].strip()

    return cleaned


def parse_date_time(s: str) -> tuple[str, str] | None:
    if not s:
        return None
    try:
        dt = datetime.strptime(s, '%d-%m-%Y %H:%M')
    except ValueError as _:
        return None
    return dt.date().strftime('%Y-%m-%d'), dt.strftime('%H:%M')
