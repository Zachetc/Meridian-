"""Bounded hourly passage cohorts; never invent or shift a received ping."""
import math
from datetime import datetime
from .traffic import PASSAGES

def distance_km(a, b):
    lat1, lat2 = math.radians(a['latitude']), math.radians(b['latitude'])
    dlon = math.radians(a['longitude'] - b['longitude'])
    return 6371 * 2 * math.asin(min(1, math.sqrt(
        math.sin((lat1-lat2)/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2)))

class PassageSampler:
    """Each passage gets its own quota, regardless of traffic in other passages.

    First received eligible reports fill each hourly cohort. This is not a
    representative traffic census. Followed vessels bypass the area quota.
    Latest-state writes are limited to once per source minute; the store archives
    at most one actual report per vessel/source hour, including after restarts.
    """
    def __init__(self, passages=None, limit=10):
        self.passages = list((passages or PASSAGES).values())
        self.limit = limit
        self.hour = None
        self.members = {}
        self.minutes = {}
        self.watched = set()

    def accept(self, vessel):
        if vessel['kind'] not in ('Cargo', 'Tanker'): return False
        stamp = datetime.fromisoformat(vessel['observedAt'].replace('Z', '+00:00')).timestamp()
        hour, minute = int(stamp//3600), int(stamp//60)
        if self.hour is None or hour > self.hour:
            self.hour = hour
            self.members = {p['id']:set() for p in self.passages}
            self.minutes = {}
        if hour < self.hour: return False  # no backfill across a reception gap
        mmsi = vessel['mmsi']
        chosen = mmsi in self.watched
        for p in self.passages:
            if distance_km(p, vessel) > p['radiusKm']: continue
            cohort = self.members[p['id']]
            if mmsi in cohort or len(cohort) < self.limit:
                cohort.add(mmsi)
                chosen = True
        if not chosen or minute <= self.minutes.get(mmsi, -1): return False
        self.minutes[mmsi] = minute
        return True
