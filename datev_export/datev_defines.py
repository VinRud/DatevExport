#!/usr/bin/env python3

"""
datev_export.py: Konvertiert Buchungsstapel von jverein in Datev kompatibles Format
Format: https://developer.datev.de/portal/de/dtvf/formate
"""

__author__ = "Vinzent Rudolf"
__version__ = "1.0.0"
__email__ = "v.rudolf@vfr-grossbottwar.de"

import dataclasses
import enum
from datetime import date, datetime
from typing import Union


class BUSchluesselUSt(enum.Enum):
    k0 = 0
    k7 = 1
    k19 = 2
    k5 = 3
    k16 = 4


class BUSchluesselVSt(enum.Enum):
    k0 = 0
    k7 = 1
    k19 = 2
    k5 = 3
    k16 = 4


@dataclasses.dataclass
class KontoMapping:
    jverein_konto_name: str
    datev_konto_nr: int


@dataclasses.dataclass
class SteuerKonto:
    jverein_konto_nr: int
    jverein_konto_name: str
    steuersatz: int
    buschluessel: Union[BUSchluesselUSt, BUSchluesselVSt]
    used_daterange: list((date, date))

    """
    konto_7ust = SteuerKonto(
                    5198,
                    'S - Umsatzsteuer 7%',
                    7,
                    BUSchluesselUSt.k7,
                    [[date(2007, 1, 1), date(2020, 6, 30)], [date(2021, 1, 1), date(date.today().year + 1, 12, 31)]])
    """


BU_UST_MAPPING = {
    (date(2007, 1, 1), date(2020, 6, 30)): {
        BUSchluesselUSt.k0: 1,
        BUSchluesselUSt.k7: 2,
        BUSchluesselUSt.k19: 3,
        BUSchluesselUSt.k16: 5,
    },
    (date(2020, 7, 1), date(2020, 12, 31)): {
        BUSchluesselUSt.k0: 1,
        BUSchluesselUSt.k5: 2,
        BUSchluesselUSt.k16: 3,
        BUSchluesselUSt.k7: 4,
        BUSchluesselUSt.k19: 5,
    },
    (date(2021, 1, 1), date(date.today().year, 12, 31)): {
        BUSchluesselUSt.k0: 1,
        BUSchluesselUSt.k7: 2,
        BUSchluesselUSt.k19: 3,
        BUSchluesselUSt.k5: 4,
        BUSchluesselUSt.k16: 5,
    },
}


BU_VST_MAPPING = {
    (date(2007, 1, 1), date(2020, 6, 30)): {
        BUSchluesselVSt.k16: 7,
        BUSchluesselVSt.k7: 8,
        BUSchluesselVSt.k19: 9,
    },
    (date(2020, 7, 1), date(2020, 12, 31)): {
        BUSchluesselVSt.k7: 6,
        BUSchluesselVSt.k19: 7,
        BUSchluesselVSt.k5: 8,
        BUSchluesselVSt.k16: 9,
    },
    (date(2021, 1, 1), date(date.today().year, 12, 31)): {
        BUSchluesselVSt.k5: 6,
        BUSchluesselVSt.k16: 7,
        BUSchluesselVSt.k7: 8,
        BUSchluesselVSt.k19: 9,
    },
}


def get_bu_schluessel(buchung_date: date, key: Union[BUSchluesselUSt, BUSchluesselVSt]):
    if isinstance(key, BUSchluesselUSt):
        active_date = next(filter(lambda date_range: date_range[0] <= buchung_date <= date_range[1], BU_UST_MAPPING.keys()))
        return BU_UST_MAPPING[active_date][key]
    elif isinstance(key, BUSchluesselVSt):
        active_date = next(filter(lambda date_range: date_range[0] <= buchung_date <= date_range[1], BU_VST_MAPPING.keys()))
        return BU_VST_MAPPING[active_date][key]
    else:
        raise ValueError


