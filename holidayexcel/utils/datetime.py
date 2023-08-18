import datetime as dtm
from collections.abc import Iterable


def date_range(start_date: dtm.date, end_date: dtm.date) -> Iterable[dtm.date]:
    for number in range(int((end_date - start_date).days) + 1):
        yield start_date + dtm.timedelta(number)


def day_of_year(date: dtm.date) -> int:
    return int(date.strftime("%j"))


def truncate_to_year(date: dtm.date, year: int) -> dtm.date:
    min_date = dtm.date(year, 1, 1)
    max_date = dtm.date(year, 12, 31)
    return min(max(date, min_date), max_date)
