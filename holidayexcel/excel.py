import calendar
import datetime as dtm
from collections.abc import Collection, Iterable
from enum import IntEnum
from pathlib import Path
from types import TracebackType

from isoweek import Week
from xlsxwriter import Workbook
from xlsxwriter import utility as utils
from xlsxwriter.format import Format
from xlsxwriter.worksheet import Worksheet

from holidayexcel.colors import BATLOW_S_HEX
from holidayexcel.enums import StateCode
from holidayexcel.holidays import BaseHoliday, PublicHoliday, SchoolHoliday
from holidayexcel.utils.datetime import date_range, day_of_year

calendar.setfirstweekday(calendar.MONDAY)

_MONTH_FORMAT = {
    "bold": 1,
    "border": 1,
    "align": "center",
    "valign": "vcenter",
    "fg_color": "white",
}
_DAY_FORMAT = {
    "bottom": 1,
}
_SCHOOL_HOLIDAY_FORMAT = {
    "fg_color": BATLOW_S_HEX[0],
}
_PUBLIC_HOLIDAY_FORMAT = {
    "fg_color": BATLOW_S_HEX[1],
}
_NATIONAL_HOLIDAY_FORMAT = {
    "fg_color": BATLOW_S_HEX[2],
}
_SATURDAY_FORMAT = {
    "fg_color": BATLOW_S_HEX[3],
    "left": 1,
}
_SUNDAY_FORMAT = {
    "fg_color": BATLOW_S_HEX[3],
    "right": 1,
}


class RowNumbers(IntEnum):
    MONTH_NAMES = 0
    WEEK_NUMBERS = 1
    DAY_NUMBERS = 2


