"""Conservative Q3 disk-union certificate; no approximate maximum authorizes a skip.

Input binary floats are converted exactly to rational numbers. A finite partition
of a containing rectangle proves coverage of the ENTIRE lens, not sample points.
Failure to finish the partition returns False (unknown), never a coverage claim.
"""
from fractions import Fraction as F
from functools import lru_cache


def _min_d2(box, p):
    x0, x1, y0, y1 = box
    x, y = p
    return max(x0-x, F(0), x-x1)**2 + max(y0-y, F(0), y-y1)**2


def _max_d2(box, p):
    x0, x1, y0, y1 = box
    x, y = p
    return max((x0-x)**2, (x1-x)**2) + max((y0-y)**2, (y1-y)**2)


@lru_cache(maxsize=512)
def _certify(sites, disks, hearing_radius, max_boxes):
    if not disks:
        return False
    ss = [tuple(map(F, s)) for s in sites]
    dd = [(tuple(map(F, c)), F(r)) for c, r in disks]
    h = F(hearing_radius)
    if h < 0 or any(r < 0 for _, r in dd):
        raise ValueError("radii must be nonnegative")
    # Analytic containment includes exact equality for a scanned scout's own disk.
    for c, r in dd:
        if r <= h and any(sum((s[i]-c[i])**2 for i in (0, 1)) <= (h-r)**2 for s in ss):
            return True
    box = (max(c[0]-r for c, r in dd), min(c[0]+r for c, r in dd),
           max(c[1]-r for c, r in dd), min(c[1]+r for c, r in dd))
    if box[0] > box[1] or box[2] > box[3]:
        return True
    stack = [box]
    visited = 0
    while stack:
        if visited >= max_boxes:
            return False
        visited += 1
        b = stack.pop()
        if any(_min_d2(b, c) > r*r for c, r in dd):
            continue
        if any(_max_d2(b, s) <= h*h for s in ss):
            continue
        x0, x1, y0, y1 = b
        if x0 == x1 and y0 == y1:
            return False
        if x1-x0 >= y1-y0:
            mid = (x0+x1)/2
            stack.extend([(x0, mid, y0, y1), (mid, x1, y0, y1)])
        else:
            mid = (y0+y1)/2
            stack.extend([(x0, x1, y0, mid), (x0, x1, mid, y1)])
    return True


def certified_covered(sites, disks, hearing_radius=1000.0, max_boxes=256):
    """True proves lens coverage. False means uncovered OR undecided.

    Cache keys preserve every coordinate bit. No rounding, ULP tolerance,
    point deletion, or statistical test is used to authorize coverage.
    """
    return _certify(tuple(sorted(set(tuple(s) for s in sites))),
                    tuple((tuple(c), r) for c, r in disks), hearing_radius, max_boxes)
