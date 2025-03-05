# reliq-python

A python module for [reliq](https://github.com/TUVIMEN/reliq) library.

## Requirements

- [reliq](https://github.com/TUVIMEN/reliq)

## Installation

    pip install reliq

## Import

    from reliq import reliq

## Usage

```python
from reliq import reliq, ReliqError, reliqType

html = ""
with open('index.html','r') as f:
    html = f.read()

rq = reliq(html) #parse html
expr = reliq.expr(r"""
    div .user; {
        a href; {
            .name @ | "%i",
            .link @ | "%(href)v"
        },
        .score.u span .score,
        .info dl; {
            .key dt | "%i",
            .value dd | "%i"
        },
        .achievements.a li class=b>"achievement-" | "%i\n"
    }
""") #expressions can be compiled

users = []
links = []

#filter()
#   returns object holding list of results such object (plural type node)
#   behaves like an array, but can be converted to array with
#       self() - objects with lvl() = 0
#       children() - objects with lvl() = 1
#       descendants() - objects with lvl > 0
#       full() - same as indexing filter(), all objects

for i in rq.filter(r'table; tr').self()[:-2]:
    #"i"
    #
    #   A node has multiple types specified in reliqType flag
    #   It can be a plural, tag, comment, text, textempty, texterr
    #   or textall which will match to all text types

    #   It has a set of functions for getting its properties (most of which don't work for plural type):
    #       __str__()       all of the text creating node
    #       __len__()       same as len(i.descendants())
    #       tag()           tag name
    #       insides()       string containing contents inside tag or comment
    #       tag_count()     count of tags
    #       text_count()    count of text
    #       comment_count() count of comments
    #       lvl()           level in html structure
    #       attribsl()      number of attributes
    #       attribs()       returns dictionary of attributes
    #       type()          returns instance of reliqType that describes the type of node
    #       starttag()      head of the tag
    #       endtag()        tail of the tag, if the first option is set to True result will be stripped
    #       text()          combined text nodes inside the node from the first level, if first option
    #                           is set to True all text nodes will be used

    if i.type() is not reliqType.tag:
        continue

    if i.child_count() < 3 and i[0].tag() == "div" and i[0].starttag() == '<div>':
        continue

    #objects can be accessed as an array which is the same
    #as array returned by descendants() method
    link = i[5].attribs()['href']
    #link = i.descendants()[5].attribs()['href']
    if re.match('^https://$',link):
        links.append(link)
        continue

    #search() returns str, in this case expression is already compiled
    #but can be passed as a string
    user = json.loads(i.search(expr))
    users.append(user)

#get_data() returns data from which the html structure has been compiled

#if the second argument of filter() is True the returned
#object will use independent data, allowing garbage collector
#to free the previous unused data

try: #handle errors
    reliq.search('p / /','<p></p>')
except ReliqError:
    print("error")

#shows all the text nodes
print(rq[2].text(True))
#shows only the text nodes that are the direct children or self of rq[2]
print(rq[2].text())

#decodes html entities
reliq.decode('loop &amp; &lt &tdot; &#212')
```
## Projects using reliq in python

- [forumscraper](https://github.com/TUVIMEN/forumscraper)
- [lightnovelworld](https://github.com/TUVIMEN/lightnovelworld/)