def get_datev_header(year: int, debug: bool = False) -> Union[dict, list]:
    header = {
        1: {"value": "EXTF", "descr": "Kennzeichen"},
        2: {"value": "700", "descr": "Versionsnummer"},
        3: {"value": "21", "descr": "Formatkategorie"},
        4: {"value": "Buchungsstapel", "descr": "Formatname"},
        5: {"value": "9", "descr": "Formatversion"},
        6: {
            "value": datetime.today().strftime("%Y%m%d%H%M%S%f")[:-3],
            "descr": "erzeugt am (YYYYMMDDHHMMSSFFF)",
        },
        7: {"value": "", "descr": "reserviert (Leerfeld)"},
        8: {"value": "", "descr": "reserviert (Leerfeld)"},
        9: {"value": "", "descr": "reserviert (Leerfeld)"},
        10: {"value": "", "descr": "reserviert (Leerfeld)"},
        11: {"value": "123", "descr": "Beraternummer"},
        12: {"value": "321", "descr": "Mandantennummer"},
        13: {
            "value": date(year, 1, 1).strftime("%Y%m%d"),
            "descr": "Wirtschaftsjahresbeginn (Format: YYYYMMDD)",
        },
        14: {"value": "4", "descr": "Nummernlänge der Sachkonten"},
        15: {
            "value": date(year, 1, 1).strftime("%Y%m%d"),
            "descr": "Beginn der Periode des Stapels (YYYYMMDD)",
        },
        16: {
            "value": date(year, 12, 31).strftime("%Y%m%d"),
            "descr": "Ende der Periode des Stapels (YYYYMMDD)",
        },
        17: {"value": "", "descr": "Bezeichnung des Stapels"},
        18: {
            "value": "VR",
            "descr": "Diktatkürzel (Kürzel in Großbuchstaben des Bearbeiters)",
        },
        19: {
            "value": "1",
            "descr": "Buchungstyp (1 = Finanzbuchführung (default), 2 = Jahresabschluss",
        },
        20: {"value": "0", "descr": "Rechnungslegungszweck"},
        21: {"value": "1", "descr": "Festschreibung"},
        22: {"value": "EUR", "descr": "WKZ (ISO-Code der Währung)"},
        23: {"value": "", "descr": "reserviert (Leerfeld)"},
        24: {"value": "", "descr": "Derivatskennzeichen (Leerfeld)"},
        25: {"value": "", "descr": "reserviert (Leerfeld)"},
        26: {"value": "", "descr": "reserviert (Leerfeld)"},
        27: {"value": "", "descr": "Sachkontenrahmen"},
        28: {"value": "", "descr": "ID der Branchenlösung"},
        29: {"value": "", "descr": "reserviert (Leerfeld)"},
        30: {"value": "", "descr": "reserviert (Leerfeld)"},
        31: {"value": "", "descr": "Anwendungsinformation"},
    }
    if debug:
        return header
    else:
        return [val["value"] for val in header.values()]


