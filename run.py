#!/usr/bin/env python3

"""
datev_export.py: Konvertiert Buchungsstapel von jverein in Datev kompatibles Format
Format: https://developer.datev.de/portal/de/dtvf/formate
"""

__author__ = "Vinzent Rudolf"
__version__ = "1.0.0"
__email__ = "v.rudolf@vfr-grossbottwar.de"

import argparse
from typing import Sequence
from datev_export import datev_export

import argparse


def parse_args(argv: Sequence[str] = None):
    parser = argparse.ArgumentParser(description="Connect to your 'jVerein' database.")
    parser.add_argument(
        "year",
        type=int,
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="host IP of your MySQL database",
        type=str,
    )
    parser.add_argument(
        "user",
        help="username of your MySQL database",
        type=str,
    )
    parser.add_argument(
        "password",
        help="password of your MySQL database",
        type=str,
    )
    parser.add_argument(
        "--database",
        default="jverein",
        help="name of the databse",
        type=str,
    )
    args = parser.parse_args(argv)
    return {
        "year": args.year,
        "host": args.host,
        "user": args.user,
        "password": args.password,
        "database": args.database,
    }


if __name__ == "__main__":
    datev_export.main(**parse_args())
