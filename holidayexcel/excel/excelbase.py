import locale
from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path
from types import TracebackType
from typing import Self

from xlsxwriter import Workbook
from xlsxwriter.format import Format
from xlsxwriter.worksheet import Worksheet

from holidayexcel.colors import BATLOW_S_HEX, get_gray_scale_color
from holidayexcel.holidays import HolidayDate, HolidayYear

_MONTH_FORMAT = {
    "bold": 1,
    "border": 1,
    "align": "center",
    "valign": "vcenter",
    "fg_color": "white",
}


class ExcelBase(ABC):
    SCHOOL_HOLIDAY_COLOR = BATLOW_S_HEX[0]
    PUBLIC_HOLIDAY_COLOR = BATLOW_S_HEX[1]
    WEEKEND_COLOR = BATLOW_S_HEX[2]

    def __init__(
        self,
        holiday_year: HolidayYear,
        *,
        path: Path | None = None,
        workbook: Workbook | None = None,
        worksheet_name: str | None = None,
        close: bool = True,
    ) -> None:
        if not (path is None) ^ (workbook is None):
            raise ValueError("Either path xor workbook must be passed.")

        self._holiday_year: HolidayYear = holiday_year
        self._path: Path = path or Path(workbook.filename)  # type: ignore[union-attr]
        self._workbook: Workbook = workbook or Workbook(str(self._path))
        self._worksheet = self.workbook.add_worksheet(name=worksheet_name)
        self._gray_scale_format: dict[str, Format] = {}
        self._close = close

        # formats
        self._cached_formats: dict[dict[str, str | int], Format] = {}
        self._month_format = self.workbook.add_format(_MONTH_FORMAT)

    @lru_cache(maxsize=256)  # noqa: B019
    def _get_format(self, parameters: tuple[tuple[str, str | int]]) -> Format:
        format_ = self.workbook.add_format()
        for key, value in parameters:
            setattr(format_, key, value)
        return format_

    def get_format(self, parameters: dict[str, str | int]) -> Format:
        return self._get_format(tuple(parameters.items()))

    def initialize(self) -> None:
        self.path.unlink(missing_ok=True)
        locale.setlocale(locale.LC_ALL, "de_DE.UTF-8")

    def shutdown(self) -> None:
        if self._close:
            self._workbook.close()

    def __enter__(self: Self) -> Self:
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

    def _get_gray_scale_format(self, percentage: float) -> Format:
        colour = get_gray_scale_color(percentage)
        if colour not in self._gray_scale_format:
            cell_format = self.workbook.add_format({"fg_color": colour, "font_color": "white"})
            self._gray_scale_format[colour] = cell_format
        return self._gray_scale_format[colour]

    @abstractmethod
    def write_holiday_date(self, holiday_date: HolidayDate) -> None:
        pass

    def write_holiday_dates(self) -> None:
        # Print the holiday days
        for holiday_date in self.holiday_year.iter():
            self.write_holiday_date(holiday_date)

    @abstractmethod
    def write_week_numbers(self) -> None:
        pass

    @abstractmethod
    def write_day_numbers(self) -> None:
        pass

    @abstractmethod
    def write_month_names(self) -> None:
        pass

    @abstractmethod
    def write_division_names(self) -> None:
        pass

    def write_year(self) -> None:
        # Order matters here, because we overwrite the cells in each call
        self.write_division_names()
        self.write_month_names()
        self.write_day_numbers()
        self.write_week_numbers()
        self.write_holiday_dates()

    @property
    def workbook(self) -> Workbook:
        return self._workbook

    @property
    def path(self) -> Path:
        return self._path

    @property
    def worksheet(self) -> Worksheet:
        return self._worksheet

    @property
    def holiday_year(self) -> HolidayYear:
        return self._holiday_year

    @property
    def year(self) -> int:
        return self.holiday_year.year
