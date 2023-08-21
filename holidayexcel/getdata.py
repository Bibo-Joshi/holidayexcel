import asyncio
import datetime as dtm
import itertools
from collections.abc import Collection, Iterable, Mapping
from typing import Any

from httpx import AsyncClient, Limits, Timeout

from holidayexcel.enums import CountryCode, HolidayType, LanguageCode
from holidayexcel.openholidaysapi import (
    CountryResponse,
    HolidayByDateResponse,
    HolidayResponse,
    SubdivisionResponse,
)
from holidayexcel.utils.collections import scn_to_set

_HEADERS = {"Accept": "application/json"}
_CLIENT = AsyncClient(
    headers=_HEADERS, limits=Limits(max_keepalive_connections=1000), timeout=Timeout(10)
)


def _build_url(endpoint: str, parameters: Mapping[str, str]) -> str:
    base_url = f"https://openholidaysapi.org/{endpoint}?"
    effective_parameters = dict(parameters)
    effective_parameters["languageIsoCode"] = LanguageCode.GERMAN
    return base_url + "&".join(f"{key}={value}" for key, value in parameters.items())


async def get_json_data(endpoint: str, parameters: Mapping[str, str]) -> list[dict[str, Any]]:
    response = await _CLIENT.get(_build_url(endpoint, parameters), headers=_HEADERS)
    response.raise_for_status()  # raises an exception if the request failed

    return response.json()


async def get_holidays(
    holiday_type: HolidayType, year: int | None, country_code: str
) -> tuple[HolidayResponse, ...]:
    effective_year = year or dtm.date.today().year
    parameters = {
        "countryIsoCode": country_code,
        "validFrom": f"{effective_year}-01-01",
        "validTo": f"{effective_year}-12-31",
    }
    endpoint = "PublicHolidays" if holiday_type is HolidayType.PUBLIC else "SchoolHolidays"
    return tuple(HolidayResponse(**entry) for entry in await get_json_data(endpoint, parameters))


async def get_holidays_by_date(
    holiday_type: HolidayType, date: dtm.date | None
) -> tuple[HolidayByDateResponse, ...]:
    effective_date = date or dtm.date.today()
    parameters = {
        "date": effective_date.isoformat(),
    }
    endpoint = (
        "PublicHolidaysByDate" if holiday_type is HolidayType.PUBLIC else "SchoolHolidaysByDate"
    )
    return tuple(
        HolidayByDateResponse(**entry) for entry in await get_json_data(endpoint, parameters)
    )


async def get_public_holidays(
    country_code: str, year: int | None = None
) -> tuple[HolidayResponse, ...]:
    return await get_holidays(
        holiday_type=HolidayType.PUBLIC, year=year, country_code=country_code
    )


async def get_public_holidays_by_date(
    date: dtm.date | None = None,
) -> tuple[HolidayByDateResponse, ...]:
    return await get_holidays_by_date(holiday_type=HolidayType.PUBLIC, date=date)


async def get_school_holidays(
    country_code: str, year: int | None = None
) -> tuple[HolidayResponse, ...]:
    return await get_holidays(
        holiday_type=HolidayType.SCHOOL, year=year, country_code=country_code
    )


async def get_school_holidays_by_date(
    date: dtm.date | None = None,
) -> tuple[HolidayByDateResponse, ...]:
    return await get_holidays_by_date(holiday_type=HolidayType.SCHOOL, date=date)


async def get_all_holidays(
    year: int | None = None, country_code: str | Collection[str] = CountryCode.GERMANY
) -> Iterable[HolidayResponse]:
    country_codes: Collection[str] = scn_to_set(country_code)
    return itertools.chain(
        *(
            await asyncio.gather(
                *(
                    get_holidays(holiday_type=holiday_type, country_code=country_code, year=year)
                    for country_code in country_codes
                    for holiday_type in HolidayType
                ),
            )
        ),
    )


async def get_all_holidays_by_date(
    date: dtm.date | None = None,
    country_code: str | Collection[str] = CountryCode.GERMANY,
) -> Iterable[HolidayByDateResponse]:
    country_codes: Collection[str] = scn_to_set(country_code)
    results = itertools.chain(
        *(
            await asyncio.gather(
                *(
                    get_holidays_by_date(holiday_type=holiday_type, date=date)
                    for holiday_type in HolidayType
                ),
            )
        ),
    )
    return tuple(result for result in results if result.country.iso_code in country_codes)


async def get_subdivisions(country_code: CountryCode) -> tuple[SubdivisionResponse, ...]:
    parameters = {"countryIsoCode": country_code}
    endpoint = "Subdivisions"
    return tuple(
        SubdivisionResponse(**entry) for entry in await get_json_data(endpoint, parameters)
    )


async def get_countries() -> tuple[CountryResponse, ...]:
    endpoint = "Countries"
    parameters: dict[str, Any] = {}
    return tuple(CountryResponse(**entry) for entry in await get_json_data(endpoint, parameters))
