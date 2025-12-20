from __future__ import annotations

from datetime import date, timedelta


def next_business_day(d: date | None = None) -> date:
    d = d or date.today()
    nd = d + timedelta(days=1)
    while nd.weekday() >= 5:  # 5=Sat, 6=Sun
        nd += timedelta(days=1)
    return nd