DATEV_COLUMN_NAMES = {
    1: {
        "name": "Umsatz",
        "descr": "Umsatz/Betrag für den Datensatz (muss immer positiv sein)",
    },
    2: {
        "name": "Soll-/Haben-Kennzeichen",
        "descr": "Soll-/Haben-Kennzeichnung (bezieht sich auf das Feld #7 Konto); S = SOLL (default), H = HABEN",
    },
    3: {"name": "WKZ Umsatz", "descr": "ISO-Code der Währung"},
    4: {
        "name": "Kurs",
        "descr": "Wenn Umsatz in Fremdwährung bei #1 angegeben wird (braucht #4, #5, #6)",
    },
    5: {"name": "Basisumsatz", "descr": "siehe #4"},
    6: {"name": "WKZ Basisumsatz", "descr": "siehe #4"},
    7: {"name": "Konto", "descr": "Sach- oder Personenkonto z.B. 8400"},
    8: {
        "name": "Gegenkonto (ohne BU-Schlüssel)",
        "descr": "Sach- oder Personenkonto z.B. 70000",
    },
    9: {
        "name": "BU-Schlüssel",
        "descr": "Steuerungskennzeichen zur Abbildung verschiedener Funktionen/Sachverhalte",
    },
    10: {
        "name": "Belegdatum",
        "descr": "Format: TTMM, z.B. 0105; Das Jahr wird immer aus dem Feld 13 des Headers ermittelt",
    },
    11: {
        "name": "Belegfeld 1",
        "descr": "Rechnungs-/Belegnummer; Wird als 'Schlüssel' für den Ausgleich offener Rechnungen genutzt",
    },
    12: {
        "name": "Belegfeld 2",
        "descr": "https://apps.datev.de/help-center/documents/9211385",
    },
    13: {
        "name": "Skonto",
        "descr": "Skontobetrag z.B. 3,71; nur bei Zahlungsbuchungen zulässig",
    },
    14: {"name": "Buchungstext", "descr": "0-60 Zeichen"},
    15: {
        "name": "Postensperre",
        "descr": "Mahn- oder Zahlsperre; 0 = keine Sperre (default), 1 = Sperre; Die Rechnung kann aus dem Mahnwesen / Zahlungsvorschlag ausgeschlossen werden.",
    },
    16: {
        "name": "Diverse Adressnummer",
        "descr": "Adressnummer einer diversen Adresse.",
    },
    17: {"name": "Geschäftspartnerbank", "descr": ""},
    18: {"name": "Sachverhalt", "descr": ""},
    19: {"name": "Zinssperre", "descr": ""},
    20: {"name": "Beleglink", "descr": ""},
    21: {"name": "Beleginfo-Art 1", "descr": ""},
    22: {"name": "Beleginfo-Inhalt 1", "descr": ""},
    23: {"name": "Beleginfo-Art 2", "descr": ""},
    24: {"name": "Beleginfo-Inhalt 2", "descr": ""},
    25: {"name": "Beleginfo-Art 3", "descr": ""},
    26: {"name": "Beleginfo-Inhalt 3", "descr": ""},
    27: {"name": "Beleginfo-Art 4", "descr": ""},
    28: {"name": "Beleginfo-Inhalt 4", "descr": ""},
    29: {"name": "Beleginfo-Art 5", "descr": ""},
    30: {"name": "Beleginfo-Inhalt 5", "descr": ""},
    31: {"name": "Beleginfo-Art 6", "descr": ""},
    32: {"name": "Beleginfo-Inhalt 6", "descr": ""},
    33: {"name": "Beleginfo-Art 7", "descr": ""},
    34: {"name": "Beleginfo-Inhalt 7", "descr": ""},
    35: {"name": "Beleginfo-Art 8", "descr": ""},
    36: {"name": "Beleginfo-Inhalt 8", "descr": ""},
    37: {"name": "KOST1-Kostenstelle", "descr": ""},
    38: {"name": "KOST2-Kostenstelle", "descr": ""},
    39: {"name": "KOST-Menge", "descr": ""},
    40: {"name": "EU-Mitgliedstaat u. UStID (Bestimmung)", "descr": ""},
    41: {"name": "EU-Steuersatz (Bestimmung)", "descr": ""},
    42: {"name": "Abw. Versteuerungsart", "descr": ""},
    43: {"name": "Sachverhalt L+L", "descr": ""},
    44: {"name": "Funktionsergänzung L+L", "descr": ""},
    45: {"name": "BU 49 Hauptfunktiontyp", "descr": ""},
    46: {"name": "BU 49 Hauptfunktionsnummer", "descr": ""},
    47: {"name": "BU 49 Funktionsergänzung", "descr": ""},
    48: {"name": "Zusatzinformation - Art 1", "descr": ""},
    49: {"name": "Zusatzinformation - Inhalt 1", "descr": ""},
    50: {"name": "Zusatzinformation - Art 2", "descr": ""},
    51: {"name": "Zusatzinformation - Inhalt 2", "descr": ""},
    52: {"name": "Zusatzinformation - Art 3", "descr": ""},
    53: {"name": "Zusatzinformation - Inhalt 3", "descr": ""},
    54: {"name": "Zusatzinformation - Art 4", "descr": ""},
    55: {"name": "Zusatzinformation - Inhalt 4", "descr": ""},
    56: {"name": "Zusatzinformation - Art 5", "descr": ""},
    57: {"name": "Zusatzinformation - Inhalt 5", "descr": ""},
    58: {"name": "Zusatzinformation - Art 6", "descr": ""},
    59: {"name": "Zusatzinformation - Inhalt 6", "descr": ""},
    60: {"name": "Zusatzinformation - Art 7", "descr": ""},
    61: {"name": "Zusatzinformation - Inhalt 7", "descr": ""},
    62: {"name": "Zusatzinformation - Art 8", "descr": ""},
    63: {"name": "Zusatzinformation - Inhalt 8", "descr": ""},
    64: {"name": "Zusatzinformation - Art 9", "descr": ""},
    65: {"name": "Zusatzinformation - Inhalt 9", "descr": ""},
    66: {"name": "Zusatzinformation - Art 10", "descr": ""},
    67: {"name": "Zusatzinformation - Inhalt 10", "descr": ""},
    68: {"name": "Zusatzinformation - Art 11", "descr": ""},
    69: {"name": "Zusatzinformation - Inhalt 11", "descr": ""},
    70: {"name": "Zusatzinformation - Art 12", "descr": ""},
    71: {"name": "Zusatzinformation - Inhalt 12", "descr": ""},
    72: {"name": "Zusatzinformation - Art 13", "descr": ""},
    73: {"name": "Zusatzinformation - Inhalt 13", "descr": ""},
    74: {"name": "Zusatzinformation - Art 14", "descr": ""},
    75: {"name": "Zusatzinformation - Inhalt 14", "descr": ""},
    76: {"name": "Zusatzinformation - Art 15", "descr": ""},
    77: {"name": "Zusatzinformation - Inhalt 15", "descr": ""},
    78: {"name": "Zusatzinformation - Art 16", "descr": ""},
    79: {"name": "Zusatzinformation - Inhalt 16", "descr": ""},
    80: {"name": "Zusatzinformation - Art 17", "descr": ""},
    81: {"name": "Zusatzinformation - Inhalt 17", "descr": ""},
    82: {"name": "Zusatzinformation - Art 18", "descr": ""},
    83: {"name": "Zusatzinformation - Inhalt 18", "descr": ""},
    84: {"name": "Zusatzinformation - Art 19", "descr": ""},
    85: {"name": "Zusatzinformation - Inhalt 19", "descr": ""},
    86: {"name": "Zusatzinformation - Art 20", "descr": ""},
    87: {"name": "Zusatzinformation - Inhalt 20", "descr": ""},
    88: {"name": "Stück", "descr": ""},
    89: {"name": "Gewicht", "descr": ""},
    90: {"name": "Zahlweise", "descr": ""},
    91: {"name": "Forderungsart", "descr": ""},
    92: {"name": "Veranlagungsjahr", "descr": ""},
    93: {"name": "Zugeordnete Fälligkeit", "descr": ""},
    94: {"name": "Skontotyp", "descr": ""},
    95: {"name": "Auftragsnummer", "descr": ""},
    96: {"name": "Buchungstyp", "descr": ""},
    97: {"name": "USt-Schlüssel (Anzahlungen)", "descr": ""},
    98: {"name": "EU-Mitgliedstaat (Anzahlungen)", "descr": ""},
    99: {"name": "Sachverhalt L+L (Anzahlungen)", "descr": ""},
    100: {"name": "EU-Steuersatz (Anzahlungen)", "descr": ""},
    101: {"name": "Erlöskonto (Anzahlungen)", "descr": ""},
    102: {"name": "Herkunft-Kz", "descr": ""},
    103: {"name": "Leerfeld", "descr": ""},
    104: {"name": "KOST-Datum", "descr": ""},
    105: {"name": "SEPA-Mandatsreferenz", "descr": ""},
    106: {"name": "Skontosperre", "descr": ""},
    107: {"name": "Gesellschaftername", "descr": ""},
    108: {"name": "Beteiligtennummer", "descr": ""},
    109: {"name": "Identifikationsnummer", "descr": ""},
    110: {"name": "Zeichnernummer", "descr": ""},
    111: {"name": "Postensperre bis", "descr": ""},
    112: {"name": "Bezeichnung SoBil-Sachverhalt", "descr": ""},
    113: {"name": "Kennzeichen SoBil-Buchung", "descr": ""},
    114: {"name": "Festschreibung", "descr": ""},
    115: {"name": "Leistungsdatum", "descr": ""},
    116: {"name": "Datum Zuord. Steuerperiode", "descr": ""},
    117: {"name": "Fälligkeit", "descr": ""},
    118: {"name": "Generalumkehr", "descr": ""},
    119: {"name": "Steuersatz", "descr": ""},
    120: {"name": "Land", "descr": ""},
    121: {"name": "Abrechnungsreferenz", "descr": ""},
    122: {"name": "BVV-Position (Betriebsvermögensvergleich)", "descr": ""},
    123: {"name": "EU-Mitgliedstaat u. UStID (Ursprung)", "descr": ""},
    124: {"name": "EU-Steuersatz (Ursprung)", "descr": ""},
}


def get_datev_column_names(debug: bool = False) -> Union[dict, list]:
    if debug:
        return DATEV_COLUMN_NAMES
    else:
        return [val["name"] for val in DATEV_COLUMN_NAMES.values()]
