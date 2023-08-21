import asyncio
import pickle
from pathlib import Path

# from holidayexcel.enums import CountryCode
from holidayexcel.excel import YearCalendar

# from holidayexcel.holidays import HolidayYear


async def main() -> None:
    # country_codes = (
    #     CountryCode.GERMANY,
    #     CountryCode.AUSTRIA,
    #     CountryCode.SWITZERLAND,
    #     CountryCode.FRANCE,
    # )
    # async with HolidayYear(year=2024, country_code=country_codes) as holiday_year:
    #     pickle.dump(holiday_year, Path("holiday_year.pickle").open("wb"))
    with Path("holiday_year.pickle").open("rb") as file:
        holiday_year = pickle.load(file)
        with YearCalendar(holiday_year=holiday_year, path=Path("holidays.xlsx")) as year_calendar:
            year_calendar.write_year()


if __name__ == "__main__":
    asyncio.run(main())
