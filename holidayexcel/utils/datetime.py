import datetime as dtm
from collections.abc import Iterable


def date_range(
    start_date: dtm.date, end_date: dtm.date, limit_to_year: int | None = None
) -> Iterable[dtm.date]:
    if limit_to_year is not None:
        start_date = truncate_to_year(start_date, limit_to_year)
        end_date = truncate_to_year(end_date, limit_to_year)

    for number in range(int((end_date - start_date).days) + 1):
        yield start_date + dtm.timedelta(number)


def year_range(year: int) -> Iterable[dtm.date]:
    return date_range(dtm.date(year, 1, 1), dtm.date(year, 12, 31))


def day_of_year(date: dtm.date) -> int:
    return int(date.strftime("%j"))


def truncate_to_year(date: dtm.date, year: int) -> dtm.date:
    min_date = dtm.date(year, 1, 1)
    max_date = dtm.date(year, 12, 31)
    return min(max(date, min_date), max_date)
