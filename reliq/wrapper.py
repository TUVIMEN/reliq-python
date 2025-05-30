#!/usr/bin/env python3
# by Dominik Stanisław Suchora <suchora.dominik7@gmail.com>
# License: GNU GPLv3

import os
from pathlib import Path
import inspect

from .reliq import reliq, reliqExpr

def RQ(path="",cached=False):
    expressions = {}
    class rq(reliq):
        pass

    if path[:1] != "/":
        basepath = os.path.realpath(os.path.dirname(inspect.stack()[1].filename))
        path = os.path.realpath(basepath + "/" + path)

    expr_env = {
        "cached": cached,
        "path": Path(path)
    }

    class rqExpr(reliqExpr):
        def __init__(self,script: str|bytes|Path):
            x = script

            if isinstance(x,Path):
                s = str(x)
                if s[:1] != '/' and s[:2] != "./" and s[:3] != '../':
                    x = Path(os.path.realpath(expr_env['path'] / x))

            if not expr_env['cached']:
                return super().__init__(x)

            r = expressions.get(x)
            if r is not None:
                return r

            expr = super.__init__(x)
            expressions[x] = expr
            return expr

    rq.expr = rqExpr
    return rq
