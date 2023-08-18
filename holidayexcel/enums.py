from enum import StrEnum


class StateCode(StrEnum):
    BADEN_WÜRTTEMBERG = "BW"
    BAYERN = "BY"
    BERLIN = "BE"
    BRANDENBURG = "BB"
    BREMEN = "HB"
    HAMBURG = "HH"
    HESSEN = "HE"
    MECKLENBURG_VORPOMMERN = "MV"
    NIEDERSACHSEN = "NI"
    NORDRHEIN_WESTFALEN = "NW"
    RHEINLAND_PFALZ = "RP"
    SAARLAND = "SL"
    SACHSEN = "SN"
    SACHSEN_ANHALT = "ST"
    SCHLESWIG_HOLSTEIN = "SH"
    THÜRINGEN = "TH"
    NATIONAL = "NATIONAL"

    @property
    def state_name(self) -> str:
        return self.name.replace("_", "-").title()


class HolidayType(StrEnum):
    PUBLIC = "public"
    SCHOOL = "school"
