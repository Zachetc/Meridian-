"""Versioned sensitivity model, not a calibrated event predictor.

Units: hours, USD per day, USD shipment value, fractions expressed as percents.
LCG intentionally matches the browser implementation for portable replay.
"""
from dataclasses import dataclass, asdict
from math import isfinite, sqrt

@dataclass(frozen=True)
class Assumptions:
    cargoValue: float = 2_000_000
    units: int = 10_000
    delayHours: float = 48
    likelihood: float = 25
    dailyCost: float = 18_000
    annualRate: float = 12
    passThrough: float = 50
    seed: int = 42

    def validate(self):
        if any(not isfinite(v) or v < 0 for v in asdict(self).values()):
            raise ValueError('Inputs must be finite and nonnegative')
        if self.units < 1 or any(v > 100 for v in [self.likelihood,self.passThrough,self.annualRate]) or self.delayHours > 720:
            raise ValueError('Inputs out of range')

class CostModel:
    version = '0.1.0'
    def run(self, a: Assumptions, samples: int = 4000) -> dict:
        a.validate()
        if samples < 1:
            raise ValueError('samples must be positive')
        seed = int(a.seed) & 0xffffffff
        def random():
            nonlocal seed
            seed = (1664525 * seed + 1013904223) & 0xffffffff
            return seed / 4294967296
        conditional, outcomes = [], []
        ordinary = delayed = extended = 0
        for _ in range(samples):
            u = random()
            lo, mode, hi = a.delayHours*.5, a.delayHours, a.delayHours*1.75
            hours = 0 if hi == lo else (lo + sqrt(u*(hi-lo)*(mode-lo)) if u < (mode-lo)/(hi-lo) else hi - sqrt((1-u)*(hi-lo)*(hi-mode)))
            cost = hours/24 * (a.dailyCost + a.cargoValue*a.annualRate/100/365)
            conditional.append(cost)
            hit = random() < a.likelihood/100 and hours > 0
            outcomes.append(cost if hit else 0)
            if not hit: ordinary += 1
            elif hours > 72: extended += 1
            else: delayed += 1
        conditional.sort();outcomes.sort()
        expected = sum(outcomes)/samples
        return dict(expected=expected, conditionalMean=sum(conditional)/samples,
                    low=conditional[int((samples-1)*.1)],high=conditional[int((samples-1)*.9)],p95=outcomes[int((samples-1)*.95)],
                    supplier=expected*(1-a.passThrough/100),passed=expected*a.passThrough/100,
                    perUnit=expected*a.passThrough/100/a.units,ordinary=ordinary/samples*100,delayed=delayed/samples*100,extended=extended/samples*100,samples=samples)
