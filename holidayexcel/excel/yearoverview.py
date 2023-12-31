import calendar
import datetime as dtm
from collections.abc import Collection
from enum import IntEnum
from pathlib import Path
from typing import Literal

from isoweek import Week
from xlsxwriter import Workbook
from xlsxwriter import utility as utils

from holidayexcel.enums import CountryCode, HolidayType
from holidayexcel.excel.excelbase import ExcelBase
from holidayexcel.holidays import HolidayDate, HolidayYear
from holidayexcel.openholidaysapi import CountryResponse, SubdivisionResponse
from holidayexcel.utils.datetime import day_of_year, truncate_to_year, year_range

calendar.setfirstweekday(calendar.MONDAY)

_DAY_FORMAT = {
    "bottom": 1,
}
_SCHOOL_HOLIDAY_FORMAT = {
    "fg_color": ExcelBase.SCHOOL_HOLIDAY_COLOR,
}
_PUBLIC_HOLIDAY_FORMAT = {
    "fg_color": ExcelBase.PUBLIC_HOLIDAY_COLOR,
}
_WEEKEND_FORMAT = {
    "fg_color": ExcelBase.WEEKEND_COLOR,
}


class _RowNumbers(IntEnum):
    MONTH_NAMES = 0
    WEEK_NUMBERS = 1
    DAY_NUMBERS = 2
    HOLIDAY_COUNT = 3


