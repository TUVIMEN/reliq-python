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
from reliq import reliq, ReliqError

html = ""
with open('index.html','r') as f:
    html = f.read()

rq = reliq(html) #parse html
expr = reliq.expr(r"""
    div .user; {
        a href; {
            .name * l@[0] | "%i"
            .link * l@[0] | "%(href)v"
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
images = []

#filter()
#   returns object holding list of results such object
#   behaves like an array, but can be converted to array with
#       self() - objects with lvl() 0
#       children() - objects with lvl() 1
#       descendants() - objects with lvl > 0
#       full() - same as indexing filter(), all objects

for i in rq.filter(r'table; tr').self()[:-2]:
    #"i"
    #   It has a set of functions for getting its properties:
    #       tag()           tag name
    #       insides()       string containing contents inside tag
    #       desc_count()   count of descendants
    #       lvl()           level in html structure
    #       attribsl()      number of attributes
    #       attribs()       returns dictionary of attributes

    if i.child_count() < 3 and i[0].tag() == "div":
        continue

    #objects can be accessed as an array which is the same
    #as array returned by descendants() method
    link = i[5].attribs()['href']
    if re.match('^https://$',href):
        links.append(link)
        continue

    #search() returns str, in this case expression is already compiled
    user = json.loads(i.search(expr))
    users.append(user)

#reliq objects have __str__ method
#get_data() returns data from which the html structure has been compiled

#if the second argument of filter() is True the returned
#object will use independent data, allowing garbage collector
#to free the previous unused data

#fsearch()
#   executes expression at parsing saving memory, and because
#   of that it supports only chain expressions i.e use of
#   grouping brackets and separating commas will throw an exception
for i in reliq.fsearch(r'ul; img src | "%(src)v\n"',html).split('\n')[:-1]:
    images.append(i)

try: #handle errors
    reliq.fsearch('p / /','<p></p>')
except ReliqError:
    print("error")
```
## Projects using reliq

- [forumscraper](https://github.com/TUVIMEN/forumscraper)
