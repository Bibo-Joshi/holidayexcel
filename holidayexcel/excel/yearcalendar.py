import calendar
import datetime as dtm
from collections import defaultdict
from enum import IntEnum
from functools import lru_cache
from pathlib import Path

from xlsxwriter import Workbook

from holidayexcel.colors import get_gray_scale_color
from holidayexcel.enums import CountryCode
from holidayexcel.excel.excelbase import ExcelBase
from holidayexcel.holidays import HolidayDate, HolidayYear
from holidayexcel.utils.datetime import date_range, year_range


class _RowNumbers(IntEnum):
    MONTH_NAMES = 0
    DESCRIPTION = 1


class _CellContainer:
    def __init__(self) -> None:
        self.format: dict[str, str | int] = {}
        self.content: str = ""


class _DayContainer:
    def __init__(self) -> None:
        self.day_number: _CellContainer = _CellContainer()
        self.week_number: _CellContainer = _CellContainer()
        self.field: _CellContainer = _CellContainer()


class YearCalendar(ExcelBase):
    def __init__(
        self,
        holiday_year: HolidayYear,
        *,
        path: Path | None = None,
        workbook: Workbook | None = None,
        worksheet_name: str | None = None,
        close: bool = True,
        foreign_country_code: CountryCode | None = None,
    ) -> None:
        super().__init__(
            holiday_year, path=path, workbook=workbook, worksheet_name=worksheet_name, close=close
        )
        self._foreign_country_code = foreign_country_code
        self._day_containers: dict[dtm.date, _DayContainer] = defaultdict(_DayContainer)

    @staticmethod
    @lru_cache(maxsize=12)
    def _get_month_column_offset(month: int) -> int:
        return 3 * (month - 1)

    @lru_cache(maxsize=12)  # noqa: B019
    def _get_month_row_offset(self, month: int) -> int:
        weekday = calendar.weekday(self.year, month, 1)
        return max(_RowNumbers) + 1 + (weekday - 1)

    def write_holiday_date(self, holiday_date: HolidayDate) -> None:
        for country_code in holiday_date.country_codes:
            if country_code not in (CountryCode.GERMANY, self._foreign_country_code):
                continue

            percentage = self.holiday_year.get_percentage_for_country_and_date(
                country_code, holiday_date.date
            )
            gray_scale = get_gray_scale_color(percentage)
            font_color = "#000000" if percentage < 0.5 else "#FFFFFF"
            day_container = self._day_containers[holiday_date.date]
            cell_container = (
                day_container.day_number
                if country_code == CountryCode.GERMANY
                else day_container.week_number
            )
            cell_container.format.update({"fg_color": gray_scale, "font_color": font_color})

            if (
                country_code == CountryCode.GERMANY
                and holiday_date.country_codes[country_code] is True
            ):
                day_container.field.format.update({"fg_color": self.PUBLIC_HOLIDAY_COLOR})

    def write_week_numbers(self) -> None:
        # Covered by write_day_numbers
        pass

    def write_day_numbers(self) -> None:
        for month in range(1, 13):
            number_days = calendar.monthrange(self.year, month)[1]
            month_column_offset = self._get_month_column_offset(month)

            for date in date_range(
                dtm.date(self.year, month, 1), dtm.date(self.year, month, number_days)
            ):
                format_params: dict[str, str | int] = {}
                if date.weekday() == calendar.SUNDAY or date.day == number_days:
                    format_params["bottom"] = 1
                if date.weekday() == calendar.SATURDAY or date.day == 1:
                    format_params["top"] = 1
                if date.weekday() in (calendar.SATURDAY, calendar.SUNDAY):
                    format_params["fg_color"] = self.WEEKEND_COLOR

                format_params["right"] = 1
                self._day_containers[date].day_number.format.update(format_params)
                self._day_containers[date].day_number.content = str(date.day)

                format_params["left"] = 1
                format_params["right"] = 0
                self._day_containers[date].week_number.format.update(format_params)

                if date.weekday() == calendar.MONDAY or date.day == 1:
                    self._day_containers[date].week_number.content = str(date.isocalendar().week)

                format_params["left"] = 1
                format_params["right"] = 1
                self._day_containers[date].field.format.update(format_params)
                self._day_containers[date].field.content = ""

            self.worksheet.set_column(month_column_offset, month_column_offset + 1, 2)

    def write_month_names(self) -> None:
        for month in range(1, 13):
            # Print the month name
            self.worksheet.merge_range(
                first_row=_RowNumbers.MONTH_NAMES,
                last_row=_RowNumbers.MONTH_NAMES,
                first_col=self._get_month_column_offset(month),
                last_col=self._get_month_column_offset(month) + 2,
                data=str(calendar.month_name[month]),
                cell_format=self._month_format,
            )

    def write_division_names(self) -> None:
        for month in range(1, 13):
            month_column_offset = self._get_month_column_offset(month)
            self.worksheet.write(
                _RowNumbers.DESCRIPTION, month_column_offset, self._foreign_country_code
            )
            self.worksheet.write(
                _RowNumbers.DESCRIPTION, month_column_offset + 1, CountryCode.GERMANY
            )

    def write_holiday_count_germany(self) -> None:
        pass

    def write_year(self) -> None:
        super().write_year()
        for date in year_range(self.year):
            month = date.month
            month_row_offset = self._get_month_row_offset(month)
            month_column_offset = self._get_month_column_offset(month)
            day_container = self._day_containers[date]

            self.worksheet.write(
                month_row_offset + date.day,
                month_column_offset,
                day_container.week_number.content,
                self.get_format(day_container.week_number.format),
            )
            self.worksheet.write(
                month_row_offset + date.day,
                month_column_offset + 1,
                day_container.day_number.content,
                self.get_format(day_container.day_number.format),
            )
            self.worksheet.write(
                month_row_offset + date.day,
                month_column_offset + 2,
                day_container.field.content,
                self.get_format(day_container.field.format),
            )
