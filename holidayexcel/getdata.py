import datetime as dtm
from collections.abc import Iterable
from typing import Any

import httpx

from holidayexcel.enums import HolidayType, StateCode
from holidayexcel.holidays import PublicHoliday, SchoolHoliday


def get_json_data(holiday_type: HolidayType, year: int) -> Any:
    url = (
        "https://ferien-api.de/api/v1/holidays"
        if holiday_type is HolidayType.SCHOOL
        else f"https://feiertage-api.de/api/?jahr={year}"
    )
    response = httpx.get(url)
    response.raise_for_status()  # raises an exception if the request failed

    return response.json()


def get_public_holidays(year: int | None = None) -> Iterable[PublicHoliday]:
    effective_year = year or dtm.date.today().year

    for state, entries in get_json_data(
        holiday_type=HolidayType.PUBLIC, year=effective_year
    ).items():
        for name, entry in entries.items():
            if (
                holiday := PublicHoliday.de_json(state_code=state, data=entry, name=name)
            ).year == effective_year:
                yield holiday


def get_school_holidays(year: int | None = None) -> Iterable[SchoolHoliday]:
    effective_year = year or dtm.date.today().year

    for entry in get_json_data(holiday_type=HolidayType.SCHOOL, year=effective_year):
        if (holiday := SchoolHoliday.de_json(entry)).year == effective_year:
            yield holiday


def get_all_holidays(
    year: int | None = None,
) -> tuple[Iterable[PublicHoliday], Iterable[PublicHoliday], Iterable[SchoolHoliday]]:
    """Gives the national holidays, the state holidays and the school holidays for the given year,
    eah as an iterable.
    """
    public_holidays = tuple(get_public_holidays(year=year))
    return (
        (holiday for holiday in public_holidays if holiday.state_code is StateCode.NATIONAL),
        (holiday for holiday in public_holidays if holiday.state_code is not StateCode.NATIONAL),
        get_school_holidays(year=year),
    )
