#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import datetime
import locale
import logging
import re
from typing import Optional

from zvg_portal.model import Addresse


class VerkehrswertParser:
    def __init__(self):
        self._r = re.compile(r'[\d,.]{4,20}')

    def cents(self, s: str) -> Optional[int]:
        match = self._r.search(s)
        if not match:
            return
        betrag_str = match.group(0)
        if betrag_str[-3] in [',', '.']:
            cents = int(betrag_str[-2:], 10)
            betrag_without_cents = betrag_str[:-3]
        else:
            cents = 0
            betrag_without_cents = betrag_str
        euro_str = betrag_without_cents.replace('.', '').replace(',', '')
        return int(euro_str, 10) * 100 + cents


class AddressParser:
    def __init__(self):
        self._regexes = [
            re.compile(
                r'(?P<strasse>[äüöÄÜÖß (),a-zA-Z0-9-".]+), '
                r'(?P<plz>\d{5}) '
                r'(?P<ort>[äüöÄÜÖß a-zA-Z0-9-.]+), '
                r'(?P<stadtteil>[äüöÄÜÖß a-zA-Z0-9-.]+)'
            ),
            re.compile(r'(?P<strasse>[äüöÄÜÖß (),a-zA-Z0-9-."]+), (?P<plz>\d{5}) (?P<ort>[äüöÄÜÖß a-zA-Z0-9-.]+)'),
            re.compile(
                r'(?P<strasse>[^,;]+)\s*,\s*'
                r'(?P<plz>\d{5})\s*;'
                r'(?P<ort>[^,;]+)'
                r'(?:,\s*(?P<stadtteil>[^,;]+))?'
            ),
            # Handle formats with a colon separator, e.g., "Description: Street, PLZ Ort"
            re.compile(
                r':\s*(?P<strasse>[^,]+?)\s*,\s*'
                r'(?P<plz>\d{5})\s*'
                r'(?P<ort>[^,;]*)'  # Ort is optional here
            ),
        ]

    def parse(self, s: str) -> Optional[Addresse]:
        for r in self._regexes:
            m = r.search(s)
            if m:
                ret = Addresse(
                    strasse=m.group('strasse').strip(),
                    plz=m.group('plz').strip(),
                    ort=m.group('ort').strip(),
                )
                try:
                    stadtteil_val = m.group('stadtteil')
                    if stadtteil_val:
                        ret.stadtteil = stadtteil_val.strip()
                except IndexError:
                    pass

                return ret


class VersteigerungsTerminParser:
    def __init__(self):
        self._logger = logging.getLogger(self.__class__.__name__)
        self._months = {
            'januar': 1, 'februar': 2, 'märz': 3, 'april': 4, 'mai': 5, 'juni': 6,
            'juli': 7, 'august': 8, 'september': 9, 'oktober': 10, 'november': 11, 'dezember': 12
        }
        # Regex to capture "dd. month YYYY, HH:MM"
        self._date_regex = re.compile(
            r'(?P<day>\d{1,2})\.\s+(?P<month>\w+)\s+(?P<year>\d{4}),\s+(?P<hour>\d{1,2}):(?P<minute>\d{2})'
        )

    def to_datetime(self, s: str) -> Optional[datetime.datetime]:
        s = s.strip().lower()
        # Remove weekday if present (e.g., "montag, ")
        if ',' in s:
            s = s.split(',', 1)[1].strip()

        match = self._date_regex.search(s)
        if not match:
            # Fallback for strings that might have been cleaned already (e.g. no "Uhr")
            if not s.endswith('uhr'):
                 match = self._date_regex.search(f'{s} uhr')
            if not match:
                raise ValueError(f"time data {s!r} does not match any known format")

        parts = match.groupdict()
        month = self._months.get(parts['month'])
        if not month:
            raise ValueError(f"Unknown month: {parts['month']}")

        try:
            return datetime.datetime(
                year=int(parts['year']),
                month=month,
                day=int(parts['day']),
                hour=int(parts['hour']),
                minute=int(parts['minute'])
            )
        except (ValueError, TypeError) as e:
            raise ValueError(f"Could not construct datetime from {parts}: {e}")
