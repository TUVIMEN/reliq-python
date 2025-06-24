#!/usr/bin/env python

from pprint import pprint
import platform
from typing import Callable

for i in sorted(dir(platform)):
    if i[:1] == "_" or i == "system_alias":
        continue
    r = getattr(platform, i)
    if isinstance(r, type) or not isinstance(r, Callable):
        continue

    print(i + ": " + str(r()))


print("\n=========== ALLOWED =============\n")

try:  # normal dist
    from pip._vendor.distlib.wheel import COMPATIBLE_TAGS

    pprint(COMPATIBLE_TAGS)
except Exception:  # dev dist
    from pip._vendor.packaging.tags import sys_tags

    pprint(set(sys_tags()))
