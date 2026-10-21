"""Affiliate deep-link builders.

Every link is generated at build time, so dates in hotel/flight searches
are always in the future, no matter how old the post is.
"""
import datetime as dt
from urllib.parse import quote_plus, urlencode


class Links:
    def __init__(self, cfg, build_date):
        self.aff = cfg.get("affiliates", {})
        self.origin = cfg.get("home_airport", "DEL")
        self.d = build_date

    # ---------- date helpers ----------
    def next_weekend(self):
        days = (4 - self.d.weekday()) % 7 or 7  # next Friday (never today)
        fri = self.d + dt.timedelta(days=days)
        return fri, 2

    def in_weeks(self, weeks=3, nights=3):
        return self.d + dt.timedelta(weeks=weeks), nights

    # ---------- hotels ----------
    def booking(self, place, country="", checkin=None, nights=2):
        params = {"ss": f"{place}, {country}".strip(", ")}
        if checkin:
            params["checkin"] = checkin.isoformat()
            params["checkout"] = (checkin + dt.timedelta(days=nights)).isoformat()
        params["group_adults"] = 2
        if self.aff.get("BOOKING_AID"):
            params["aid"] = self.aff["BOOKING_AID"]
        return "https://www.booking.com/searchresults.html?" + urlencode(params)

    def agoda(self, place, checkin=None, nights=2):
        params = {"textToSearch": place, "adults": 2, "rooms": 1}
        if checkin:
            params["checkIn"] = checkin.isoformat()
            params["los"] = nights
        if self.aff.get("AGODA_CID"):
            params["cid"] = self.aff["AGODA_CID"]
        return "https://www.agoda.com/search?" + urlencode(params)

    # ---------- flights (Travelpayouts / Aviasales) ----------
    def flights(self, dest_iata, depart=None, origin=None):
        origin = origin or self.origin
        depart = depart or self.in_weeks()[0]
        if not dest_iata or dest_iata == origin:
            return None
        path = f"{origin}{depart.strftime('%d%m')}{dest_iata}1"
        url = f"https://www.aviasales.com/search/{path}"
        if self.aff.get("TP_MARKER"):
            url += "?" + urlencode({"marker": self.aff["TP_MARKER"]})
        return url

    # ---------- gear (Amazon India) ----------
    def amazon(self, keyword):
        url = "https://www.amazon.in/s?k=" + quote_plus(keyword)
        if self.aff.get("AMAZON_TAG"):
            url += "&tag=" + quote_plus(self.aff["AMAZON_TAG"])
        return url

    def missing(self):
        return [k for k in ("BOOKING_AID", "AGODA_CID", "AMAZON_TAG", "TP_MARKER") if not self.aff.get(k)]
