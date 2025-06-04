#!/usr/bin/env python3
# by Dominik Stanisław Suchora <hexderm@gmail.com>
# License: GNU GPLv3

import os
from pathlib import Path
import inspect
from threading import Lock

from .reliq import reliq, reliqExpr

def RQ(path="",cached=False):
    expressions = {}
    class rq(reliq):
        pass

    if path[:1] != "/":
        basepath = os.path.realpath(os.path.dirname(inspect.stack()[1].filename))
        path = os.path.realpath(basepath + "/" + path)
    path = Path(path)

    lock = Lock() if cached else None

    class rqExpr(reliqExpr):
        def __init__(self,script: str|bytes|Path):
            x = script

            if isinstance(x,Path):
                s = str(x)
                if s[:1] != '/' and s[:2] != "./" and s[:3] != '../':
                    x = Path(os.path.realpath(path / x))

            if not cached:
                return super().__init__(x)

            r = expressions.get(x)
            if r is not None:
                return r

            expr = super().__init__(x)
            with lock:
                expressions[x] = expr
            return expr

    rq.expr = rqExpr
    return rq
