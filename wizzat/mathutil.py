from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import collections
import math
import six

__all__ = [
    'avg',
    'Percentile',
]

def avg(iterable):
    """
    Returns the average (mean) of all values in the iterable.
    """
    return 1.0 * sum(iterable) / len(iterable)

class Avg(object):
    """
    Calculates the running average.

    a = Average()
    for x in iterable:
        a.add_value(x)

    a.average()
    """
    def __init__(self, *values):
        pass

class Percentile(object):
    """
    Logarithmic percentile approximation for non-negative values.
    Expected variance from actual median is about 5%.
    Expected memory consumption is ~8kb with constant time calculation.

    p = Percentile()
    for x in iterable:
        p.add_value(x)

    p.percentile(0.0) # Min value
    p.percentile(0.5) # Median
    p.percentile(1.0) # Max value
    """
    def __init__(self, *values):
        self.values     = collections.defaultdict(int)
        self.total      = 0
        self.num_values = 0

        for value in values:
            self.add_value(value)

    def add_value(self, value):
        if value is None:
            return

        if value < 0:
            raise ValueError()

        idx = int(math.log10(value+1) * 100)

        self.total += value
        self.values[idx] += 1
        self.num_values += 1

    def percentile(self, pct):
        if pct > 1.0:
            raise ValueError("pct > 1.0")

        if not self.values:
            return None

        target = pct * self.num_values
        ct = 0

        for idx, value in sorted(six.iteritems(self.values)):
            ct += value 
            if ct >= target:
                break

        def e(n):
            return 10**(n/100.0)-1

        return int(avg([e(idx), e(idx+.9)]))

    def __repr__(self):
        return "Percentile<min={},25={},50={},75={},98={},max={}>".format(
            self.percentile(0.0),
            self.percentile(.25),
            self.percentile(.50),
            self.percentile(.75),
            self.percentile(.98),
            self.percentile(1.0),
        )
