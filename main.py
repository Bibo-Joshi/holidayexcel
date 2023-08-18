from holidayexcel.enums import StateCode
from holidayexcel.getdata import get_all_holidays


def main() -> None:
    list(get_all_holidays(state_code=StateCode.NIEDERSACHSEN))


if __name__ == "__main__":
    main()
