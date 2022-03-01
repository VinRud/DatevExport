#!/usr/bin/env python3

"""
datev_export.py: Konvertiert Buchungsstapel von jverein in Datev kompatibles Format
Format: https://developer.datev.de/portal/de/dtvf/formate
"""

__author__ = "Vinzent Rudolf"
__version__ = "1.0.0"
__email__ = "v.rudolf@vfr-grossbottwar.de"

import csv
import datetime
import math
from typing import Dict, List, Union

import mysql.connector
import pandas as pd

from datev_export.datev_defines import (
    BUSchluesselUSt,
    BUSchluesselVSt,
    KontoMapping,
    SteuerKonto,
    get_bu_schluessel,
    get_datev_column_names,
    get_datev_header,
)

KONTO_MAPPING: List[KontoMapping]
JVEREIN_STEUER_KONTEN: List[SteuerKonto]
from datev_export.custom_defines import JVEREIN_STEUER_KONTEN, KONTO_MAPPING


def get_steuer_konto_from_key(key: Union[BUSchluesselUSt, BUSchluesselVSt]):
    return next(filter(lambda x: x.buschluessel == key, JVEREIN_STEUER_KONTEN))


def get_jverein_steuer_konten(buchungsarten: Dict):
    inv_buchungsarten = {v: k for k, v in buchungsarten.items()}
    return {inv_buchungsarten[x.jverein_konto_nr]: x for x in JVEREIN_STEUER_KONTEN}


def get_buchungen(crsr, year: int) -> pd.DataFrame:
    crsr: mysql.connector.connection_cext.CMySQLCursor
    start_date = datetime.date(year, 1, 1)
    end_date = datetime.date(year, 12, 31)

    # fetch all Buchungen
    crsr.execute(
        f"SELECT * FROM buchung WHERE datum >= '{start_date.strftime('%Y-%m-%d')}' AND datum <= '{end_date.strftime('%Y-%m-%d')}'"
    )
    buchungen = pd.DataFrame([list(row) for row in crsr.fetchall()])

    # fetch column names
    crsr.execute("SHOW COLUMNS FROM jverein.buchung")
    buchungen.columns = [column[0] for column in crsr.fetchall()]
    buchungen = buchungen[buchungen["splitid"].isna() | (buchungen["splittyp"] == 3)]
    return buchungen.assign(buschluessel=math.nan)


def get_buchungsarten(crsr) -> Dict:
    crsr: mysql.connector.connection_cext.CMySQLCursor
    crsr.execute(f"SELECT * FROM buchungsart")
    buchungsarten = {col[0]: col[1] for col in crsr.fetchall()}
    return buchungsarten


def get_konten(crsr) -> Dict:
    crsr: mysql.connector.connection_cext.CMySQLCursor
    crsr.execute(f"SELECT * FROM konto")
    konten = {col[0]: col[2] for col in crsr.fetchall()}
    # KONTO_MAPPING: list[KontoMapping]
    return {
        id: next(filter(lambda x: x.jverein_konto_name == name, KONTO_MAPPING)).datev_konto_nr for id, name in konten.items()
    }