class YearOverview(ExcelBase):
    def __init__(
        self,
        holiday_year: HolidayYear,
        *,
        path: Path | None = None,
        workbook: Workbook | None = None,
        worksheet_name: str | None = None,
        close: bool = True,
    ) -> None:
        super().__init__(
            holiday_year, path=path, workbook=workbook, worksheet_name=worksheet_name, close=close
        )

        self._state_row_numbers: dict[str, tuple[int, SubdivisionResponse | CountryResponse]] = {}
        subdivisions = self._holiday_year.subdivisions
        row = max(_RowNumbers) + 1
        sorted_subdivisions = sorted(
            subdivisions[CountryCode.GERMANY].items(),
            key=lambda item: item[1].get_name(CountryCode.GERMANY),
        )
        for code, subdivision in sorted_subdivisions:
            self._state_row_numbers[code] = (row, subdivision)
            row += 1

        row += 1
        for code in sorted(
            subdivisions,
            key=lambda code: self._holiday_year.country_codes[code].get_name(CountryCode.GERMANY),
        ):
            if code == CountryCode.GERMANY:
                continue
            self._state_row_numbers[code] = (row, holiday_year.country_codes[code])
            row += 1

        # cell formats:
        self._day_format = self.workbook.add_format(_DAY_FORMAT)
        self._school_holiday_format = self.workbook.add_format(_SCHOOL_HOLIDAY_FORMAT)
        self._public_holiday_format = self.workbook.add_format(_PUBLIC_HOLIDAY_FORMAT)
        self._weekend_format = self.workbook.add_format(_WEEKEND_FORMAT)
        self._weekend_day_format = self.workbook.add_format(_DAY_FORMAT)
        self._weekend_day_format.set_fg_color(self._weekend_format.fg_color)

    def _write_weekend_day(self, column: int) -> None:
        cell_format = self._weekend_format
        cells = (
            utils.xl_rowcol_to_cell(entity[0], column)
            for entity in self._state_row_numbers.values()
        )
        for cell in cells:
            self.worksheet.write(cell, "", cell_format)

    def _write_holiday_date_germany(
        self,
        holiday_date: HolidayDate,
        column: int,
        subdivisions: Literal[True] | Collection[SubdivisionResponse],
    ) -> None:
        if subdivisions is True:
            cells: set[str] = {
                utils.xl_rowcol_to_cell(self._state_row_numbers[subdivision][0], column)
                for subdivision in self.holiday_year.subdivisions[CountryCode.GERMANY]
            }
            cell_format = self._public_holiday_format
            for cell in cells:
                self.worksheet.write(cell, "", cell_format)
        else:
            for subdivision in subdivisions:
                code = subdivision.code
                holiday_types = holiday_date.holiday_type[code]
                cell_format = (
                    self._public_holiday_format
                    if HolidayType.PUBLIC in holiday_types
                    else self._school_holiday_format
                )
                cell = utils.xl_rowcol_to_cell(self._state_row_numbers[code][0], column)
                self.worksheet.write(cell, "", cell_format)

    def _write_holiday_date_foreign(
        self, column: int, country_code: CountryCode, holiday_date: HolidayDate
    ) -> None:
        # Print the holiday day
        cell = utils.xl_rowcol_to_cell(self._state_row_numbers[country_code][0], column)
        percentage = self.holiday_year.get_percentage_for_country_and_date(
            country_code, holiday_date.date
        )
        cell_format = self._get_gray_scale_format(percentage)
        self.worksheet.write(cell, "", cell_format)

    def write_holiday_date(self, holiday_date: HolidayDate) -> None:
        # Print the holiday day
        column = day_of_year(holiday_date.date)
        for country_code, value in holiday_date.country_codes.items():
            if country_code == CountryCode.GERMANY:
                self._write_holiday_date_germany(holiday_date, column, value)
            else:
                self._write_holiday_date_foreign(column, country_code, holiday_date)

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

                first_col = day_of_year(truncate_to_year(week.monday(), self.year))
                last_col = day_of_year(truncate_to_year(week.sunday(), self.year))

                if first_col == last_col:
                    self.worksheet.write(
                        utils.xl_rowcol_to_cell(_RowNumbers.WEEK_NUMBERS, first_col),
                        str(week.week),
                        self._month_format,
                    )
                    continue

                self.worksheet.merge_range(
                    first_row=_RowNumbers.WEEK_NUMBERS,
                    last_row=_RowNumbers.WEEK_NUMBERS,
                    first_col=first_col,
                    last_col=last_col,
                    data=str(week.week),
                    cell_format=self._month_format,
                )

    def write_day_numbers(self) -> None:
        # Print the day numbers
        for date in year_range(self.year):
            int_column = day_of_year(date)
            cell = utils.xl_rowcol_to_cell(_RowNumbers.DAY_NUMBERS, int_column)
            weekday = calendar.weekday(self.year, date.month, date.day)
            cell_format = (
                self._weekend_day_format
                if weekday in (calendar.SATURDAY, calendar.SUNDAY)
                else self._day_format
            )
            self.worksheet.write(cell, str(date.day), cell_format)

            if weekday in (calendar.SATURDAY, calendar.SUNDAY):
                self._write_weekend_day(int_column)

    def write_month_names(self) -> None:
        offset = 1
        for month in range(1, 13):
            number_days = calendar.monthrange(self.year, month)[1]

            # Print the month name
            self.worksheet.merge_range(
                first_row=_RowNumbers.MONTH_NAMES,
                last_row=_RowNumbers.MONTH_NAMES,
                first_col=offset,
                last_col=offset + number_days - 1,
                data=str(calendar.month_name[month]),
                cell_format=self._month_format,
            )

            offset += number_days

    def write_division_names(self) -> None:
        # Print the division/country names
        max_length = 0
        for row, entity in self._state_row_numbers.values():
            cell = utils.xl_rowcol_to_cell(row, 0)

            name = entity.get_name(CountryCode.GERMANY)
            max_length = max(max_length, len(name))

            self.worksheet.write(cell, name)
            self.worksheet.set_column(0, 0, max_length)

    def write_holiday_count_germany(self) -> None:
        # Print the holiday count
        for holiday_date in self.holiday_year.iter():
            date = holiday_date.date
            cell = utils.xl_rowcol_to_cell(_RowNumbers.HOLIDAY_COUNT, day_of_year(date))
            value = self.holiday_year.get_count_for_country_and_date(
                country_code=CountryCode.GERMANY, date=date
            )
            percentage = self.holiday_year.get_percentage_for_country_and_date(
                country_code=CountryCode.GERMANY, date=date
            )
            self.worksheet.write(cell, str(value), self._get_gray_scale_format(percentage))

    def write_year(self) -> None:
        super().write_year()
        self.write_holiday_count_germany()
        self.worksheet.set_column(1, 1 + day_of_year(dtm.date(self.year, 12, 31)), 2)
        self.worksheet.freeze_panes(max(_RowNumbers) + 1, 1)
