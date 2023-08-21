import asyncio
import datetime as dtm
import logging
from collections import defaultdict
from collections.abc import Collection, Iterator
from types import MappingProxyType, TracebackType
from typing import Literal

from holidayexcel.enums import CountryCode
from holidayexcel.enums import HolidayType as EnumHolidayType
from holidayexcel.getdata import get_all_holidays, get_countries, get_subdivisions
from holidayexcel.openholidaysapi import (
    CountryResponse,
    HolidayResponse,
    HolidayType,
    SubdivisionResponse,
)
from holidayexcel.utils.collections import scn_to_set
from holidayexcel.utils.datetime import date_range

_LOGGER = logging.getLogger(__name__)


class HolidayDate:
    def __init__(self, date: dtm.date):
        self._date = date
        self._country_codes: dict[CountryCode, set[SubdivisionResponse] | Literal[True]] = {}
        self._holiday_type: dict[str, set[EnumHolidayType]] = defaultdict(set)

    @property
    def date(self) -> dtm.date:
        return self._date

    @property
    def year(self) -> int:
        return self._date.year

    @property
    def month(self) -> int:
        return self._date.month

    @property
    def day(self) -> int:
        return self._date.day

    @property
    def country_codes(
        self,
    ) -> MappingProxyType[CountryCode, set[SubdivisionResponse] | Literal[True]]:
        return MappingProxyType(self._country_codes)

    @property
    def holiday_type(self) -> MappingProxyType[str, set[EnumHolidayType]]:
        return MappingProxyType(self._holiday_type)

    def add_country_code(
        self,
        country_code: CountryCode,
        *,
        subdivisions: SubdivisionResponse | Collection[SubdivisionResponse] | None = None,
        nation_wide: Literal[True] | None = None,
    ) -> None:
        if not (subdivisions is not None) ^ (nation_wide is True):
            print(nation_wide, type(subdivisions))
            raise ValueError("Either subdivisions xor nation_wide must be specified.")
        if nation_wide is True:
            self._country_codes[country_code] = True
            return

        if (entry := self._country_codes.get(country_code, set())) is True:
            _LOGGER.debug(
                "Holiday is already nation wide for %s. Subdivisions will be ignored.",
                country_code,
            )
            return

        effective_subdivisions = scn_to_set(subdivisions)
        self._country_codes[country_code] = entry | effective_subdivisions

    def add_holiday_type(self, subdivision_code: str, holiday_type: EnumHolidayType) -> None:
        self._holiday_type[subdivision_code].add(holiday_type)

    def get_count_for_country(self, country_code: CountryCode, number_of_subdivisions: int) -> int:
        if (entry := self._country_codes.get(country_code, set())) is True:
            return number_of_subdivisions or 1

        return len(entry)

    def get_percentage_for_country(
        self, country_code: CountryCode, number_of_subdivisions: int
    ) -> float:
        return self.get_count_for_country(country_code, number_of_subdivisions) / (
            number_of_subdivisions or 1
        )