class YearCalendar:
    def __init__(
        self,
        national_holidays: Iterable[PublicHoliday],
        state_holidays: Iterable[PublicHoliday],
        school_holidays: Iterable[SchoolHoliday],
        path: Path,
        year: int,
    ) -> None:
        self._national_holidays: Collection[PublicHoliday] = set(national_holidays)
        self._state_holidays: Collection[PublicHoliday] = set(state_holidays)
        self._school_holidays: Collection[SchoolHoliday] = set(school_holidays)
        self._path: Path = path
        self._year: int = year
        self._workbook: Workbook = Workbook(str(self._path))
        self._worksheet = self.workbook.add_worksheet()
        self._month_format = self.workbook.add_format(_MONTH_FORMAT)
        self._day_format = self.workbook.add_format(_DAY_FORMAT)
        self._school_holiday_format = self.workbook.add_format(_SCHOOL_HOLIDAY_FORMAT)
        self._public_holiday_format = self.workbook.add_format(_PUBLIC_HOLIDAY_FORMAT)
        self._national_holiday_format = self.workbook.add_format(_NATIONAL_HOLIDAY_FORMAT)
        self._saturday_format = self.workbook.add_format(_SATURDAY_FORMAT)
        self._sunday_format = self.workbook.add_format(_SUNDAY_FORMAT)
        self._saturday_day_format = self.workbook.add_format(_DAY_FORMAT)
        self._saturday_day_format.set_fg_color(self._saturday_format.fg_color)
        self._sunday_day_format = self.workbook.add_format(_DAY_FORMAT)
        self._sunday_day_format.set_fg_color(self._sunday_format.fg_color)

        self._state_row_numbers: dict[StateCode, int] = {}
        row = max(RowNumbers) + 1
        for state_code in StateCode:
            if state_code is StateCode.NATIONAL:
                continue

            self._state_row_numbers[state_code] = row
            row += 1

    @property
    def workbook(self) -> Workbook:
        return self._workbook

    @property
    def worksheet(self) -> Worksheet:
        return self._worksheet

    @property
    def year(self) -> int:
        return self._year

    @property
    def path(self) -> Path:
        return self._path

    def initialize(self) -> None:
        self.path.unlink(missing_ok=True)

    def shutdown(self) -> None:
        self._workbook.close()

    def __enter__(self: "YearCalendar") -> "YearCalendar":
        try:
            self.initialize()
            return self
        except Exception as exc:
            self.shutdown()
            raise exc

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        # Make sure not to return `True` so that exceptions are not suppressed
        # https://docs.python.org/3/reference/datamodel.html?#object.__aexit__
        self.shutdown()

    def write_day(
        self,
        cell_format: Format,
        *,
        holiday: BaseHoliday | None = None,
        start_date: dtm.date | None = None,
        end_date: dtm.date | None = None,
        national: bool = False,
    ) -> None:
        if not ((holiday is None) ^ ((start_date is None) and (end_date is None))):
            raise ValueError("Either holiday xor (start_date and end_date) must be given.")
        if holiday is None and national is False:
            raise ValueError("If no holiday is given, national must be True.")

        effective_start_date = holiday.start_date if holiday else start_date
        effective_end_date = holiday.end_date if holiday else end_date

        for date in date_range(effective_start_date, effective_end_date):  # type: ignore[arg-type]
            if national:
                cells: Iterable[str] = (
                    utils.xl_rowcol_to_cell(row, day_of_year(date))
                    for row in self._state_row_numbers.values()
                )
            else:
                cells = (
                    utils.xl_rowcol_to_cell(
                        self._state_row_numbers[holiday.state_code],  # type: ignore[union-attr]
                        day_of_year(date),
                    ),
                )
            for cell in cells:
                self.worksheet.write(cell, "", cell_format)

    def write_holidays(
        self,
        cell_format: Format,
        holidays: Iterable[BaseHoliday],
        national: bool = False,
    ) -> None:
        # Print the holidays
        for holiday in holidays:
            self.write_day(cell_format, holiday=holiday, national=national)

    def write_week_numbers(self) -> None:
        # Print the week numbers
        first_date_of_year = dtm.date(self.year, 1, 1)
        last_date_of_year = dtm.date(self.year, 12, 31)
        # loop over the previous, current and next year to ensure that
        # overlapping weeks are printed
        for y in (self.year - 1, self.year, self.year + 1):
            for week in Week.weeks_of_year(y):
                if week.monday() > last_date_of_year or week.sunday() < first_date_of_year:
                    continue

                first_col = day_of_year(max(first_date_of_year, week.monday()))
                last_col = day_of_year(min(last_date_of_year, week.sunday()))

                if first_col == last_col:
                    self.worksheet.write(
                        utils.xl_rowcol_to_cell(RowNumbers.WEEK_NUMBERS, first_col),
                        str(week.week),
                        self._month_format,
                    )
                    continue

                self.worksheet.merge_range(
                    first_row=RowNumbers.WEEK_NUMBERS,
                    last_row=RowNumbers.WEEK_NUMBERS,
                    first_col=first_col,
                    last_col=last_col,
                    data=str(week.week),
                    cell_format=self._month_format,
                )

    def write_day_numbers(self) -> None:
        # Print the day numbers
        for date in date_range(dtm.date(self.year, 1, 1), dtm.date(self.year, 12, 31)):
            cell = utils.xl_rowcol_to_cell(RowNumbers.DAY_NUMBERS, day_of_year(date))
            weekday = calendar.weekday(self.year, date.month, date.day)
            cell_format = (
                self._saturday_day_format
                if weekday == calendar.SATURDAY
                else (self._sunday_day_format if weekday == calendar.SUNDAY else self._day_format)
            )
            self.worksheet.write(cell, str(date.day), cell_format)

            if weekday not in (calendar.SATURDAY, calendar.SUNDAY):
                continue

            cell_format = (
                self._saturday_format if weekday == calendar.SATURDAY else self._sunday_format
            )
            self.write_day(
                cell_format,
                start_date=date,
                end_date=date,
                national=True,
            )

    def write_month_names(self) -> None:
        # Print the year
        offset = 1
        for month in range(1, 13):
            number_days = calendar.monthrange(self.year, month)[1]

            # Print the month name
            self.worksheet.merge_range(
                first_row=RowNumbers.MONTH_NAMES,
                last_row=RowNumbers.MONTH_NAMES,
                first_col=offset,
                last_col=offset + number_days - 1,
                data=str(calendar.month_name[month]),
                cell_format=self._month_format,
            )

            offset += number_days

    def write_state_names(self) -> None:
        # Print the state names
        for state_code in StateCode:
            if state_code is StateCode.NATIONAL:
                continue

            cell = utils.xl_rowcol_to_cell(self._state_row_numbers[state_code], 0)
            self.worksheet.write(cell, state_code.state_name)

    def write_year(self) -> None:
        # Order matters here, because we overwrite the cells in each call
        self.write_state_names()
        self.write_holidays(self._school_holiday_format, self._school_holidays)
        self.write_month_names()
        self.write_day_numbers()
        self.write_week_numbers()
        self.write_holidays(self._public_holiday_format, self._state_holidays)
        self.write_holidays(
            self._national_holiday_format,
            self._national_holidays,
            national=True,
        )
