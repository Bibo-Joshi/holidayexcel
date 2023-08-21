import asyncio
from pathlib import Path

from holidayexcel.enums import CountryCode
from holidayexcel.excel import YearCalendar
from holidayexcel.holidays import HolidayYear


async def main() -> None:
    async with HolidayYear(year=2024, country_code=CountryCode) as holiday_year:
        with YearCalendar(
            holiday_year=holiday_year, path=Path("holidays.xlsx"), worksheet_name="Übersicht"
        ) as year_calendar:
            year_calendar.write_year()


if __name__ == "__main__":
    asyncio.run(main())
