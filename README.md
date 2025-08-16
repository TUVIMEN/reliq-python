# reliq-python

A python bindings for [reliq](https://github.com/TUVIMEN/reliq) library.

## Installation

    pip install reliq

## Benchmark

Benchmarks were inspired by [selectolax](https://github.com/rushter/selectolax/blob/master/examples/benchmark.py) and performed on 355MB, 896 files sample of most popular websites. You can find the benchmark script [here](benchmark/benchmark.py).

### Parsing

| Package             | Time     |
| --------------      | ----     |
| bs4                 | 121.615s |
| html5-parser        | 22.424s  |
| lxml                | 4.955s   |
| selectolax (modest) | 2.901s   |
| selectolax (lexbor) | 1.200s   |
| reliq               | 0.310s   |

### Collective memory usage of parsed trees

| Package             | Memory |
| --------------      | ----   |
| bs4                 | 2234MB |
| selectolax (lexbor) | 1666MB |
| selectolax (modest) | 1602MB |
| lxml                | 1274MB |
| html5-parser        | 1262MB |
| reliq               | 58MB   |

### Parsing and processing

| Package             | Time     |
| --------------      | ----     |
| bs4                 | 230.661s |
| html5-parser        | 31.138s  |
| lxml                | 14.010s  |
| selectolax (modest) | 4.291s   |
| reliq               | 2.974s   |
| selectolax (lexbor) | 2.628s   |

## Usage

### Code

```python
from reliq import reliq

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
        } |,
        .achievements.a li class=b>"achievement-" | "%i\n"
    }
""") #expressions can be compiled

users = []
links = []

for i in rq.filter(r'table; { tr, text@ iw>lisp }')[:-2]:
    # ignore comments and text nodes
    if i.type is not reliq.Type.tag:
        continue

    first_child = i[0]

    if first_child.desc_count < 3 and first_child.name == "div" and first_child.starttag == '<div>':
        continue

    link = first_child[2].attrib['href']
    if re.match('^https://$',link):
        links.append(link)
        continue

    #make sure that object is an ancestor of <main> tag
    for j in i.ancestors():
        if j.name == "main":
          break
    else:
      continue

    #search() returns str, in this case expression is already compiled
    #  but can be also passed as a str() or bytes(). If Path() is passed
    #  file will be read
    user = json.loads(i.search(expr))
    users.append(user)

try: #handle errors
    rq.search('p / /','<p></p>')
except reliq.ScriptError: # all errors inherit from reliq.Error
    print("error")

#get text from all text nodes that are descendants of object
print(rq[2].text_recursive)
#get text from all text nodes that are children of object
print(rq[2].text)

#decode html entities
reliq.decode('loop &amp; &lt &tdot; &#212')

#execute and convert to dictionary
rq.json(r"""
    .files * #files; ( li )( span .head ); {
        .type i class child@ | "%(class)v" / sed "s/^flaticon-//",
        .name @ | "%Dt" / trim sed "s/ ([^)]* [a-zA-Z][Bb])$//",
        .size @ | "%t" / sed 's/.* \(([^)]* [a-zA-Z][Bb])\)$/\1/; s/,//g; /^[0-9].* [a-zA-Z][bB]$/!d' "E"
    } |
""") #dict format is enforced and any incompatible expressions will raise reliq.ScriptError
```

### Import

Most is contained inside `reliq` class

```python
from reliq import reliq, RQ
```

### Initialization

`reliq` object takes an argument representing html, this can be `str()`, `bytes()`, `Path()` (file is read as `bytes`), `reliq()` or `None`.

```python
rq = reliq('<p>Example</p>') #passed directly

rq2 = reliq(Path('index.html')) #passed from file

rq3 = reliq(None) # empty object
rq4 = reliq() # empty object
```

If optional argument `ref` is a string it'll set url to the first base tag in html structure, and in case there isn't any it'll be set to `ref`.

```python
rq = reliq('<p>Example</p>')
rq.ref # None

rq2 = reliq(b'<p>Second example</p>',ref="http://en.wikipedia.org")
rq2.ref # http://en.wikipedia.org

rq3 = reliq(b'<base href="https://wikipedia.org"><p>Second example</p>',ref="http://en.wikipedia.org")
rq3.ref # https://wikipedia.org

rq4 = reliq(b'<base href="https://wikipedia.org"><p>Second example</p>',ref="")
rq4.ref # https://wikipedia.org
```

### Types

`reliq` can have 5 types that change the behaviour of methods.

Calling `type` property on object e.g. `rq.type` returns instance of `reliq.Type(Flag)`.

#### empty

Gets returned from either `reliq(None)` or `reliq.filter()` that matches nothing, makes all methods return default values.

#### unknown

Similar to `empty` but should never happen

#### struct

Returned by successful initialization e.g.

```python
reliq('<p>Example</p>')
```

#### list

Returned by `reliq.filter()` that succeeds

#### single

Returned by axis methods or by accessing the object like a list.

The type itself is a grouping of more specific types:

 - tag
 - comment
 - textempty (text made only of whitespaces)
 - texterr (text where an html error occurred)
 - text
 - textall (grouping of text types)

### get_data(raw=False) -> str|bytes

Returns the same html from which the object was compiled.

If first argument is `True` or `raw=True` returns `bytes`.

```python
data = Path('index.html').read_bytes

rq = reliq(data)
x = rq[0][2][1][8]

# if both objects are bytes() then their ids should be the same
x.get_data(True) is data
```

### special methods

#### \_\_bytes\_\_ and \_\_str\_\_

Full string representation of current object

```python
rq = reliq("""
  <h1><b>H</b>1</h1>
  <h2>N2</h2>
  <h2>N3</h2>
""")

str(rq) # struct
# '\n  <h1><b>H</b>1</h1>\n  <h2>N2</h2>\n  <h2>N3</h2>\n'

str(rq.filter('h2')) # list
# '<h2>N2</h2><h2>N3</h2>'

str(rq[0]) # single
# '<h1><b>H</b>1</h1>'

str(reliq()) # empty
# ''
```

#### \_\_getitem\_\_

For `single` indexes results from `children()` axis, otherwise from `self()` axis

```python
rq = reliq('<div><p>1</p> Text <b>H</b></div>')

first = rq[0] # struct
# <div>

first[1] # single
# <b>

r = first.filter('( text@ * )( * ) child@')
r[1] # list
# " Text " obj

r[2] == first[1]
```

#### \_\_len\_\_

Amount of objects returned from `__getitem__`

### ref and ref_raw

`ref -> str`

`ref_raw -> bytes`

They return saved reference url at initialization.

```python
rq = reliq('',ref="http://en.wikipedia.org")
rq.ref # "http://en.wikipedia.org"
rq.ref_raw # b"http://en.wikipedia.org"
```

### properties of single

Calling these properties for types other than `single` returns their default values.

`lvl -> int` level in html structure

`rlvl -> int` level in html structure, relative to parent

`position -> int` position in html structure

`rposition -> int` position in html structure, relative to parent

Calling some properties makes sense only for certain types.

#### tag

`tag_count -> int` count of tags

`text_count -> int` count of text

`comment_count -> int` count of comments

`desc_count -> int` count of descendants

`attribl -> int` number of attributes

----

`attrib -> dict` dictionary of attributes

----

These return `None` only if called from `empty` type. They also have `_raw` counterparts that return `bytes` e.g. `text_recursive_raw -> Optional[bytes]`, `name_raw -> Optional[bytes]`

`insides -> Optional[str]` string containing contents inside tag or comment

`name -> Optional[str]` tag name e.g. `'div'`

`starttag -> Optional[str]` head of the tag e.g. `'<div class="user">'`

`endtag -> Optional[str]` tail of the tag e.g. `'</div>'`

`endtag_strip -> Optional[str]` tail of the tag, stripped of `<` and `>` e.g. `'/div'`

`text -> Optional[str]` text of children

`text_recursive -> Optional[str]` text of descendants

```python
rq = reliq("""
  <main>
    <ul>
      <a>
        <li>L1</li>
      </a>
      <li>L2</li>
    </ul>
  </main>
""")

ul = rq[0][0]
a = ul[0]
li1 = a[0]
li2 = ul[1]

ul.name
# 'ul'

ul.name_raw
# b'ul'

ul.lvl
# 1

li1.lvl
# 3

ul.text
# '\n      \n      \n    '

ul.text_recursive
# '\n      \n        L1\n      \n      L2\n    '

a.insides
# '\n        <li>L1</li>\n      '
```

#### comment

Comments can either return their string representation or insides by `insides` property.

```python
c = reliq('<!-- Comment -->').self(type=None)[0]

c.insides
# ' Comment '

bytes(c)
# b'<!-- Comment -->'

str(c)
# '<!-- Comment -->'
```

#### text

Text can only be converted to string

```python
t = reliq('Example').self(type=None)[0]

str(t)
# 'Example'
```
### axes

Convert `reliq` objects into a list or a generator of `single` type objects.

If their first argument is set to `True` or `gen=True` is passed, a generator is returned, otherwise a list.

By default they filter node types to only `reliq.Type.tag`, this can be changed by setting the `type` argument e.g. `type=reliq.Type.comment|reliq.Type.texterr`. If type is set to `None` all types are matched.

If `rel=True` is passed returned objects will be relative to object from which they were matched.

```python
rq = reliq("""
  <!DOCTYPE html>
  <head>
    <title>Title</title>
  </head>
  <body>
    <section>
      <h1>Title</h1>
      <p>A</p>
    </section>
    <h2>List</h2>
    <ul>
      <li>A</li>
      <li>B</li>
      <li>C</li>
    </ul>
    <section>
      TEXT
    </section>
  </body>
""")
```

#### everything

`everything()` gets all elements in structure, no matter the previous context.

```python
#traverse everything through generator
for i in rq.everything(True):
  print(str(i))
```

#### self

`self()` gets the context itself, single element for `single` type, list of the `list` type and elements with `.lvl == 0` for `struct` type.

By default filtered type depends on object type it was called for, for `single` and `list` types are unfiltered, only `struct` type enforces `type=reliq.Type.tag`.

```python
# rq is a reliq.Type.struct object

rq.self()
# [<tag head>, <tag body>]

rq.self(type=None)
# [<textempty>, <comment>, <textempty>, <tag head>, <textempty>, <tag body>]

rq.self(type=reliq.Type.tag|reliq.Type.comment)
# [<comment>,<tag head>, <tag body>]

# ls is a reliq.Type.list object that has comments and text types
ls = rq.filter('[:3] ( comment@ * )( text@ * )')

ls.self()
# [<comment>, <text>, <text>, <text>]

ls.self(type=reliq.Type.tag|reliq.Type.comment)
# [<comment>]

# body is a reliq.Type.single object
body = rq[1].self()

len(body.self())
# 1

body.self()[0].name
# "body"
```
#### children

`children()` gets all nodes of the context that have level relative to them equal to 1.

```python
# struct
rq.children()
# [<tag title>, <tag section>, <tag h2>, <tag ul>, <tag section>]

# list
rq.filter('head, ul').children()
# [<tag title>, <tag li>, <tag li>, <tag li>]

# single
first_section = rq[1][0]
first_section.children()
# [<tag h1>, <tag p>]
```

#### descendants

`descendants()` gets all nodes of the context that have level relative to them greater or equal to 1.

```python
# struct
rq.descendants()
# [<tag title>, <tag section>, <tag h1>, <tag p>, <tag h2>, <tag ul>, <tag li>, <tag li>, <tag li>, <tag section>]

# list
rq.filter('[0] section').descendants()
# [<tag h1>, <tag p>]

# single
rq[1][0].descendants()
# [<tag h1>, <tag p>]
```

#### full

`full()` gets all nodes of the context and all nodes below them (like calling `self()` and `descendants()` at once).

```python
# struct
rq.full()
# [<tag head>, <tag title>, <tag body>, <tag section>, <tag h1>, <tag p>, <tag h2>, <tag ul>, <tag li>, <tag li>, <tag li>, <tag section>]

# list
rq.filter('[0] section').descendants()
# [<tag section>, <tag h1>, <tag p>]

# single
rq[1][0].descendants()
# [<tag section>, <tag h1>, <tag p>]
```

#### parent

`parent()` gets parent of context nodes. Doesn't work for `struct` type.

```python
# list
rq.filter('li').parent()
# [<tag ul>, <tag ul>, <tag ul>]

# single
rq[1][2][0].parent()
# [<tag li>]

# single
rq[0].parent() # top level nodes don't have parents
# []
```

#### rparent

`rparent()` behaves like `parent()` but returns the parent to which the current object is relative to. Doesn't work for `struct` type.

It doesn't take `rel` argument, returned objects are always relative.

#### ancestors

`ancestors()` gets ancestors of context nodes. Doesn't work for `struct` type.

```python
# list
rq.filter('li').ancestors()
# [<tag ul>, <tag body>, <tag ul>, <tag body>, <tag ul>, <tag body>]

# single
rq[1][2][0].ancestors()
# [<tag ul>, <tag body>]

# first element of ancestors() should be the same as for parent()
rq[1][2][0].ancestors()[0].name == rq[1][2][0].parent()[0].name

# single
rq[0].ancestors() # top level nodes don't have ancestors
# []
```

#### before

`before()` gets all nodes that have lower `.position` property than context nodes. Doesn't work for `struct` type.

```python
# list
rq.filter('[0] title, [1] section').before()
# [<tag head>, <tag li>, <tag li>, <tag li>, <tag ul>, <tag h2>, <tag p>, <tag h1>, <tag section>, <tag body>, <tag title>, <tag head>]

# single
title = rq[0][0]
title.before()
# [<tag head>]

# single
second_section = rq[1][3]
second_section.before()
# [<tag li>, <tag li>, <tag li>, <tag ul>, <tag h2>, <tag p>, <tag h1>, <tag section>, <tag body>, <tag title>, <tag head>]

# single
head = rq[0]
head.before() #first element doesn't have any nodes before it
# []
```

#### preceding

`preceding()` is similar to `before()` but ignores ancestors. Doesn't work for `struct` type.

```python
# list
rq.filter('[0] title, [1] section').preceding()
# [<tag li>, <tag li>, <tag li>, <tag ul>, <tag h2>, <tag p>, <tag h1>, <tag section>, <tag title>, <tag head>]

# single
title = rq[0][0]
title.preceding() # all tags before it are it's ancestors
# []

# single
second_section = rq[1][3]
second_section.preceding()
# [<tag li>, <tag li>, <tag li>, <tag ul>, <tag h2>, <tag p>, <tag h1>, <tag section>, <tag title>, <tag head>]
```

#### after

`after()` gets all nodes that have higher `.position` property than context nodes. Doesn't work for `struct` type.

```python
# list
rq.filter('h2, ul').after()
# [<tag ul>, <tag li>, <tag li>, <tag li>, <tag section>, <tag li>, <tag li>, <tag li>, <tag section>]

# single
h2 = rq[1][1]
h2.after()
# [<tag ul>, <tag li>, <tag li>, <tag li>, <tag section>]

# single
ul = rq[1][2]
ul.after()
# [<tag li>, <tag li>, <tag li>, <tag section>]

# single
third_section = rq[1][3] # last element
third_section.after()
# []
```

#### subsequent

`subsequent()` is similar to `after()` but ignores descendants. Doesn't work for `struct` type.

```python
# list
rq.filter('h2, ul').subsequent()
# [<tag ul>, <tag li>, <tag li>, <tag li>, <tag section>, <tag section>]

# single
h2 = rq[1][1]
h2.subsequent()
# [<tag ul>, <tag li>, <tag li>, <tag li>, <tag section>]

# single
ul = rq[1][2]
ul.subsequent()
# [<tag section>]
```

#### siblings_preceding

`siblings_preceding()` gets nodes on the same level as context nodes but before them and limited to their parent. Doesn't work for `struct` type.

If `full=True` is passed descendants of siblings will also be matched.

```python
# list
rq.filter('ul, h2').siblings_preceding()
# [<tag h2>, <tag section>, <tag section>]

# single
h2 = rq[1][1]

h2.siblings_preceding()
# [<tag section>]
h2.siblings_preceding(full=True)
# [<tag p>, <tag h1>, <tag section>]

# single
ul = rq[1][2]

ul.siblings_preceding()
# [<tag h2>, <tag section>]
ul.siblings_preceding(full=True)
# [<tag h2>, <tag p>, <tag h1>, <tag section>]
```

#### siblings_subsequent

`siblings_preceding()` gets nodes on the same level as context nodes but after them and limited to their parent. Doesn't work for `struct` type.

If `full=True` is passed descendants of siblings will also be matched.

```python
# list
rq.filter('ul, h2').siblings_subsequent()
# [<tag h2>, <tag section>, <tag section>]

# single
h2 = rq[1][1]

h2.siblings_subsequent()
# [<tag ul>, <tag section>]
h2.siblings_subsequent(full=True)
# [<tag ul>, <tag li>, <tag li>, <tag li>, <tag section>]

# single
ul = rq[1][2]

ul.siblings_subsequent()
# [<tag section>]
ul.siblings_subsequent(full=True)
# [<tag section>]
```

#### siblings

`siblings()` returns merged output of `siblings_preceding()` and `siblings_subsequent()`.

### expr

`reliq.expr` is a class that compiles expressions, it accepts only one argument that can be a `str()`, `bytes()` or `Path()`.

If `Path()` argument is specified, file under it will be read with `Path.read_bytes()`.

```python
# str
reliq.expr(r'table; { tr .name; li | "%(title)v\n", th }')

# bytes
reliq.expr(rb'li')

# file from Path
reliq.expr(Path('expression.reliq'))
```

### search

`search()` executes expression in the first argument and returns `str()` or `bytes` if second argument is `True` or `raw=True`.

Expression can be passed both as compiled object of `reliq.expr` or its representation in `str()`, `bytes()` or `Path()` that will be compiled in function.

```python
rq = reliq('<span class=name data-user-id=1282>User</span><p>Title: N1ase</p>')

rq.search(r'p')
# '<p>Title: N1ase</p>\n'

rq.search(r'p', True)
# b'<p>Title: N1ase</p>\n'

rq.search(r'p', raw=True)
# b'<p>Title: N1ase</p>\n'

rq.search(r"""
  span .name; {
    .id.u @ | "%(data-user-id)v",
    .name @ | "%t"
  },
  .title p | "%i" sed "s/^Title: //"
""",True)
# b'{"id":1282,"name":"User","title":"N1ase"}'

rq.search(Path('expression.reliq'))
```

### json

Similar to `search()` but returns `dict()` while validating expression.

### filter

`filter()` executes expression in the first argument and returns `reliq` object of `list` type or `empty` type if nothing has been found.

If second argument is `True` or `independent=True` then returned object will be completely independent from the one the function was called on. A new HTML string representation will be created, and structure will be copied and shifted to new string, levels will also change.

Expression can be passed both as compiled object of `reliq.expr` or its representation in `str()`, `bytes()` or `Path()` that will be compiled in function.

Any field, formatting or string conversion in expression will be ignored, only objects used in them will be returned.

```python
rq = reliq('<span class=name data-user-id=1282>User</span><p>Title: N1ase</p>')

rq.filter(r'p').self()
# [<tag p>]

rq.filter(r'p').type
# reliq.Type.list

rq.filter(r'p').get_data()
# '<span class=name data-user-id=1282>User</span><p>Title: N1ase</p>'

rq.filter(r'p',True).get_data()
# '<p>Title: N1ase</p>'

rq.filter(r'nothing').type
# reliq.Type.empty

rq.filter(r"""
  span .name; {
    .id.u @ | "%(data-user-id)v",
    .name @ | "%t"
  },
  .title p | "%i" sed "s/^Title: //"
""")
# [<tag span>, <tag span>, <tag p>]

rq.filter(Path('expression.reliq'))
```

### Encoding and decoding html entities

`decode()` decodes html entities in first argument of `str()` or `bytes()`, and returns `str()` or `bytes()` if second argument is `True` or `raw=True`.

By default `&nbsp;` is translated to space, this can be changed by setting `no_nbsp=False`.

`encode()` does the opposite of `decode()` in the same fashion.

By default only special characters are encoded i.e. `<`, `>`, `"`, `'`, `&`. If `full=True` is set everything possible will be converted to html entities (quite slow approach).

```python
reliq.decode(r"text &amp; &lt &tdot; &#212")
# "loop & <  ⃛⃛ Ô"

reliq.decode(r"text &amp; &lt &tdot; &#212",True)
# b'text & <  \xe2\x83\x9b\xe2\x83\x9b \xc3\x94'

reliq.decode(r"text &amp; &lt &tdot; &#212",raw=True)
# b'text & <  \xe2\x83\x9b\xe2\x83\x9b \xc3\x94'

reliq.decode('ex&nbsp;t')
# "ex t"

reliq.decode('ex&nbsp;t',no_nbsp=False)
# 'ex\xa0t'

reliq.decode('ex&nbsp;t',True,no_nbsp=False)
# b'ex\xc2\xa0t'

reliq.encode("<p>li &amp; \t 'seq' \n </p>")
# '&lt;p&gt;li &amp;amp; \t &#x27;seq&#x27; \n &lt;/p&gt;'

reliq.encode("<p>li &amp; \t 'seq' \n </p>",True)
# b'&lt;p&gt;li &amp;amp; \t &#x27;seq&#x27; \n &lt;/p&gt;'

reliq.encode("<p>li &amp; \t 'seq' \n </p>",raw=True)
# b'&lt;p&gt;li &amp;amp; \t &#x27;seq&#x27; \n &lt;/p&gt;'

reliq.encode("<p>li &amp; \t 'seq' \n </p>",full=True)
# '&lt;p&gt;li &amp;amp&semi; &Tab; &#x27;seq&#x27; &NewLine; &lt;&sol;p&gt;'

reliq.encode("<p>li &amp; \t 'seq' \n </p>",True,full=True)
# b'&lt;p&gt;li &amp;amp&semi; &Tab; &#x27;seq&#x27; &NewLine; &lt;&sol;p&gt;'
```

### URLS

`urljoin` work like `urllib.parse.urljoin` but it can take argument's in `bytes` and returns `str` or `bytes` depending on `raw` argument.

`ujoin` works the same way as `urljoin` but `ref` argument is set to default reference url in structure.

### Errors

All errors are instances of `reliq.Error`.

`reliq.SystemError` is raised when kernel fails (you should assume it doesn't happen).

`reliq.HtmlError` is raised when html structure exceeds limits.

`reliq.ScriptError` is raised when incorrect script is compiled.

```python
try:
  reliq('<div>'*8193) # 8192 passes :D
except reliq.HtmlError:
  print('html depth limit exceeded')

try:
  reliq.expr('| |')
except reliq.ScriptError:
  print('incorrect expression')
```

### Relativity

`list` and `single` type object also stores a pointer to node that object is relative to in context i.e. `rq.filter(r'body; nav')` will return `nav` objects that were found in `body` tags, `nav` objects might not be direct siblings of `body` tags but because of relativity their relation is not lost.

`reliq.filter()` always keeps the relativity.

By default axis functions don't change relativity unless `rel=True` is passed.

```python
rq = reliq("""
  <body>
    <nav>
      <ul>
        <li> A </li>
        <li> B </li>
        <li> C </li>
      </ul>
    </nav>
  </body>
""")

li = rq[0][0][0][1] # not relative

li_self = rq.filter('li i@w>"B"')[0] # relative to itself

li_rel = rq.filter('nav; li i@w>"B"')[0] # relative to nav

# .rlvl and .rposition for non relative objects return same values as .lvl and .position

li.lvl
# 3
li_rel.lvl
# 3

li.rlvl
# 3
li_rel.rlvl
# 2

li.position
# 10
li_rel.position
# 10

li.rposition
# 10
li_rel.rposition
# 9

nav = rq[0][0]
for i in nav.descendants(rel=True):
    if i.rlvl == 2 and i.name == 'li':
        print(i.lvl,i.rlvl)
        # 3 2
        break

nav_rel = li_rel.rparent()[0] # nav element relative to li

nav_rel.rlvl
# -2
nav_rel.rposition
# -7
```

### Project wrapper

Expressions can grow into considerable sizes so it's beneficial to save them in separate directories and cache them. `RQ` function returns a new `reliq` type that keeps track of cache and directory of the script that has called this function.

```python
from reliq import RQ

reliq = RQ(cached=True)

rq = reliq('<p>Alive!</p>')
print(rq)
```

It takes two optional arguments `def RQ(path="", cached=False)`. If `cached` is set, compiled expressions will be saved and reused.

If `path` is not an absolute path it will be merged with directory of the calling function. When in any function that takes expression argument a `Path()` is passed it will be relative to first declared `path` argument. Exceptions to that are paths that are absolute or begin with `./` or `../`.

This function should be used by packages to save reliq expressions under their directories without polluting the general `reliq` object space. After the first declaration of this type it should be reused everywhere in project.

## Projects using reliq in python

- [forumscraper](https://github.com/TUVIMEN/forumscraper)
- [fakexy](https://github.com/TUVIMEN/fakexy)
- [1337x-scraper](https://github.com/TUVIMEN/1337x-scraper)
- [blu-ray-scraper](https://github.com/TUVIMEN/blu-ray-scraper)
- [9gag-scraper](https://github.com/TUVIMEN/9gag-scraper)
