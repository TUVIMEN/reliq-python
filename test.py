#!/usr/bin/env python3

import os
import sys
import time
import resource
import json
import gc
from ctypes import *
from reliq import *
from memory_profiler import profile
from functools import lru_cache

html_data = None

with open("index.html", "r") as f:
    html_data = f.read()

# cat /proc/$(pidof python3)/status  | grep ^VmRSS
# watch -n 0.2 ps -vp '$(pidof python)'

def trace(x1, x2, x3):
    pass


sys.settrace(trace)

class rstr:
    def __init__(
        self, string, size=0, selfallocated=False
    ):
        if isinstance(string, str):
            string = string.encode("utf-8")

        if isinstance(string, bytes):
            if size == 0:
                size = len(string)
        self.size = size
        self.data = create_string_buffer(string)

    def __str__(self):
        string = self.string
        if isinstance(string, c_void_p):
            string = string_at(string, self.size).decode()
        return string.decode()

    def __del__(self):
        pass
        # print("str type {}".format(type(self.string)))
        # print("str type str {}".format(id(self.string)))


class nstr:
    def __init__(self, html):
        self.data = rstr(html, len(html))


@profile
def run():
    ob = html_data

    for j in range(1,10):
        x = reliq(ob)
        for i in range(1,50):
            x.search("div; a")
            type(x.search("noone"))

def run2():
    for i in range(0, 1):
        run()


print(sum(sys.getsizeof(i) for i in gc.get_objects()))
#input("start")
run2()
gc.collect()
print(sum(sys.getsizeof(i) for i in gc.get_objects()))
#input("end")

rq = reliq(html_data)
x = rq.filter('ul')

assert len(x.self()) == 4
assert len(x.children()) == 48
assert len(x.descendants()) == 152
assert len(x.full()) == 156

assert x[0].starttag() == "<ul>"
assert x[0].endtag() == "</ul>"
assert x[0].endtag(True) == "/ul"

assert x[0].starttag(raw=True) == b"<ul>"
assert x[0].endtag(raw=True) == b"</ul>"
assert x[0].endtag(True,raw=True) == b"/ul"

t = x[1].attribs()
assert len(t.keys()) == 1 or t['href'] != '/index.html'

t = x[1].attribs(raw=True)
assert len(t.keys()) == 1 or t[b'href'] != b'/index.html'

assert x[1].attribsl() == 1

assert rq[1].text_count() == 139
assert rq[1].tag_count() == 147
assert rq[1].comment_count() == 2
assert rq[1].desc() == 288
assert rq[1].lvl() == 0
assert x[1].rlvl() == 1
assert x[1].lvl() == 4

assert x[1].insides() == "<li>🏡 Home</li>"
assert x[1].tag() == "a"

assert x[1].insides(raw=True) == b"<li>\xf0\x9f\x8f\xa1 Home</li>"
assert x[1].tag(raw=True) == b"a"

assert rq[0].type() in reliq.Type.comment
assert rq[1].type() in reliq.Type.tag
assert rq[2].type() in reliq.Type.textempty
assert rq[2].type() in reliq.Type.textall
assert rq[2].type() not in reliq.Type.text

assert rq[0].insides() == "DOCTYPE HTML"
assert rq[2].insides() == None

assert rq[0].insides(raw=True) == b"DOCTYPE HTML"
assert rq[2].insides(raw=True) == None

x = rq.filter('ul',True)
assert x[0][0].insides() == "<li>🏡 Home</li>"
assert x[1].attribs()['href'] == '/index.html'

assert x[0][0].insides(raw=True) == b"<li>\xf0\x9f\x8f\xa1 Home</li>"
assert x[1].attribs(raw=True)[b'href'] == b'/index.html'

assert len(x[0].children()) == 9
assert len(x[0].self()) == 1
assert len(x[0].descendants()) == 31
assert len(x[0].full()) == 32
assert len(x[0]) == 31
assert len(x[1]) == 2
assert len(x[2]) == 1
assert len(rq[0]) == 0
assert len(rq[1]) == 288

assert x[2].text() == "🏡 Home"
assert x[3].text() == "🏡 Home"

assert x[2].text(raw=True) == b"\xf0\x9f\x8f\xa1 Home"
assert x[3].text(raw=True) == b"\xf0\x9f\x8f\xa1 Home"

assert rq[253].text() == "BTC: () bc1qw5w6pxsk3aj324tmqrhhpmpfprxcfxe6qhetuv"
assert rq[253].text(True) == "BTC: (QR) bc1qw5w6pxsk3aj324tmqrhhpmpfprxcfxe6qhetuv"
assert len(rq[1].text(True)) == 2117

assert rq[253].text(raw=True) == b"BTC: () bc1qw5w6pxsk3aj324tmqrhhpmpfprxcfxe6qhetuv"
assert rq[253].text(True,raw=True) == b"BTC: (QR) bc1qw5w6pxsk3aj324tmqrhhpmpfprxcfxe6qhetuv"

assert reliq.decode('loop &amp; &lt &tdot; &#212') == "loop & <  ⃛⃛ Ô"
assert reliq.decode('loop &amp; &lt &tdot; &#212',raw=True) == b"loop & <  \xe2\x83\x9b\xe2\x83\x9b \xc3\x94"

reliq.expr('li')
reliq.expr(b'li')

try:
    reliq.expr('li @self')
except reliq.ScriptError as e:
    pass
else:
    assert False

assert rq.search(r'ul; [0] img | "%(src)v"') == "pix/git.svg"
assert rq.search(rb'ul; [0] img | "%(src)v"') == "pix/git.svg"
assert rq.search(r'ul; [0] img | "%(src)v"',raw=True) == b"pix/git.svg"

assert rq.json('.r a c@[0]; { .name @ | "%Di" trim, .link @ | "%(href)v" } |')['r'][18]['link'] == 'pix/xmr.png'
