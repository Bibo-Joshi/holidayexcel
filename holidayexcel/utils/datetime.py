import datetime as dtm
from collections.abc import Iterable


def date_range(start_date: dtm.date, end_date: dtm.date) -> Iterable[dtm.date]:
    for number in range(int((end_date - start_date).days) + 1):
        yield start_date + dtm.timedelta(number)


def day_of_year(date: dtm.date) -> int:
    return int(date.strftime("%j"))
