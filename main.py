from pathlib import Path

from holidayexcel.excel import YearCalendar
from holidayexcel.getdata import get_all_holidays


def main() -> None:
    year = 2023
    national_holidays, state_holidays, school_holidays = get_all_holidays(year=year)
    with YearCalendar(
        national_holidays=national_holidays,
        state_holidays=state_holidays,
        school_holidays=school_holidays,
        path=Path("holidays.xlsx"),
        year=year,
    ) as calendar:
        calendar.write_year()


if __name__ == "__main__":
    main()
