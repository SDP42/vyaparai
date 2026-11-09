"""Festivals, holidays, season windows and cricket as demand signals.

The dates come from a verified, sourced table (``app/data/events.csv``, see
docs/research/FESTIVALS-AND-CRICKET.md). Dates are certain; *how much* an event moves a shop's sales is
not, so this module only says when events fall and how close they are. The forecast learns the size of
the effect from the shop's own history, and keeps these signals only if they improve the backtest.
"""

import csv
from dataclasses import dataclass
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

Arr = NDArray[np.float64]
DATA = Path(__file__).resolve().parent.parent / "data" / "events.csv"
TIER_WEIGHT = {1: 1.0, 2: 0.6, 3: 0.25}
CATEGORY_CAP = {
    "season": 0.4,
    "holiday": 0.5,
}  # background context weighs less than a festival peak

# Which zones a state belongs to (some belong to two), for events limited to certain regions.
STATE_ZONES: dict[str, frozenset[str]] = {
    "Delhi": frozenset({"north"}), "Haryana": frozenset({"north"}), "Punjab": frozenset({"north"}),
    "Himachal Pradesh": frozenset({"north"}), "Chandigarh": frozenset({"north"}),
    "Uttarakhand": frozenset({"north"}), "Jammu and Kashmir": frozenset({"north"}),
    "Rajasthan": frozenset({"north", "west"}), "Uttar Pradesh": frozenset({"north", "central"}),
    "Madhya Pradesh": frozenset({"central"}), "Chhattisgarh": frozenset({"central", "east"}),
    "Maharashtra": frozenset({"west"}), "Gujarat": frozenset({"west"}), "Goa": frozenset({"west"}),
    "Karnataka": frozenset({"south"}), "Tamil Nadu": frozenset({"south"}), "Kerala": frozenset({"south"}),
    "Telangana": frozenset({"south"}), "Andhra Pradesh": frozenset({"south"}),
    "West Bengal": frozenset({"east"}), "Odisha": frozenset({"east"}), "Bihar": frozenset({"east"}),
    "Jharkhand": frozenset({"east"}), "Assam": frozenset({"east", "northeast"}),
    "Puducherry": frozenset({"south"}), "Ladakh": frozenset({"north"}), "Lakshadweep": frozenset({"south"}),
    "Tripura": frozenset({"east", "northeast"}), "Meghalaya": frozenset({"northeast"}),
    "Manipur": frozenset({"northeast"}), "Mizoram": frozenset({"northeast"}),
    "Nagaland": frozenset({"northeast"}), "Arunachal Pradesh": frozenset({"northeast"}),
    "Sikkim": frozenset({"east", "northeast"}), "Andaman and Nicobar Islands": frozenset({"east"}),
    "Dadra and Nagar Haveli and Daman and Diu": frozenset({"west"}),
}  # fmt: skip

# What a product is, in the table's demand categories, from its category and name.
CATEGORY_MAP = {
    "staples": "staples", "dairy": "dairy", "beverages": "beverages_snacks", "snacks": "beverages_snacks",
    "personal care": "personal_care", "household": "cleaning_household", "apparel": "apparel",
    "electronics": "electronics", "jewellery": "jewellery", "sweets": "sweets_dryfruits",
}  # fmt: skip
KEYWORDS = {
    "oil_ghee_sugar": ("ghee", "oil", "sugar", "jaggery", "gur"),
    "sweets_dryfruits": ("sweet", "mithai", "dry fruit", "almond", "cashew", "raisin", "chocolate", "laddu"),
    "dairy": ("milk", "paneer", "curd", "butter", "cheese", "dahi"),
    "fasting_foods": ("sabudana", "kuttu", "singhara", "makhana", "rock salt", "sendha"),
    "fruits_flowers": ("fruit", "flower", "garland", "banana", "apple"),
    "cleaning_household": ("detergent", "cleaner", "dishwash", "phenyl", "floor"),
    "firecrackers": ("cracker", "sparkler", "firework"),
    "beverages_snacks": ("tea", "coffee", "juice", "drink", "chips", "biscuit", "namkeen", "noodle", "soda", "rusk"),
    "personal_care": ("soap", "shampoo", "toothpaste", "face wash", "hair oil"),
    "staples": ("atta", "rice", "dal", "salt", "poha", "rava", "besan", "flour", "wheat"),
}  # fmt: skip


STATE_NAMES = {n.lower() for n in STATE_ZONES}
ZONE_STRENGTH = 0.5  # an event observed in the shop's zone but not named for its state


@dataclass(frozen=True, slots=True)
class Event:
    id: str
    name: str
    start: date
    end: date
    category: str
    tier: int
    scope: str
    regions: frozenset[str]
    lead: int
    tail: int
    demand: tuple[str, ...]
    notes: str
    basis: str
    confidence: str
    sources: tuple[str, ...]

    def relevance(self, zones: frozenset[str], state: str | None) -> str | None:
        """How much this event matters where the shop is: ``core``, ``zone`` or None.

        ``core``: the shop's state is named, or the event lists only zones and the shop is in one.
        ``zone``: the event names other states but also lists a zone the shop is in (observed
        there, less strongly). With no known location, national events count as core.
        """
        if "all" in self.regions:
            return "core"
        keys = {z.lower() for z in zones}
        listed = {r.lower() for r in self.regions}
        states_listed = {r for r in listed if r in STATE_NAMES}
        if state is None and not zones:
            return "core" if self.scope == "national" else None
        if state and state.lower() in listed:
            return "core"
        if keys & listed:
            return "zone" if states_listed else "core"
        return None

    def applies(self, zones: frozenset[str], state: str | None) -> bool:
        return self.relevance(zones, state) is not None

    @property
    def weight(self) -> float:
        base = TIER_WEIGHT.get(self.tier, 0.25)
        return min(base, CATEGORY_CAP.get(self.category, 1.0))

    def phase(self, d: date) -> float:
        """0 outside the event's window; ramps up over the lead, full on the days, fades over the tail."""
        if d < self.start - timedelta(days=self.lead) or d > self.end + timedelta(days=self.tail):
            return 0.0
        if d < self.start:
            return 0.3 + 0.7 * (1 - (self.start - d).days / (self.lead + 1))
        if d <= self.end:
            return 1.0
        return 1.0 - (d - self.end).days / (self.tail + 1)


