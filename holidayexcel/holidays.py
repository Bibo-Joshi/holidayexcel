import datetime as dtm
import re
from abc import ABC, abstractmethod
from collections.abc import Collection
from typing import TypeVar

from holidayexcel.enums import StateCode

_T = TypeVar("_T")


class BaseHoliday(ABC):
    def __init__(self, start_date: dtm.date, end_date: dtm.date, state_code: StateCode):
        self._start_date: dtm.date = start_date
        self._end_date: dtm.date = end_date
        self._state_code: StateCode = state_code
        self._years: Collection[int] = set(range(start_date.year, end_date.year + 1))

    @property
    def start_date(self) -> dtm.date:
        return self._start_date

    @property
    def end_date(self) -> dtm.date:
        return self._end_date

    @property
    def state_code(self) -> StateCode:
        return self._state_code

    @property
    def years(self) -> Collection[int]:
        return self._years

    @property
    @abstractmethod
    def description(self) -> str:
        ...

    @classmethod
    @abstractmethod
    def de_json(cls: type[_T], data: dict[str, str]) -> _T:
        ...

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(start_date={self.start_date}, "
            f"end_date={self.end_date}, state_code={self.state_code}), "
            f"description={self.description!r})"
        )


class SchoolHoliday(BaseHoliday):
    def __init__(
        self, start_date: dtm.date, end_date: dtm.date, state_code: StateCode, name: str, slug: str
    ):
        super().__init__(start_date, end_date, state_code)
        self._name: str = name
        self._slug: str = slug

    @property
    def description(self) -> str:
        return self._name

    @property
    def slug(self) -> str:
        return self._slug

    @staticmethod
    def _prettify_name(name: str, state_code: StateCode) -> str:
        if "beweglicher ferientag" in name.lower():
            return "Brückentag"

        pattern = re.compile(rf"(\w+) {state_code.state_name.lower()} \d+")
        return pattern.sub(r"\1", name).title()

    @classmethod
    def de_json(cls, data: dict[str, str]) -> "SchoolHoliday":
        # Don't change in-place
        data = data.copy()

        state_code = StateCode(data["stateCode"])
        return cls(
            start_date=dtm.date.fromisoformat(data["start"]),
            end_date=dtm.date.fromisoformat(data["end"]),
            state_code=state_code,
            name=cls._prettify_name(data["name"], state_code),
            slug=data["slug"],
        )


class PublicHoliday(BaseHoliday):
    def __init__(self, date: dtm.date, state_code: StateCode, name: str, hint: str):
        super().__init__(start_date=date, end_date=date, state_code=state_code)
        self._name: str = name
        self._hint: str = hint

    @property
    def description(self) -> str:
        return self._name

    @property
    def hint(self) -> str:
        return self._hint

    @classmethod
    def de_json(
        cls,
        data: dict[str, str],
        name: str | None = None,
        state_code: str | StateCode | None = None,
    ) -> "PublicHoliday":
        if name is None or state_code is None:
            raise ValueError("Missing required arguments `name` or `state_code`")

        state_code = StateCode(state_code)
        return cls(
            state_code=state_code,
            date=dtm.date.fromisoformat(data["datum"]),
            hint=data["hinweis"],
            name=name,
        )
