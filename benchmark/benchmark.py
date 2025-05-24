#!/usr/bin/env python

# inspired by https://github.com/rushter/selectolax/blob/master/examples/benchmark.py

# this downloads 1000 html files that weight 361MB for me
#    mkdir pages
#    for i in $(./ahrefs 99); do ucurl "$i" > "$(sed 's/^https:\/\//pages\//' <<< "$i")"; done

# faulty pages can be removed by running: ./benchmark.py test | xargs rm

"""
For each page, in seperate steps we extract:

1. Title
2. Number of script tag
3. The ``href`` attribute from all links
4. The content of the Meta description tag
5. The amount of tags with [ flex, relative, items-center, w-full, icon, lazyload, block, title ] classes
"""
# TODO
# 6. Most frequent attribute name with frequency
# 7. html size of first span tag where its insides begin with upper case letter, that is a descendand of li tag, which is a child of ul tag - ul; li child@; span i@bB>[A-Z]
# 8. Average size of blocks of a tags that have immediate siblings of a tags

import functools
import time
import os
import sys
from typing import Optional
from pathlib import Path
from dataclasses import dataclass

from bs4 import BeautifulSoup
from html5_parser import parse
from lxml.html import fromstring
from selectolax.parser import HTMLParser
from reliq import reliq
from selectolax.lexbor import LexborHTMLParser

popular_classes_list = [
    "flex",
    "relative",
    "items-center",
    "w-full",
    "icon",
    "lazyload",
    "block",
    "title",
]


@dataclass
class test_result:
    title: Optional[str]
    href_amount: list[str]
    script_amount: int
    description: Optional[str]
    popular_classes: int
    # freq_attribute: Tuple[str, int]
    # span_size: int
    # avg_a_blocks: float


def bs4_test(page, parseonly=False):
    tree = BeautifulSoup(page, "html.parser")
    # tree = BeautifulSoup(page, "lxml")

    if parseonly:
        return

    # 1
    title = tree.title.string

    # 2
    href_amount = 0
    for i in tree.find_all("a"):
        if len(i.attrs.get("href", "")) > 0:
            href_amount += 1

    # 3
    script_amount = len(tree.find_all("script"))

    # 4
    description = None
    meta_description = tree.find(
        "meta", attrs={"name": lambda x: x and x.lower() == "description"}
    )
    if meta_description:
        description = meta_description.get("content")

    # 5
    popular_classes = 0
    for i in popular_classes_list:
        # popular_classes += len(tree.find_all(class=i))
        popular_classes += len(tree.select("." + i))

    return test_result(title, href_amount, script_amount, description, popular_classes)


def html5_test(page, parseonly=False):
    tree = parse(page)

    if parseonly:
        return

    # 1
    title = tree.xpath("//title/text()")[0]

    # 2
    href_amount = 0
    for i in tree.xpath("//a[@href]"):
        if len(i.attrib.get("href", "")) > 0:
            href_amount += 1

    # 3
    script_amount = len(tree.xpath("//script"))

    # 4
    description = None
    meta_description = tree.xpath(
        '//meta[translate(@name,"ABCDEFGHIJKLMNOPQRSTUVWXYZ","abcdefghijklmnopqrstuvwxyz")="description"]'
    )
    if meta_description:
        description = meta_description[0].attrib.get("content")

    # 5
    popular_classes = 0
    for i in popular_classes_list:
        popular_classes += len(
            tree.xpath(
                '//*[contains(concat(" ",normalize-space(@class)," ")," ' + i + ' ")]'
            )
        )

    return test_result(title, href_amount, script_amount, description, popular_classes)


def lxml_test(page, parseonly=False):
    tree = fromstring(page)

    if parseonly:
        return

    # 1
    title = tree.xpath("//title/text()")[0]

    # 2
    href_amount = 0
    for i in tree.xpath("//a[@href]"):
        if len(i.attrib.get("href", "")) > 0:
            href_amount += 1

    # 3
    script_amount = len(tree.xpath("//script"))

    description = None
    meta_description = tree.xpath(
        '//meta[translate(@name,"ABCDEFGHIJKLMNOPQRSTUVWXYZ","abcdefghijklmnopqrstuvwxyz")="description"]'
    )
    if meta_description:
        description = meta_description[0].attrib.get("content")

    # 5
    popular_classes = 0
    for i in popular_classes_list:
        popular_classes += len(
            tree.xpath(
                '//*[contains(concat(" ",normalize-space(@class)," ")," ' + i + ' ")]'
            )
        )

    return test_result(title, href_amount, script_amount, description, popular_classes)