@lru_cache
def load() -> tuple[Event, ...]:
    out = []
    with DATA.open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            out.append(
                Event(
                    id=r["id"], name=r["name"], start=date.fromisoformat(r["date_start"]),
                    end=date.fromisoformat(r["date_end"]), category=r["category"], tier=int(r["tier"]),
                    scope=r["scope"], regions=frozenset(x.strip() for x in r["regions"].split(";") if x.strip()),
                    lead=int(r["lead_days"] or 0), tail=int(r["tail_days"] or 0),
                    demand=tuple(x for x in r["demand_categories"].split(";") if x),
                    notes=r["effect_notes"], basis=r["date_basis"], confidence=r["confidence"],
                    sources=tuple(x.strip() for x in r["sources"].split("|") if x.strip()),
                )
            )  # fmt: skip
    return tuple(sorted(out, key=lambda e: (e.start, e.id)))


def coverage() -> dict[str, Any]:
    ev = load()
    return {
        "first": min(e.start for e in ev) if ev else None,
        "last": max(e.end for e in ev) if ev else None,
        "events": len(ev),
        "by_confidence": {
            c: sum(1 for e in ev if e.confidence == c) for c in ("high", "medium", "low")
        },
    }


def zones_for(state: str | None) -> frozenset[str]:
    return STATE_ZONES.get(state or "", frozenset())


def relevant(zones: frozenset[str], state: str | None) -> list[Event]:
    return [e for e in load() if e.applies(zones, state)]


def intensity(
    dates: list[date], zones: frozenset[str] = frozenset(), state: str | None = None
) -> Arr:
    """Strongest festival, holiday or season effect on each day, 0 to 1. Overlaps do not stack."""
    ev = [e for e in relevant(zones, state) if e.category != "cricket"]
    strength = {e.id: (ZONE_STRENGTH if e.relevance(zones, state) == "zone" else 1.0) for e in ev}
    out = np.zeros(len(dates))
    for i, d in enumerate(dates):
        out[i] = max((strength[e.id] * e.weight * e.phase(d) for e in ev), default=0.0)
    return out


def cricket_flag(dates: list[date]) -> Arr:
    """1 on days inside an IPL or international cricket window or match day."""
    ev = [e for e in load() if e.category == "cricket" and e.tier <= 2]
    return np.array([1.0 if any(e.start <= d <= e.end for e in ev) else 0.0 for d in dates])


def peak_dates() -> list[date]:
    """Start dates of tier-1 festivals: the big retail peaks."""
    return sorted({e.start for e in load() if e.tier == 1 and e.category == "festival"})


def covariates(
    dates: list[date], horizon: int, zones: frozenset[str] = frozenset(), state: str | None = None
) -> dict[str, Arr] | None:
    """Event signals for the history plus the forecast days, or None when the table has no coverage."""
    full = [*dates, *[dates[-1] + timedelta(days=i + 1) for i in range(horizon)]]
    cov = coverage()
    if cov["first"] is None or full[-1] < cov["first"] or full[0] > cov["last"]:
        return None
    return {"event_intensity": intensity(full, zones, state), "cricket": cricket_flag(full)}


def demand_categories(name: str, category: str | None) -> set[str]:
    out: set[str] = set()
    if category and category.lower() in CATEGORY_MAP:
        out.add(CATEGORY_MAP[category.lower()])
    low = name.lower()
    for dc, words in KEYWORDS.items():
        if any(w in low for w in words):
            out.add(dc)
    return out


def window(e: Event) -> tuple[date, date]:
    return e.start - timedelta(days=e.lead), e.end + timedelta(days=e.tail)


def festival_peak_days(
    dates: list[date],
    zones: frozenset[str] = frozenset(),
    state: str | None = None,
    floor: float = 0.5,
) -> NDArray[np.bool_]:
    """Days inside a tier-1 festival's build-up, peak or first days after (phase at least ``floor``)."""
    ev = [e for e in relevant(zones, state) if e.tier == 1 and e.category == "festival"]
    return np.array([any(e.phase(d) >= floor for e in ev) for d in dates], dtype=bool)


def peak_names(
    dates: list[date], zones: frozenset[str] = frozenset(), state: str | None = None
) -> list[str]:
    """Names of the tier-1 festivals whose build-up or peak touches these dates, soonest first."""
    seen: dict[str, date] = {}
    for e in relevant(zones, state):
        if e.tier == 1 and e.category == "festival" and any(e.phase(d) >= 0.5 for d in dates):
            seen.setdefault(e.name, e.start)
    return [n for n, _ in sorted(seen.items(), key=lambda kv: kv[1])]


def gap_to_peak(dates: list[date], cap: int = 60) -> Arr:
    """Days from each date to the nearest tier-1 festival start, capped."""
    peaks = np.array([p.toordinal() for p in peak_dates()], dtype=float)
    if len(peaks) == 0:
        return np.full(len(dates), float(cap))
    days = np.array([d.toordinal() for d in dates], dtype=float)
    return np.asarray(
        np.minimum(np.abs(days[:, None] - peaks[None, :]).min(axis=1), cap), dtype=float
    )