def main(year: int, host: str, user: str, password: str, database: str):
    cnxn: mysql.connector.CMySQLConnection
    cnxn = mysql.connector.connect(host=host, user=user, password=password, database=database)
    crsr: mysql.connector.connection_cext.CMySQLCursor
    crsr = cnxn.cursor()
    buchungen = get_buchungen(crsr, year)
    buchungsarten = get_buchungsarten(crsr)
    konten = get_konten(crsr)
    jverein_steuer_konten = get_jverein_steuer_konten(buchungsarten)

    use_leistungsausgleich = True
    debitoren_konto = 9999
    kreditoren_konto = 99999

    # DATEV Header
    header = get_datev_header(year)
    columns = get_datev_column_names()
    datev_buchungen = [header, columns]
    output_file = f"datev_export_{year}.csv"

    for konto, konto_buchungen in buchungen.groupby(["konto"]):
        umsatz_buchungen: pd.DataFrame
        for umsatzid, umsatz_buchungen in konto_buchungen.groupby("name"):
            buchung: pd.Series
            # check if we split for taxes
            for _, steuer_buchung in filter(
                lambda x: x[1]["buchungsart"] in jverein_steuer_konten.keys(),
                umsatz_buchungen.iterrows(),
            ):
                steuer_konto = jverein_steuer_konten[steuer_buchung["buchungsart"]]

                def find_netto_buchung(buchung: pd.Series):
                    steuer = round(buchung["betrag"] * steuer_konto.steuersatz / 100, 2)
                    steuer_fits = (
                        (steuer == steuer_buchung["betrag"])
                        or (steuer == round(steuer_buchung["betrag"] + 0.01, 2))
                        or (steuer == round(steuer_buchung["betrag"] - 0.01, 2))
                    )
                    zweck_fits = steuer_buchung["zweck"].startswith(buchung["zweck"])
                    not_used = buchung[["buschluessel"]].isna().all()
                    return steuer_fits and zweck_fits and not_used

                netto_buchung = list(filter(lambda x: find_netto_buchung(x[1]), umsatz_buchungen.iterrows()))
                if len(netto_buchung) == 0:
                    raise IOError(f"Cannot find corresponding netto Buchung:\n{steuer_buchung}\n{umsatz_buchungen}")
                elif len(netto_buchung) > 1:
                    raise IOError(f"Netto Buchung is not unique:\n{steuer_buchung}\n{umsatz_buchungen}")
                id = netto_buchung[0][0]

                netto_buchung = umsatz_buchungen.loc[id]
                brutto = round(netto_buchung["betrag"] + steuer_buchung["betrag"], 2)
                umsatz_buchungen.loc[id, "betrag"] = brutto
                umsatz_buchungen.loc[id, "buschluessel"] = steuer_konto.buschluessel

            for _, buchung in filter(
                lambda x: x[1]["buchungsart"] not in jverein_steuer_konten.keys() and x[1]["betrag"] != 0,
                umsatz_buchungen.iterrows(),
            ):
                new_buchung = {col: "" for col in columns}
                new_buchung["Umsatz"] = f"{abs(buchung['betrag'])}".replace(".", ",")
                new_buchung["WKZ Umsatz"] = "EUR"
                leistung_ausgleich = None

                if buchung["betrag"] >= 0:
                    new_buchung["Konto"] = buchungsarten[buchung["buchungsart"]]
                    new_buchung["Gegenkonto (ohne BU-Schlüssel)"] = konten[konto]
                else:
                    new_buchung["Konto"] = konten[konto]
                    new_buchung["Gegenkonto (ohne BU-Schlüssel)"] = buchungsarten[buchung["buchungsart"]]

                new_buchung["Belegdatum"] = buchung["datum"].strftime("%d%m")
                new_buchung["Belegfeld 1"] = int(umsatzid)
                new_buchung["Buchungstext"] = buchung["zweck"].replace("\r", "").replace("\n", "")

                if not buchung[["buschluessel"]].isna().all():
                    new_buchung["BU-Schlüssel"] = get_bu_schluessel(buchung["datum"], buchung["buschluessel"])
                    steuer_konto = get_steuer_konto_from_key(buchung["buschluessel"])
                    is_active = any(filter(lambda x: x[0] <= buchung["datum"] <= x[1], steuer_konto.used_daterange))
                    if not is_active:
                        leistung_ausgleich = new_buchung.copy()
                        leistung_ausgleich["Buchungstext"] = "Ausgleich - " + leistung_ausgleich["Buchungstext"]

                        # use last date for "Leistungsdatum"
                        leistung_date = list(filter(lambda x: x[1] < buchung["datum"], steuer_konto.used_daterange))[-1][1]
                        new_buchung["BU-Schlüssel"] = get_bu_schluessel(leistung_date, buchung["buschluessel"])
                        new_buchung["Leistungsdatum"] = leistung_date.strftime("%d%m%Y")
                        new_buchung["Datum Zuord. Steuerperiode"] = buchung["datum"].strftime("%d%m%Y")
                        if use_leistungsausgleich:
                            if buchung["betrag"] >= 0:
                                leistung_ausgleich["Gegenkonto (ohne BU-Schlüssel)"] = konten[konto]
                                leistung_ausgleich["Konto"] = kreditoren_konto
                                new_buchung["Gegenkonto (ohne BU-Schlüssel)"] = kreditoren_konto
                            else:
                                leistung_ausgleich["Konto"] = konten[konto]
                                leistung_ausgleich["Gegenkonto (ohne BU-Schlüssel)"] = debitoren_konto
                                new_buchung["Konto"] = debitoren_konto

                datev_buchungen.append(list(new_buchung.values()))
                if use_leistungsausgleich and leistung_ausgleich:
                    datev_buchungen.append(list(leistung_ausgleich.values()))

    with open(output_file, "w", newline="") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerows(datev_buchungen)