class HolidayYear:
    def __init__(
        self, year: int, country_code: CountryCode | Collection[CountryCode] = CountryCode.GERMANY
    ):
        self._year = year
        self._dates: dict[dtm.date, HolidayDate] = {
            date: HolidayDate(date)
            for date in date_range(dtm.date(self.year, 1, 1), dtm.date(self.year, 12, 31))
        }
        self._country_codes: set[CountryCode] = scn_to_set(country_code)
        self._subdivisions: dict[CountryCode, dict[str, SubdivisionResponse]] = defaultdict(dict)
        self._country_code_mapping: dict[CountryCode, CountryResponse] = {}

    def _parse_holiday_response(
        self, country_code: str, holiday_response: HolidayResponse
    ) -> None:
        subdivisions = (
            {
                self._subdivisions[CountryCode(country_code)][subdivision_ref.code]
                for subdivision_ref in holiday_response.subdivisions
            }
            if holiday_response.subdivisions
            else None
        )
        for date in date_range(
            holiday_response.start_date, holiday_response.end_date, limit_to_year=self.year
        ):
            self._dates[date].add_country_code(
                CountryCode(country_code),
                subdivisions=subdivisions,
                nation_wide=holiday_response.nationwide or None,
            )
            if holiday_response.type in (
                HolidayType.SCHOOL,
                HolidayType.BACK_TO_SCHOOL,
                HolidayType.END_OF_LESSONS,
            ):
                for subdivision_ref in holiday_response.subdivisions:
                    self._dates[date].add_holiday_type(
                        subdivision_code=subdivision_ref.code,
                        holiday_type=EnumHolidayType.SCHOOL,
                    )
            if holiday_response.type in (HolidayType.BANK, HolidayType.PUBLIC):
                for subdivision_ref in holiday_response.subdivisions:
                    self._dates[date].add_holiday_type(
                        subdivision_code=subdivision_ref.code,
                        holiday_type=EnumHolidayType.PUBLIC,
                    )

    async def _get_all_holidays(self, country_code: CountryCode) -> None:
        holiday_responses = await get_all_holidays(country_code=country_code, year=self.year)
        for holiday_response in holiday_responses:
            self._parse_holiday_response(country_code, holiday_response)

    async def _get_subdivisions(self, country_code: CountryCode) -> None:
        def _parse_subdivisions(subdivisions: tuple[SubdivisionResponse, ...]) -> None:
            for subdivision in subdivisions:
                self._subdivisions[country_code][subdivision.code] = subdivision
                if subdivision.children:
                    _parse_subdivisions(subdivision.children)

        results = await get_subdivisions(country_code)
        self._subdivisions.setdefault(country_code, {})
        _parse_subdivisions(results)

    async def _get_countries(self) -> None:
        results = await get_countries()
        for country in results:
            if country.iso_code in self._country_codes:
                self._country_code_mapping[CountryCode(country.iso_code)] = country

    async def initialize(self) -> None:
        await asyncio.gather(
            *(self._get_subdivisions(country_code) for country_code in self._country_codes),
            self._get_countries(),
        )

        # Don't merge with the above gather, as we want to wait for the countries to be fetched
        # before we start fetching the holidays.
        await asyncio.gather(
            *(
                self._get_all_holidays(country_code=country_code)
                for country_code in self._country_codes
            )
        )

    async def shutdown(self) -> None:
        pass

    async def __aenter__(self: "HolidayYear") -> "HolidayYear":
        try:
            await self.initialize()
            return self
        except Exception as exc:
            await self.shutdown()
            raise exc

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        # Make sure not to return `True` so that exceptions are not suppressed
        # https://docs.python.org/3/reference/datamodel.html?#object.__aexit__
        await self.shutdown()

    def get_count_for_country_and_date(self, country_code: CountryCode, date: dtm.date) -> int:
        return self._dates[date].get_count_for_country(
            country_code,
            len(self._subdivisions[country_code]),
        )

    def get_percentage_for_country_and_date(
        self, country_code: CountryCode, date: dtm.date
    ) -> float:
        return self._dates[date].get_percentage_for_country(
            country_code,
            len(self._subdivisions[country_code]),
        )

    def day(self, date: dtm.date) -> HolidayDate:
        return self._dates[date]

    @property
    def subdivisions(
        self,
    ) -> MappingProxyType[CountryCode, MappingProxyType[str, SubdivisionResponse]]:
        return MappingProxyType(
            {
                country_code: MappingProxyType(subdivisions)
                for country_code, subdivisions in self._subdivisions.items()
            }
        )

    @property
    def country_codes(self) -> MappingProxyType[CountryCode, CountryResponse]:
        return MappingProxyType(self._country_code_mapping)

    @property
    def year(self) -> int:
        return self._year

    def iter(self) -> Iterator[HolidayDate]:
        return iter(self._dates.values())
