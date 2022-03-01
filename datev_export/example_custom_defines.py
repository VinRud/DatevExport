#!/usr/bin/env python3

"""
datev_export.py: Konvertiert Buchungsstapel von jverein in Datev kompatibles Format
Format: https://developer.datev.de/portal/de/dtvf/formate
"""

__author__ = "Vinzent Rudolf"
__version__ = "1.0.0"
__email__ = "v.rudolf@vfr-grossbottwar.de"

from datev_export.datev_defines import KontoMapping, SteuerKonto, BUSchluesselUSt, BUSchluesselVSt
from datetime import date

KONTO_MAPPING = [
    KontoMapping("Hauptkonto", 920),
    KontoMapping("Barkasse", 921),
]

JVEREIN_STEUER_KONTEN = [
    SteuerKonto(
        9650,
        "Umsatzsteuer Zweckbetrieb 7%",
        7,
        BUSchluesselUSt.k7,
        [(date(2007, 1, 1), date(2020, 6, 30)), (date(2021, 1, 1), date(date.today().year + 1, 12, 31))],
    ),
    SteuerKonto(9651, "Umsatzsteuer Zweckbetrieb 5%", 5, BUSchluesselUSt.k5, [(date(2020, 6, 30), date(2020, 12, 31))]),
]
