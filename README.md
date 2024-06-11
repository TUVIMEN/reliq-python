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
#   behaves like an array, but can be converted to array
#   with unpack() method

#result can be accessed like an array
for i in rq.filter(r'table; tr')[:-2]:
    #"i"
    #   also can be accessed as an array of its children
    #   and it also works with unpack().
    #   It has a set of functions for getting its properties:
    #       tag()           tag name
    #       insides()       string containing contents inside tag
    #       child_count()   count of children
    #       lvl()           level in html structure
    #       attribsl()      number of attributes
    #       attribs()       returns dictionary of attributes

    if i.child_count() < 3 and i[0].tag() == "div":
        continue
    
    link = i[5].attribs()['href']
    if re.match('^https://$',href):
        links.append(link)
        continue

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
```
