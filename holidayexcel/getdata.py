import datetime as dtm
from collections.abc import Collection, Iterable
from pprint import pprint
from typing import Any

import httpx

from holidayexcel.enums import HolidayType, StateCode
from holidayexcel.holidays import BaseHoliday, PublicHoliday, SchoolHoliday


def get_json_data(holiday_type: HolidayType, year: int) -> Any:
    url = (
        "https://ferien-api.de/api/v1/holidays"
        if holiday_type is HolidayType.SCHOOL
        else f"https://feiertage-api.de/api/?jahr={year}"
    )
    response = httpx.get(url)
    response.raise_for_status()  # raises an exception if the request failed

    return response.json()


def _get_allowed_state_codes(
    state_code: StateCode | Collection[StateCode] | None,
) -> Collection[StateCode]:
    if state_code is None:
        return set(*StateCode)
    if isinstance(state_code, StateCode):
        return {state_code, StateCode.NATIONAL}
    return set(state_code) | {StateCode.NATIONAL}


def get_public_holidays(
    year: int | None = None, state_code: StateCode | Collection[StateCode] | None = None
) -> Iterable[PublicHoliday]:
    allowed_state_codes = _get_allowed_state_codes(state_code)
    effective_year = year or dtm.date.today().year

    for state, entries in get_json_data(
        holiday_type=HolidayType.PUBLIC, year=effective_year
    ).items():
        for name, entry in entries.items():
            holiday = PublicHoliday.de_json(state_code=state, data=entry, name=name)
            if holiday.state_code in allowed_state_codes and holiday.year == effective_year:
                pprint(holiday)
                yield holiday


def get_school_holidays(
    year: int | None = None, state_code: StateCode | Collection[StateCode] | None = None
) -> Iterable[SchoolHoliday]:
    allowed_state_codes = _get_allowed_state_codes(state_code)
    effective_year = year or dtm.date.today().year

    for entry in get_json_data(holiday_type=HolidayType.SCHOOL, year=effective_year):
        holiday = SchoolHoliday.de_json(entry)
        if holiday.state_code in allowed_state_codes and holiday.year == effective_year:
            pprint(holiday)
            yield holiday


def get_all_holidays(
    year: int | None = None, state_code: StateCode | Collection[StateCode] | None = None
) -> Iterable[BaseHoliday]:
    yield from get_public_holidays(year=year, state_code=state_code)
    yield from get_school_holidays(year=year, state_code=state_code)