def selectolax_test(page, parseonly=False, lexbor=False):
    tree = LexborHTMLParser(page) if lexbor else HTMLParser(page)

    if parseonly:
        return

    # 1
    title = None
    title_node = tree.css_first("title")
    if title_node:
        title = title_node.text()

    # 2
    href_amount = 0
    for i in tree.css("a[href]"):
        c = i.attrs.get("href", "")
        if c is not None and len(c) > 0:
            href_amount += 1

    # 3
    script_amount = len(tree.css("script"))

    # 4
    description = None
    if lexbor:
        meta_description = tree.css_first('meta[name="description" i]')
    else:
        meta_description = tree.css_first('meta[name="description"]')
    if meta_description:
        description = meta_description.attrs.sget("content")

    # 5
    popular_classes = 0
    for i in popular_classes_list:
        popular_classes += len(tree.css("." + i))
    popular_classes = len(
        tree.css(
            ".flex, .relative, .items-center, .w-full, .icon, .lazyload, .block, .title"
        )
    )

    return test_result(title, href_amount, script_amount, description, popular_classes)


def reliq_test(page, parseonly=False):
    tree = reliq(page)

    if parseonly:
        return

    # 1
    title = tree.search(r'[0] title | "%Ui" decode "e"')

    # 2
    href_amount = len(tree.search(r'a href=>[1:] | "%(href)v\n"').split("\n")[:-1])

    # 3
    script_amount = len(tree.filter("script"))

    # 4
    description = None
    meta_description = tree.filter("[0] meta name=i>description")
    if len(meta_description) > 0:
        description = reliq.decode(
            meta_description[0].attrib.get("content"), no_nbsp=False
        )

    # 5
    popular_classes = len(
        tree.filter(
            "* .flex, * .relative, * .items-center, * .w-full, * .icon, * .lazyload, * .block, * .title"
        )
    )

    return test_result(title, href_amount, script_amount, description, popular_classes)


def tests_check_results(r):
    model = r["reliq"]

    tm = model
    # lxml cannot fathom that classes can be split in multiple attributes
    tm.popular_classes = r["lxml"].popular_classes
    assert r["bs4"] == tm
    assert r["lxml"] == tm

    for i in ["html5_parser", "modest", "lexbor"]:
        assert r[i].title == model.title
        assert r[i].description == model.description


def compare_test(page, testers):
    r = {}
    for name, tester in testers:
        r[name] = tester(page)

    tests_check_results(r)


def compare_tests(pages, testers):
    for path, page in pages:
        try:
            compare_test(page, testers)
        except:
            print(path)


def run_tests_r(pages, testers, parseonly=False):
    for name, tester in testers:
        start = time.time()

        for path, page in pages:
            tester(page, parseonly=parseonly)

        print("{}: {}".format(name, time.time() - start))


def run_tests(pages, testers):
    print("########### parse")
    run_tests_r(pages, testers, True)
    print("########### parse and process")
    run_tests_r(pages, testers, False)


def load_files(path):
    ret = []
    for i in os.scandir(path):
        if not i.is_file():
            continue
        with open(i.path, "r") as f:
            try:
                ret.append((i.path, f.read()))
            except:
                pass
    return ret


pages_path = Path("pages")
pages = load_files(pages_path)

testers = [
    (
        "bs4",
        bs4_test,
    ),
    (
        "html5_parser",
        html5_test,
    ),
    (
        "lxml",
        lxml_test,
    ),
    (
        "modest",
        selectolax_test,
    ),
    ("lexbor", functools.partial(selectolax_test, lexbor=True)),
    (
        "reliq",
        reliq_test,
    ),
]

if len(sys.argv) == 2 and sys.argv[1] == "test":
    compare_tests(pages, testers)
else:
    run_tests(pages, testers)
