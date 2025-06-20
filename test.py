#!/usr/bin/env python3

import os
import sys
import time
import resource
import json
import gc
from ctypes import *
from reliq import reliq
from memory_profiler import profile
from functools import lru_cache
from typing import Generator

html_data = None

with open("index.html", "rb") as f:
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


def test_many():
    ob = html_data

    for j in range(1,10):
        x = reliq(ob)
        for i in range(1,50):
            x.search("div; a")
            type(x.search("noone"))

@profile
def run_many(func, last=1):
    for i in range(0, last):
        func()

def print_memusage():
    print(sum(sys.getsizeof(i) for i in gc.get_objects()))

def print_run_many(func,last=1):
    print_memusage()

    run_many(func,last)
    gc.collect()

    print_memusage()
    print("========= {}\n".format(repr(func)))

def test_basic():
    rq = reliq(html_data)
    x = rq.filter('ul')

    assert x.get_data(True) is html_data

    assert len(x.self()) == 4
    assert len(x.children(type=None)) == 48
    assert len(x.children()) == 36
    assert len(x.descendants(type=None)) == 152
    assert len(x.descendants(type=reliq.Type.comment)) == 2
    assert len(x.descendants(type=reliq.Type.text)) == 53
    assert len(x.descendants(type=reliq.Type.text|reliq.Type.comment)) == 55
    assert len(x.full(type=None)) == 156
    assert isinstance(x.full(True),Generator)

    s = x[0][2]
    pos = s.position

    assert len(x.siblings()) == 11
    assert len(rq.siblings()) == 0

    assert len(s.siblings()) == 8
    assert len(s.siblings_preceding()) == 2
    assert len(s.siblings_subsequent()) == 6
    assert any(map(lambda x: x.position < pos,s.siblings_preceding()))
    assert any(map(lambda x: x.position > pos,s.siblings_subsequent()))

    assert len(x.siblings(full=True)) == 95
    assert len(rq.siblings(full=True)) == 0

    assert len(s.siblings_preceding(full=True)) == 4
    assert len(s.siblings_subsequent(full=True)) == 15
    assert len(s.siblings(full=True)) == 19
    assert any(map(lambda x: x.position < pos,s.siblings_preceding(full=True)))
    assert any(map(lambda x: x.position > pos,s.siblings_subsequent(full=True)))

    assert len(rq.everything()) == 148
    assert len(x.everything()) == 592
    assert len(s.everything()) == 148
    assert len(s.everything(type=None)) == s.struct.struct.nodesl

    assert len(rq.after()) == 0
    assert len(x.after()) == 283
    assert len(s.after()) == 130
    assert len(s.after(type=None)) == s.struct.struct.nodesl-pos-1
    def grows():
        prev = pos
        for i in map(lambda x: x.position,s.after(type=None)):
            if i-prev != 1:
                return False
            prev = i
        return True
    assert grows()

    assert len(rq.before()) == 0
    assert len(x.before()) == 305
    assert len(s.before()) == 17
    assert len(s.before(type=None)) == pos
    def descends():
        prev = pos
        for i in map(lambda x: x.position,s.before(type=None)):
            if prev-i != 1:
                return False
            prev = i
        return True
    assert descends()

    assert len(rq.rparent()) == 0
    assert len(x.rparent()) == len(x.self())
    assert len(s.rparent()) == 1
    assert s.rparent()[0].name == "ul"

    assert len(s.parent()) == 1
    assert s.parent()[0].name == 'ul'
    assert s.parent()[0].position == 28
    assert len(x.parent()) == len(x.self())
    assert x.parent()[3].name == 'main'
    assert rq.parent() == []

    assert rq.ancestors() == []
    assert len(x.ancestors()) == 14
    assert len(s.ancestors()) == 4
    assert s.ancestors()[0].name == 'ul'
    assert s.ancestors()[1].name == 'nav'
    assert s.ancestors()[2].name == 'body'
    assert s.ancestors()[3].name == 'html'

    assert len(rq.preceding()) == 0
    assert len(x.preceding()) == 291
    assert len(s.preceding()) == 13
    assert len(s.preceding(type=None)) == pos-len(s.ancestors())

    assert len(rq.subsequent()) == 0
    assert len(x.subsequent()) == 198
    assert len(s.subsequent()) == 128
    assert len(s.subsequent(type=None)) == s.struct.struct.nodesl-pos-s.desc_count-1

    assert x[0].starttag == "<ul>"
    assert x[0].endtag == "</ul>"
    assert x[0].endtag_strip == "/ul"

    assert x[0].starttag_raw == b"<ul>"
    assert x[0].endtag_raw == b"</ul>"
    assert x[0].endtag_strip_raw == b"/ul"

    t = x[1].attrib
    assert len(t.keys()) == 1 or t['href'] != '/index.html'

    t = x[1].attrib_raw
    assert len(t.keys()) == 1 or t[b'href'] != b'/index.html'

    assert x[1].attribl == 1

    assert rq[0].text_count == 139
    assert rq[0].tag_count == 147
    assert rq[0].comment_count == 2
    assert rq[0].desc_count == 288
    assert rq[0].lvl == 0
    assert rq[0][0].position == 3
    assert rq[0][0].rposition == 3
    assert x[0][0].rlvl == 1
    assert x[0][0].lvl == 4
    assert x.descendants()[3].position == 33
    assert x[0][1][0].rposition == 5
    assert x[0][1][0].position == 33

    assert x[0][0].insides == "<li>🏡 Home</li>"
    assert x[0][0].name == "a"

    assert x[0][0].insides_raw == b"<li>\xf0\x9f\x8f\xa1 Home</li>"
    assert x[0][0].name_raw == b"a"

    y = rq.full(type=None)

    assert repr(reliq()) == "<reliq Empty>"
    assert repr(rq) == "<reliq Struct 291 nodes / 6293 bytes>"
    assert repr(x) == "<reliq List 4 nodes / 6293 bytes>"

    assert repr(y[0]) == '<comment "<!DOCTYPE HTML>" / pos 0>'
    assert y[0].type in reliq.Type.comment
    assert repr(y[1]) == '<html desc 288 / pos 1>'
    assert y[1].type in reliq.Type.tag
    assert repr(y[2]) == '<textempty size 1 / pos 2>'
    assert y[2].type in reliq.Type.textempty
    assert y[2].type in reliq.Type.textall
    assert y[2].type not in reliq.Type.text
    assert repr(y[52]) == '<text "📧 Contact" / pos 52>'
    assert repr(reliq('   aaaaaaaaa a aaaaaaaaaaa  ').self(type=None)[0]) == '<text "aaaaaaaaa a aaaaaaaa"... / pos 0>'
    assert repr(reliq('k</').self(type=None)[0]) == '<texterr "k</" / pos 0>'

    assert y[0].insides == "DOCTYPE HTML"
    assert y[2].insides == None

    assert y[0].insides_raw == b"DOCTYPE HTML"
    assert y[2].insides_raw == None

    x = rq.filter('ul',True)
    assert x[0][0].insides == "<li>🏡 Home</li>"
    assert x[0][0].attrib['href'] == '/index.html'

    assert x[0][0].insides_raw == b"<li>\xf0\x9f\x8f\xa1 Home</li>"
    assert x[0][0].attrib_raw[b'href'] == b'/index.html'

    assert len(rq.filter('[0] dl style')[0].attrib['style']) == 15

    assert len(str(x)) == 3472
    assert len(x[0].children(type=None)) == 9
    assert len(x[0].self()) == 1
    assert len(x[0].descendants(type=None)) == 31
    assert len(x[0].full(type=None)) == 32
    assert len(x[0].descendants(type=None)) == 31
    assert len(x[0][0].descendants(type=None)) == 2
    assert len(x[0][0][0].descendants(type=None)) == 1
    assert len(y[0]) == 0
    assert len(y[1]) == 2
    assert len(y[1].descendants(type=None)) == 288

    z = x[0].filter('li')
    assert len(z.filter('.n img').self()) == 4
    assert len(z.children(type=None)) == 13
    assert z.search('.x [0] img | "%(src)v", .y text@ RSS') == '{"x":"pix/git.svg","y":" RSS\\n"}'

    assert x[0][0].text_recursive == "🏡 Home"
    assert x[0][0][0].text == "🏡 Home"

    assert x[0][0].text_recursive_raw == b"\xf0\x9f\x8f\xa1 Home"
    assert x[0][0][0].text_raw == b"\xf0\x9f\x8f\xa1 Home"

    assert y[253].text == "BTC: () bc1qw5w6pxsk3aj324tmqrhhpmpfprxcfxe6qhetuv"
    assert y[253].text_recursive == "BTC: (QR) bc1qw5w6pxsk3aj324tmqrhhpmpfprxcfxe6qhetuv"
    assert len(y[1].text_recursive) == 2117

    assert y[253].text_raw == b"BTC: () bc1qw5w6pxsk3aj324tmqrhhpmpfprxcfxe6qhetuv"
    assert y[253].text_recursive_raw == b"BTC: (QR) bc1qw5w6pxsk3aj324tmqrhhpmpfprxcfxe6qhetuv"

    w = rq.filter('li i@"X", text@ X')
    assert len(w.self()) == 3
    assert len(w.self(type=reliq.Type.tag)) == 1
    assert len(w) == 3
    assert len(w[2].text) == 95
    assert len(rq.self()) == 1
    assert len(rq.self(type=None)) == 3

    w = rq.filter('[0] li')
    assert str(w) == str(w[0])
    w = rq.filter('[0] ul')
    assert w.search('text@ *') == '🏡 Home\n📜 Blog\n Software\n LandChad\n📚 LindyPress\n LARBS\n📧 Contact\n RSS\n💸 Donate\n'

    assert reliq.decode('loop &amp; &lt &tdot; &#212') == "loop & <  ⃛⃛ Ô"
    assert reliq.decode('loop &amp; &lt &tdot; &#212',raw=True) == b"loop & <  \xe2\x83\x9b\xe2\x83\x9b \xc3\x94"
    assert reliq.decode('nn&nbsp;nope') == 'nn nope'
    assert reliq.decode('nn&nbsp;nope',True) == b'nn nope'
    assert reliq.decode('nn&nbsp;nope',no_nbsp=False) == 'nn\xa0nope'
    assert reliq.decode('nn&nbsp;nope',True,no_nbsp=False) == b'nn\xc2\xa0nope'

    assert reliq.encode("<p>li &amp; \t 'seq' \n </p>") == '&lt;p&gt;li &amp;amp; \t &#x27;seq&#x27; \n &lt;/p&gt;'
    assert reliq.encode("<p>li &amp; \t 'seq' \n </p>",True) == b'&lt;p&gt;li &amp;amp; \t &#x27;seq&#x27; \n &lt;/p&gt;'
    assert reliq.encode("<p>li &amp; \t 'seq' \n </p>",raw=True) == b'&lt;p&gt;li &amp;amp; \t &#x27;seq&#x27; \n &lt;/p&gt;'
    assert reliq.encode("<p>li &amp; \t 'seq' \n </p>",full=True) == '&lt;p&gt;li &amp;amp&semi; &Tab; &#x27;seq&#x27; &NewLine; &lt;&sol;p&gt;'
    assert reliq.encode("<p>li &amp; \t 'seq' \n </p>",True,full=True) == b'&lt;p&gt;li &amp;amp&semi; &Tab; &#x27;seq&#x27; &NewLine; &lt;&sol;p&gt;'

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
    try:
        rq.json('.r li, a')
    except reliq.ScriptError:
        pass
    else:
        assert 0
    try:
        rq.json('.r li, .r a')
    except reliq.ScriptError:
        pass
    else:
        assert 0

    nav = rq.filter('nav')[0]
    n1 = nav[0].children(rel=True)[0]
    n2 = nav[0].children()[0]
    assert n1.rlvl == 1
    assert n2.rlvl == 2
    assert n1.rposition == 1
    assert n2.rposition == 2

    assert nav.ancestors()[1].rlvl == -2

    rq = reliq(html_data,ref="https://wikipedia.org")
    assert rq.json('.n.U [0] a | "%(href)v"')['n'] == 'https://wikipedia.org/index.html'
    assert rq.ref == "https://wikipedia.org"
    assert rq.ujoin('index.html/../name') == "https://wikipedia.org/name"
    assert rq.urljoin('https://wikipedia.org','index.html/../name') == "https://wikipedia.org/name"

    u = reliq('<base href="https://en.wikipedia.org"><a href="index.html">k</a>',ref="https://wikipedia.org")
    assert u.json('.n.U [0] a | "%(href)v"')['n'] == 'https://en.wikipedia.org/index.html'
    assert u.ref == "https://en.wikipedia.org"

    assert reliq('<base href="/loop" >',ref="https://g.xyz/").ref == 'https://g.xyz/loop'

print_run_many(test_many,1)
print_run_many(test_basic,1)
