#!/usr/bin/env python3
# by Dominik Stanisław Suchora <hexderm@gmail.com>
# License: GNU GPLv3

import os
from ctypes import *
#import ctypes.util
import typing
from typing import Optional, Tuple, Callable, Generator
from enum import Flag, auto
from itertools import chain

import json
from pathlib import Path

libreliq_name = 'libreliq.so'
libreliq_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),libreliq_name)
if not os.path.exists(libreliq_path):
    libreliq_path = libreliq_name
libreliq = CDLL(libreliq_path)

c_uintptr = c_uint64 if sizeof(c_void_p) == 8 else c_uint32

UINT32_MAX = 4294967295 # (uint32_t)-1

def strconv(string, raw: bool) -> str|bytes:
    if isinstance(string,str):
        if raw:
            return string.encode('utf-8')
        else:
            return string
    else:
        string = bytes(string)
        if raw:
            return string
        else:
            return string.decode()

#cstdlib = CDLL(ctypes.util.find_library("c"))

class reliq_str():
    def __init__(self,string: str|bytes|Path|c_void_p,size=0):
        if isinstance(string,str):
            string = string.encode("utf-8")
        elif isinstance(string,Path):
            string = string.read_bytes()

        if isinstance(string,bytes) and size == 0:
            size = len(string)

        self.string = string
        self.data = string

        self.size = size

    def __bytes__(self):
        string = self.string
        if isinstance(string,c_void_p) or isinstance(string,int):
            string = string_at(string,self.size)
        return string

    def __str__(self):
        return bytes(self).decode()

    def __del__(self):
        if isinstance(self.string,c_void_p):
            libreliq.reliq_std_free(self.string,0)

class _reliq_cstr_struct(Structure):
    _fields_ = [('b',c_void_p),('s',c_size_t)]

    def __bytes__(self):
        return string_at(self.b,self.s)

    def __str__(self):
        return bytes(self).decode()

class _reliq_str_struct(_reliq_cstr_struct):
    pass

class _reliq_compressed_struct(Structure):
    _pack_ = 1
    _fields_ = [("hnode",c_uint32),
                ("parent",c_uintptr)]

class _reliq_field_type_arg_union(Union):
    _fields_ = [("s",_reliq_str_struct),
                ("u",c_uint64),
                ("i",c_int64),
                ("d",c_double)]

class _reliq_field_type_arg_struct(Structure):
    _fields_ = [("v",_reliq_field_type_arg_union),
                ("type",c_uint8)]

class _reliq_field_type_struct(Structure):
    pass

_reliq_field_type_struct_fields_ = [("name",_reliq_str_struct),
        ("args",POINTER(_reliq_field_type_arg_struct)),
        ("subtypes",_reliq_field_type_struct),
        ("argsl",c_size_t),
        ("subtypesl",c_size_t)]

class _reliq_field_struct(Structure):
    _fields_ = [("name",_reliq_str_struct),
                ("annotation",_reliq_str_struct),
                ("types",POINTER(_reliq_field_type_struct)),
                ("typesl",c_size_t),
                ("isset",c_uint8)]

class _reliq_scheme_field_struct(Structure):
    _fields_ = [("field",POINTER(_reliq_field_struct)),
                 ("lvl",c_uint16),
                 ("type",c_uint8,2)]

class _reliq_scheme_struct(Structure):
    _fields_ = [("fields",POINTER(_reliq_scheme_field_struct)),
                ("fieldsl",c_size_t),
                ("leaking",c_uint8,1),
                ("repeating",c_uint8,1)]


class reliq_compressed_list():
    def __init__(self, nodes: c_void_p, compressed: POINTER(_reliq_compressed_struct), size: c_size_t):
        self.compressed = cast(compressed,POINTER(_reliq_compressed_struct))
        self.size = size
        self.nodes = nodes

    def iter(self):
        i = 0
        size = self.size.value
        compressed = self.compressed
        while i < size:
            c = compressed[i]
            if c.hnode >= UINT32_MAX-6:
                i += 1
                continue

            hnode = self.nodes+c.hnode*chnode_sz
            parent = None
            if c.parent != UINT32_MAX:
                parent = self.nodes+(c.parent*chnode_sz)
            i += 1
            yield hnode, parent

    def __del__(self):
        if self.compressed is not None:
            libreliq.reliq_std_free(self.compressed,0)

class reliq_single:
    def __init__(self, rq: "reliq", hnode: c_void_p, parent: c_void_p):
        self.chnode = hnode
        self._hnode_d = None
        self.cparent = parent
        self._parent_d = None
        self.rq = rq.struct

    @property
    def position(self):
        return (self.chnode-self.rq.struct.nodes)//chnode_sz

    @property
    def rposition(self):
        parent = self.cparent
        if parent is None:
            return self.position
        return (self.chnode-parent)//chnode_sz

    @property
    def hnode(self):
        if self._hnode_d is not None:
            return self._hnode_d
        self._hnode_d = chnode_conv(self.rq.struct,self.chnode)
        return self._hnode_d

    @property
    def parent(self):
        if self.cparent is None:
            return None
        if self._parent_d is not None:
            return self._parent_d
        self._parent_d = chnode_conv(self.rq.struct,self.cparent)
        return self._parent_d

class reliqType(Flag):
    empty = auto()

    struct = auto()

    list = auto()

    plural = struct|list

    tag = auto()
    textempty = auto()
    texterr = auto()
    text = auto()
    textall = textempty|texterr|text
    comment = auto()
    single = tag|textempty|texterr|text|comment

    unknown = auto()

class _reliq_attrib_struct(Structure):
    _fields_ = [('key',_reliq_cstr_struct),('value',_reliq_cstr_struct)]

class _reliq_hnode_struct(Structure):
    _fields_ = [('all',_reliq_cstr_struct),
                ('tag',_reliq_cstr_struct),
                ('insides',_reliq_cstr_struct),
                ('attribs',c_void_p),
                ('attribsl',c_uint32),
                ('tag_count',c_uint32),
                ('text_count',c_uint32),
                ('comment_count',c_uint32),
                ('lvl',c_uint16),
                ('type',c_uint8)]

    @property
    def desc(self) -> int:
        return self.tag_count+self.text_count+self.comment_count

    @property
    def ntype(self) -> reliqType:
        match self.type:
            case 0:
                return reliqType.tag
            case 1:
                return reliqType.comment
            case 2:
                return reliqType.text
            case 3:
                return reliqType.textempty
            case 4:
                return reliqType.texterr

        return reliqType.unknown

    def __bytes__(self):
        return string_at(self.all.b,self.all.s)

    def __str__(self):
        return bytes(self).decode()

class _reliq_error_struct(Structure):
    _fields_ = [('msg',c_char*512),('code',c_int)]

class _reliq_url_struct(Structure):
    _fields_ = [('url',_reliq_str_struct),
                ('scheme',_reliq_cstr_struct),
                ('netloc',_reliq_cstr_struct),
                ('path',_reliq_cstr_struct),
                ('params',_reliq_cstr_struct),
                ('query',_reliq_cstr_struct),
                ('fragment',_reliq_cstr_struct),
                ('allocated',c_size_t)]

class _reliq_struct(Structure):
    _fields_ = [('url',_reliq_url_struct),
                ('freedata',c_void_p),
                ('data',c_void_p),
                ('nodes',c_void_p),
                ('attribs',c_void_p),
                ('datal',c_size_t),
                ('nodesl',c_size_t),
                ('attribsl',c_size_t)]

libreliq_functions = [
    (
		libreliq.reliq_init,
		POINTER(_reliq_error_struct),
		[c_void_p,c_size_t,POINTER(_reliq_struct)]
    ),(
		libreliq.reliq_free,
		c_int,
		[POINTER(_reliq_struct)]
    ),(
        libreliq.reliq_ecomp,
        POINTER(_reliq_error_struct),
        [c_void_p,c_size_t,POINTER(c_void_p)]
    ),(
        libreliq.reliq_efree,
        None,
        [c_void_p]
    ),(
		libreliq.reliq_exec,
		POINTER(_reliq_error_struct),
		[POINTER(_reliq_struct),POINTER(_reliq_compressed_struct),c_size_t,c_void_p,POINTER(c_void_p),POINTER(c_size_t)]
    ),(
		libreliq.reliq_exec_str,
		POINTER(_reliq_error_struct),
		[POINTER(_reliq_struct),POINTER(_reliq_compressed_struct),c_size_t,c_void_p,POINTER(c_void_p),POINTER(c_size_t)]
    ),(
        libreliq.reliq_from_compressed,
        _reliq_struct,
        [c_void_p,c_size_t,POINTER(_reliq_struct)]
    ),(
        libreliq.reliq_from_compressed_independent,
        _reliq_struct,
        [c_void_p,c_size_t,POINTER(_reliq_struct)]
    ),(
        libreliq.reliq_chnode_conv,
        None,
        [POINTER(_reliq_struct),c_void_p,POINTER(_reliq_hnode_struct)]
    ),(
        libreliq.reliq_cattrib_conv,
        None,
        [POINTER(_reliq_struct),c_void_p,POINTER(_reliq_attrib_struct)]
    ),(
        libreliq.reliq_hnode_starttag,
        c_void_p,
        [POINTER(_reliq_hnode_struct),POINTER(c_size_t)]
    ),(
        libreliq.reliq_hnode_endtag,
        c_void_p,
        [POINTER(_reliq_hnode_struct),POINTER(c_size_t)]
    ),(
        libreliq.reliq_hnode_endtag_strip,
        c_void_p,
        [POINTER(_reliq_hnode_struct),POINTER(c_size_t)]
    ),(
        libreliq.reliq_std_free,
        c_int,
        [c_void_p,c_size_t]
    ),(
        libreliq.reliq_decode_entities_str,
        None,
        [c_void_p,c_size_t,POINTER(c_void_p),POINTER(c_size_t),c_bool]
    ),(
        libreliq.reliq_encode_entities_str,
        None,
        [c_void_p,c_size_t,POINTER(c_void_p),POINTER(c_size_t),c_bool]
    ),(
        libreliq.reliq_scheme,
        _reliq_scheme_struct,
        [c_void_p]
    ),(
        libreliq.reliq_scheme_free,
        None,
        [POINTER(_reliq_scheme_struct)]
    ),(
        libreliq.reliq_set_url,
        None,
        [POINTER(_reliq_struct),c_char_p,c_size_t]
    ),(
        libreliq.reliq_url_parse,
        None,
        [c_char_p,c_size_t,c_char_p,c_size_t,c_bool,POINTER(_reliq_url_struct)]
    ),(
        libreliq.reliq_url_join,
        None,
        [POINTER(_reliq_url_struct),POINTER(_reliq_url_struct),POINTER(_reliq_url_struct)]
    ),(
        libreliq.reliq_url_free,
        None,
        [POINTER(_reliq_url_struct)]
    )
]

chnode_sz = c_uint8.in_dll(libreliq,"reliq_chnode_sz").value
cattrib_sz = c_uint8.in_dll(libreliq,"reliq_cattrib_sz").value

def def_functions(functions):
    for i in functions:
        i[0].restype = i[1]
        i[0].argtypes = i[2]

def_functions(libreliq_functions)

def chnode_conv(rq: _reliq_struct, s: c_void_p) -> _reliq_hnode_struct:
    ret = _reliq_hnode_struct()
    libreliq.reliq_chnode_conv(byref(rq),s,byref(ret))
    return ret

class reliq_struct():
    def __init__(self,struct: _reliq_struct):
        self.struct = struct

    def __del__(self):
        libreliq.reliq_free(byref(self.struct))

def tobytes(text: bytes|str, encoding="utf-8") -> bytes:
    if isinstance(text,bytes):
        return text
    return text.encode(encoding)

class reliqExpr():
    @staticmethod
    def scriptbytes(x):
        if isinstance(x,Path):
            return x.read_bytes()
        return tobytes(x)

    def __init__(self,script: str|bytes|Path):
        s = self.scriptbytes(script)

        self.scheme = None
        self.expr = None

        expr = c_void_p()
        err = libreliq.reliq_ecomp(cast(s,c_void_p),len(s),byref(expr))
        if err:
            raise reliq._create_error(err)

        self.expr = expr

    def _get_scheme(self):
        if self.expr is None:
            return

        scheme = libreliq.reliq_scheme(self.expr)
        r = (scheme.leaking,scheme.repeating)
        libreliq.reliq_scheme_free(byref(scheme))

        return r

    def correct_scheme(self):
        if self.scheme is None:
            self.scheme = self._get_scheme()

        if self.scheme[0]:
            raise reliq.ScriptError("expression is leaking")
        if self.scheme[1]:
            raise reliq.ScriptError("expression has repeating field names")

    def __del__(self):
        if self.expr is not None:
            libreliq.reliq_efree(self.expr)


class reliq():
    @classmethod
    def _new(cls,html):
        return cls(html)

    @classmethod
    def _init_independent(cls,data,struct,ref):
        ret = cls(None,ref=ref)
        ret.data = data
        ret.struct = struct
        return ret

    @classmethod
    def _init_single(cls, self, hnode: c_void_p, parent: c_void_p) -> 'reliq':
        ret = cls(self)
        ret.compressed = None
        ret.single = reliq_single(ret,hnode,parent)
        return ret

    def __init__(self,html: Optional[typing.Union[str,bytes,Path,'reliq']]=None,ref: Optional[str|bytes]=None):
        if isinstance(html,reliq):
            self.data = html.data
            self.struct = html.struct
            self.single = html.single
            self.compressed = html.compressed
            return

        self.data: Optional[reliq_str] = None
        self.struct: Optional[reliq_struct] = None
        self.single: Optional[reliq_single] = None
        self.compressed: Optional[reliq_compressed_list] = None

        if html is None:
            return

        self.data = reliq_str(html)
        rq = _reliq_struct()
        err = libreliq.reliq_init(self.data.data,self.data.size,byref(rq))
        if err:
            raise self._create_error(err)
        self.struct = reliq_struct(rq)

        if isinstance(ref,str|bytes):
            r = self._get_base()
            self._set_url(r,strconv(ref,True))

    expr = reliqExpr
    Type = reliqType

    class Error(Exception):
        pass

    class ScriptError(Error):
        pass

    class HtmlError(Error):
        pass

    class SystemError(Error):
        pass

    def _elnodes(self) -> Tuple[Optional[c_void_p],int,int,Optional[c_void_p]]:
        rtype = self.type
        if rtype in self.Type.empty|self.Type.unknown:
            return (None,0,0,None)

        if rtype in self.Type.list:
            ret = []
            for hnode, parent in self.compressed.iter():
                hn = chnode_conv(self.struct.struct,hnode)
                nodesl = hn.desc+1
                if parent is None:
                    parent = hnode

                ret.append((hnode,nodesl,hn.lvl,parent))
            return ret

        if rtype in self.Type.single:
            nodes = self.single.chnode
            hn = self.single.hnode
            nodesl = hn.desc+1
            return [(nodes,nodesl,hn.lvl,self.single.cparent)]

        nodesl = self.struct.struct.nodesl
        nodes = self.struct.struct.nodes
        return [(nodes,nodesl,0,None)]

    @property
    def _isempty(self) -> bool:
        if self.struct is None:
            return True
        if self.data is None:
            return True
        return False

    def _getitem_r(self, type: reliqType) -> Generator['reliq',None,None]:
        if type in self.Type.single:
            return self.children(gen=True)
        return self.self(gen=True)

    def _noaxis(self) -> Optional[reliqType]:
        rtype = self.type

        if rtype in self.Type.empty|self.Type.unknown:
            return None # should be treated as True

        return rtype

    def __getitem__(self,item) -> 'reliq':
        rtype = self._noaxis()

        if rtype is not None:
            if rtype in self.Type.struct:
                nodes, nodesl, lvl, parent = self._elnodes()[0]
                if item >= nodesl:
                    raise IndexError("list index out of range")
            elif rtype in self.Type.list:
                if item >= self.compressed.size.value:
                    raise IndexError("list index out of range")

            index = 0
            for i in self._getitem_r(rtype):
                if index == item:
                    return i
                index += 1

        raise IndexError("list index out of range")

    def __len__(self):
        if self._noaxis() is None:
            return 0

        count = 0
        for i in self._getitem_r(self.type):
            count += 1
        return count

    def _axis(self, gen: bool, func: Callable, type: Optional[reliqType], rel=False) -> list['reliq']|Generator['reliq',None,None]:
        def y():
            if self._noaxis() is None:
                return

            for nodes, nodesl, lvl, parent in self._elnodes():
                if rel:
                    parent = nodes

                for i in func(self,nodes,nodesl,lvl,parent):
                    if type is not None and not (i.type&type):
                        continue
                    yield i

        r = y()
        if not gen:
            r = list(r)
        return r

    def self(self, gen=False, type="", rel=False) -> list['reliq']|Generator['reliq',None,None]:
        def from_nodes(self, nodes, nodesl, lvl, parent):
            i = 0
            while i < nodesl:
                n = self._init_single(self,nodes+i*chnode_sz,parent)
                i += n.single.hnode.desc+1
                yield n

        if type == "":
            type = self.Type.tag if self.compressed is None else None

        return self._axis(gen,from_nodes,type=type,rel=rel)

    def children(self, gen=False, type=reliqType.tag, rel=False) -> list['reliq']|Generator['reliq',None,None]:
        def from_nodes(self, nodes, nodesl, lvl, parent):
            i = 1
            lvl += 1
            while i < nodesl:
                node = nodes+i*chnode_sz
                hn = chnode_conv(self.struct.struct,node)

                if hn.lvl == lvl:
                    n = self._init_single(self,node,parent)
                    i += hn.desc+1
                    yield n
                else:
                    i += 1

        return self._axis(gen,from_nodes,type=type,rel=rel)

    def descendants(self, gen=False, type=reliqType.tag, rel=False) -> list['reliq']|Generator['reliq',None,None]:
        def from_nodes(self, nodes, nodesl, lvl, parent):
            ret = []
            i = 1
            while i < nodesl:
                node = nodes+i*chnode_sz
                hn = chnode_conv(self.struct.struct,node)

                if hn.lvl > lvl:
                    yield self._init_single(self,node,parent)
                i += 1
            return ret

        return self._axis(gen,from_nodes,type=type,rel=rel)

    def full(self, gen=False, type=reliqType.tag, rel=False) -> list['reliq']|Generator['reliq',None,None]:
        def from_nodes(self, nodes, nodesl, lvl, parent):
            i = 0
            while i < nodesl:
                node = nodes+i*chnode_sz
                hn = chnode_conv(self.struct.struct,node)

                if hn.lvl >= lvl:
                    yield self._init_single(self,node,parent)
                i += 1

        return self._axis(gen,from_nodes,type=type,rel=rel)

    def everything(self, gen=False, type=reliqType.tag, rel=False) -> list['reliq']|Generator['reliq',None,None]:
        def from_nodes(self, nodes, nodesl, lvl, parent):
            i = 0
            nodes = self.struct.struct.nodes
            nodesl = self.struct.struct.nodesl
            while i < nodesl:
                node = nodes+i*chnode_sz
                hn = chnode_conv(self.struct.struct,node)
                yield self._init_single(self,node,parent)
                i += 1

        return self._axis(gen,from_nodes,type=type,rel=rel)

    def rparent(self, gen=False, type=reliqType.tag) -> list['reliq']|Generator['reliq',None,None]:
        def from_nodes(self, nodes, nodesl, lvl, parent):
            if parent is not None:
                yield self._init_single(self,parent,nodes)

        return self._axis(gen,from_nodes,type=type)

    def _find_parent(self, nodes, lvl):
        lvl -= 1
        j = (nodes-self.struct.struct.nodes)//chnode_sz-1
        while True:
            node = self.struct.struct.nodes+j*chnode_sz
            hn = chnode_conv(self.struct.struct,node)
            if hn.lvl == lvl:
                return node, hn.lvl

            if j == 0:
                break
            j -= 1
        return None, 0

    def parent(self, gen=False, type=reliqType.tag, rel=False) -> list['reliq']|Generator['reliq',None,None]:
        def from_nodes(self, nodes, nodesl, lvl, parent):
            if self.Type.struct in self.type:
                return
            p, lvl = self._find_parent(nodes,lvl)
            if p:
                yield self._init_single(self,p,parent)

        return self._axis(gen,from_nodes,type=type,rel=rel)

    def ancestors(self, gen=False, type=reliqType.tag, rel=False) -> list['reliq']|Generator['reliq',None,None]:
        def from_nodes(self, nodes, nodesl, lvl, parent):
            if self.Type.struct in self.type:
                return
            node = nodes
            nodes = self.struct.struct.nodes

            while node != nodes:
                node, lvl = self._find_parent(node,lvl)
                if node is None:
                    break

                yield self._init_single(self,node,parent)

        return self._axis(gen,from_nodes,type=type,rel=rel)

    def before(self, gen=False, type=reliqType.tag, rel=False) -> list['reliq']|Generator['reliq',None,None]:
        def from_nodes(self, nodes, nodesl, lvl, parent):
            if self.Type.struct in self.type:
                return
            node = nodes
            nodes = self.struct.struct.nodes

            i = (node-nodes)//chnode_sz-1
            while True:
                node = nodes+i*chnode_sz
                yield self._init_single(self,node,parent)
                if i == 0:
                    break
                i -= 1

        return self._axis(gen,from_nodes,type=type,rel=rel)

    def preceding(self, gen=False, type=reliqType.tag, rel=False) -> list['reliq']|Generator['reliq',None,None]:
        def from_nodes(self, nodes, nodesl, lvl, parent):
            if self.Type.struct in self.type:
                return
            node = nodes
            nodes = self.struct.struct.nodes
            if node == nodes:
                return
            lvl = chnode_conv(self.struct.struct,node).lvl
            lvl = -1 if lvl == 0 else lvl-1

            i = (node-nodes)//chnode_sz-1
            while True:
                node = nodes+i*chnode_sz
                hn = chnode_conv(self.struct.struct,node)
                if hn.lvl == lvl:
                    if i == 0:
                        break
                    lvl -= 1
                    i -= 1
                    continue

                yield self._init_single(self,node,parent)

                if i == 0:
                    break
                i -= 1

        return self._axis(gen,from_nodes,type=type,rel=rel)

    def after(self, gen=False, type=reliqType.tag, rel=False) -> list['reliq']|Generator['reliq',None,None]:
        def from_nodes(self, nodes, nodesl, lvl, parent):
            if self.Type.struct in self.type:
                return
            node = nodes
            nodes = self.struct.struct.nodes
            nodesl = self.struct.struct.nodesl

            i = (node-nodes)//chnode_sz+1
            while i < nodesl:
                node = nodes+i*chnode_sz
                yield self._init_single(self,node,parent)
                i += 1

        return self._axis(gen,from_nodes,type=type,rel=rel)

    def subsequent(self, gen=False, type=reliqType.tag, rel=False) -> list['reliq']|Generator['reliq',None,None]:
        def from_nodes(self, nodes, nodesl, lvl, parent):
            if self.Type.struct in self.type:
                return
            node = nodes
            hn = chnode_conv(self.struct.struct,node)
            nodes = self.struct.struct.nodes
            nodesl = self.struct.struct.nodesl

            i = (node-nodes)//chnode_sz+hn.desc+1
            while i < nodesl:
                node = nodes+i*chnode_sz
                yield self._init_single(self,node,parent)
                i += 1

        return self._axis(gen,from_nodes,type=type,rel=rel)

    def siblings_preceding(self, gen=False, type=reliqType.tag, full=False, rel=False) -> list['reliq']|Generator['reliq',None,None]:
        def from_nodes(self, nodes, nodesl, lvl, parent):
            if self.Type.struct in self.type:
                return
            node = nodes
            nodes = self.struct.struct.nodes
            if nodes == node:
              return

            i = (node-nodes)//chnode_sz-1
            while True:
                node = nodes+i*chnode_sz
                hn = chnode_conv(self.struct.struct,node)

                if hn.lvl < lvl:
                    break

                if full or hn.lvl == lvl:
                    yield self._init_single(self,node,parent)

                if i == 0:
                    break
                i -= 1
        return self._axis(gen,from_nodes,type=type,rel=rel)

    def siblings_subsequent(self, gen=False, type=reliqType.tag, full=False, rel=False) -> list['reliq']|Generator['reliq',None,None]:
        def from_nodes(self, nodes, nodesl, lvl, parent):
            if self.Type.struct in self.type:
                return
            node = nodes
            hn = chnode_conv(self.struct.struct,node)
            nodes = self.struct.struct.nodes
            nodesl = self.struct.struct.nodesl

            i = (node-nodes)//chnode_sz+hn.desc+1
            while i < nodesl:
                node = nodes+i*chnode_sz
                hn = chnode_conv(self.struct.struct,node)

                if full:
                    if hn.lvl < lvl:
                        break
                elif hn.lvl != lvl:
                    break

                node = nodes+i*chnode_sz
                yield self._init_single(self,node,parent)

                if full:
                    i += 1
                else:
                    i += hn.desc+1

        return self._axis(gen,from_nodes,type=type,rel=rel)

    def siblings(self, gen=False, type=reliqType.tag, full=False, rel=False) -> list['reliq']|Generator['reliq',None,None]:
        r = chain(
            self.siblings_preceding(True,type=type,full=full,rel=rel),
            self.siblings_subsequent(True,type=type,full=full,rel=rel),
        )
        if not gen:
            r = list(r)
        return r

    def __bytes__(self):
        ret = b""

        rtype = self.type

        if rtype in self.Type.single:
            return bytes(self.single.hnode.all)

        if rtype is self.Type.list:
            for hnode, parent in self.compressed.iter():
                hn = chnode_conv(self.struct.struct,hnode)
                ret += bytes(hn)

            return ret

        if rtype is not self.Type.struct:
            return ret

        nodes = self.struct.struct.nodes
        nodesl = self.struct.struct.nodesl
        i = 0
        while i < nodesl:
            hn = chnode_conv(self.struct.struct,nodes+i*chnode_sz)
            ret += bytes(hn)
            i += hn.desc+1
        return ret

    def __str__(self):
        return bytes(self).decode()

    def _repr_short_str(self, text,mx=20):
        x = '"' + text[:mx] + '"'
        if len(text) > 20:
            x += "..."
        return x

    def __repr__(self):
        t = self.type

        if self.type is self.Type.empty:
            return "<reliq Empty>"
        if  self.Type.unknown in self.type:
            return "<reliq Unknown>"
        if self.type is self.Type.struct:
            return "<reliq Struct {} nodes / {} bytes>".format(self.struct.struct.nodesl,self.struct.struct.datal)
        if self.type is self.Type.list:
            return "<reliq List {} nodes / {} bytes>".format(self.compressed.size.value,self.struct.struct.datal)

        assert self.type in self.Type.single

        hn = self.single.hnode
        pos = self.single.position

        if self.type is self.Type.tag:
            return "<{} desc {} / pos {}>".format(str(hn.tag),hn.desc,pos)
        if self.type is self.Type.comment:
            return "<comment {} / pos {}>".format(self._repr_short_str(str(hn.all)),pos)
        if self.type is self.Type.text:
            return "<text {} / pos {}>".format(self._repr_short_str(str(hn.all).strip()),pos)
        if self.type is self.Type.texterr:
            return "<texterr {} / pos {}>".format(self._repr_short_str(str(hn.all).strip()),pos)
        if self.type is self.Type.textempty:
            return "<textempty size {} / pos {}>".format(hn.all.s,pos)

        assert 0

    def _name(self, raw: bool=False) -> Optional[str|bytes]:
        if self.type is not self.Type.tag:
            return None
        return strconv(self.single.hnode.tag,raw)

    @property
    def ref_raw(self) -> bytes:
        if self._isempty:
            return b""
        url = self.struct.struct.url
        if url.allocated == 0:
            return b""
        return bytes(url.url)

    @property
    def ref(self) -> str:
        return self.ref_raw.decode()

    @property
    def name_raw(self) -> Optional[bytes]:
        return self._name(True)

    @property
    def name(self) -> Optional[str]:
        return self._name()

    def _starttag(self, raw: bool=False) -> Optional[str|bytes]:
        if self.type is not self.Type.tag:
            return None

        x = _reliq_cstr_struct()
        l = c_size_t()
        x.b = libreliq.reliq_hnode_starttag(byref(self.single.hnode),byref(l))
        x.s = l
        return strconv(x,raw)

    @property
    def starttag_raw(self) -> Optional[bytes]:
        return self._starttag(True)

    @property
    def starttag(self) -> Optional[str]:
        return self._starttag()

    def _endtag(self, strip=False, raw: bool=False) -> Optional[str|bytes]:
        if self.type is not self.Type.tag:
            return None
        x = _reliq_cstr_struct()
        l = c_size_t()
        if strip:
            x.b = libreliq.reliq_hnode_endtag_strip(byref(self.single.hnode),byref(l))
        else:
            x.b = libreliq.reliq_hnode_endtag(byref(self.single.hnode),byref(l))
        if x.b is None:
            return None
        x.s = l
        return strconv(x,raw)

    @property
    def endtag_raw(self) -> Optional[bytes]:
        return self._endtag(raw=True)

    @property
    def endtag_strip(self) -> Optional[bytes]:
        return self._endtag(strip=True)

    @property
    def endtag_strip_raw(self) -> Optional[bytes]:
        return self._endtag(strip=True,raw=True)

    @property
    def endtag(self) -> Optional[str]:
        return self._endtag()

    def _insides(self, raw: bool=False) -> Optional[str|bytes]:
        if self.type not in self.Type.tag|self.Type.comment:
            return None
        return strconv(self.single.hnode.insides,raw)

    @property
    def insides(self) -> Optional[str]:
        return self._insides()

    @property
    def insides_raw(self) -> Optional[bytes]:
        return self._insides(True)

    @property
    def desc_count(self) -> int: #count of descendants
        if self.type is not self.Type.tag:
            return 0
        return self.single.hnode.desc

    @property
    def tag_count(self) -> int: #count of tags inside
        if self.type is not self.Type.tag:
            return 0
        return self.single.hnode.tag_count

    @property
    def text_count(self) -> int: #count of text nodes inside
        if self.type is not self.Type.tag:
            return 0
        return self.single.hnode.text_count

    @property
    def comment_count(self) -> int: #count of comments inside
        if self.type is not self.Type.tag:
            return 0
        return self.single.hnode.comment_count

    @property
    def lvl(self) -> int:
        if self.type not in self.Type.single:
            return 0
        return self.single.hnode.lvl

    @property
    def rlvl(self) -> int:
        if self.type not in self.Type.single:
            return 0
        parent = self.single.parent
        if parent is None:
            return self.single.hnode.lvl
        return self.single.hnode.lvl-parent.lvl

    @property
    def position(self) -> int:
        if self.type not in self.Type.single:
            return 0
        return self.single.position

    @property
    def rposition(self) -> int:
        if self.type not in self.Type.single:
            return 0
        return self.single.rposition

    @property
    def attribl(self) -> int:
        if self.type is not self.Type.tag:
            return 0
        return self.single.hnode.attribsl

    def _attrib(self, raw: bool=False) -> dict:
        if self.type is not self.Type.tag:
            return {}

        ret = {}
        length = self.single.hnode.attribsl
        i = 0
        attr = self.single.hnode.attribs

        conv = lambda x: strconv(x,raw)
        value_separator = conv(" ")

        while i < length:
            a = _reliq_attrib_struct()
            libreliq.reliq_cattrib_conv(byref(self.struct.struct),attr+i*cattrib_sz,byref(a))

            key = conv(a.key).lower()
            t = conv('')
            prev = ret.get(key)
            if prev is not None:
                t += ret.get(key)
            if len(t) > 0:
                t += value_separator
            t += conv(a.value)
            ret[key] = t
            i += 1
        return ret

    @property
    def attrib(self) -> dict:
        return self._attrib()

    @property
    def attrib_raw(self) -> dict:
        return self._attrib(True)

    @property
    def type(self) -> Type:
        if self._isempty:
            return self.Type.empty
        if self.compressed is not None:
            return self.Type.list
        if self.single is None:
            return self.Type.struct

        return self.single.hnode.ntype

    def _text(self,recursive: bool=False, raw: bool=False) -> str|bytes:
        conv = lambda x: strconv(x,raw)
        ret = conv('')
        if self.struct is None:
            return ret

        for nodes, nodesl, lvl, parent in self._elnodes():
            i = 0
            lvl = -1
            while i < nodesl:
                hn = chnode_conv(self.struct.struct,nodes+i*chnode_sz)
                if lvl == -1:
                    lvl = hn.lvl

                if hn.ntype in self.Type.textall:
                    ret += conv(hn)

                if not recursive and hn.lvl == lvl+1:
                    i += hn.desc+1
                else:
                    i += 1

        return ret

    @property
    def text(self):
        return self._text()

    @property
    def text_raw(self):
        return self._text(raw=True)

    @property
    def text_recursive(self):
        return self._text(recursive=True)

    @property
    def text_recursive_raw(self):
        return self._text(recursive=True,raw=True)

    @staticmethod
    def decode(string: str|bytes, raw: bool=False, no_nbsp=True) -> str|bytes:
        if isinstance(string,str):
            string = string.encode("utf-8")
        src = c_void_p()
        srcl = c_size_t()

        libreliq.reliq_decode_entities_str(cast(string,c_void_p),len(string),byref(src),byref(srcl), c_bool(no_nbsp))
        ret = string_at(src,srcl.value)
        libreliq.reliq_std_free(src,0)

        return strconv(ret,raw)

    @staticmethod
    def encode(string: str|bytes, raw: bool=False, full=False) -> str|bytes:
        if isinstance(string,str):
            string = string.encode("utf-8")
        src = c_void_p()
        srcl = c_size_t()

        libreliq.reliq_encode_entities_str(cast(string,c_void_p),len(string),byref(src),byref(srcl), c_bool(full))
        ret = string_at(src,srcl.value)
        libreliq.reliq_std_free(src,0)

        return strconv(ret,raw)

    def get_data(self, raw: bool=False) -> bytes:
        return strconv(self.data,raw)

    @staticmethod
    def _create_error(err: POINTER(_reliq_error_struct)):
        p_err = err.contents
        msg = p_err.msg.decode()
        code = p_err.code
        errmsg = 'failed {}: {}'.format(code,msg)

        if code == 5:
            ret = reliq.SystemError(errmsg)
        elif code == 10:
            ret = reliq.HtmlError(errmsg)
        elif code == 15:
            ret = reliq.ScriptError(errmsg)
        else:
            ret = reliq.Error(errmsg)

        libreliq.reliq_std_free(err,0)
        return ret

    def _convscript(self,script):
        if isinstance(script,reliqExpr):
            return script
        return self.expr(script)

    def search(self, script: typing.Union[str,bytes,Path,reliqExpr], raw: bool=False) -> str|bytes:
        conv = lambda x: strconv(x,raw)
        ret = conv('')

        rtype = self.type
        if rtype in self.Type.empty|self.Type.unknown:
            return ret

        expr = self._convscript(script)

        src = c_void_p()
        srcl = c_size_t()

        struct = self.struct.struct
        if rtype in self.Type.single:
            struct = _reliq_struct()
            memmove(byref(struct),byref(self.struct.struct),sizeof(_reliq_struct))
            struct.nodesl = self.single.hnode.desc+1
            struct.nodes = self.single.chnode

        input = None
        inputl = 0
        compr_buffer = None

        if rtype in self.Type.single:
            hnode = (self.single.chnode-struct.nodes)//chnode_sz
            parent = self.single.cparent
            if parent is None:
                parent = UINT32_MAX
            else:
                parent = (parent-struct.nodes)//chnode_sz
            compr_buffer = _reliq_compressed_struct(hnode,parent)
            input = byref(compr_buffer)
            inputl = 1
        elif rtype is self.Type.list:
            input = self.compressed.compressed
            inputl = self.compressed.size

        err = libreliq.reliq_exec_str(byref(struct),input,inputl,expr.expr,byref(src),byref(srcl))

        if src:
            if not err:
                ret = conv(string_at(src,srcl.value))
            libreliq.reliq_std_free(src,0)

        if err:
            raise self._create_error(err)
        return ret

    def _get_base(self) -> bytes:
        return self.search(r'[0] base href | "%(href)v"',raw=True)

    def _set_url(self,url: bytes, ref: bytes):
        if self.type is not self.Type.struct:
            return

        ref_struct = _reliq_url_struct()
        libreliq.reliq_url_parse(ref,len(ref),None,0,False,byref(ref_struct))

        url_struct = byref(self.struct.struct.url)
        libreliq.reliq_url_parse(url,len(url),cast(ref_struct.scheme.b,c_char_p),ref_struct.scheme.s,True,url_struct)

        libreliq.reliq_url_join(byref(ref_struct),url_struct,url_struct)

        libreliq.reliq_url_free(byref(ref_struct))

    @staticmethod
    def urljoin(ref: bytes|str, url: bytes|str, raw=False) -> str|bytes:
        url = tobytes(url)
        ref = tobytes(ref)

        ref_struct = _reliq_url_struct()
        libreliq.reliq_url_parse(ref,len(ref),None,0,False,byref(ref_struct))

        url_struct = _reliq_url_struct()
        libreliq.reliq_url_parse(url,len(url),cast(ref_struct.scheme.b,c_char_p),ref_struct.scheme.s,False,byref(url_struct))

        libreliq.reliq_url_join(byref(ref_struct),byref(url_struct),byref(url_struct))

        ret = bytes(url_struct.url)

        libreliq.reliq_url_free(byref(ref_struct))
        libreliq.reliq_url_free(byref(url_struct))

        return strconv(ret,raw)

    def ujoin(self, url: bytes|str, raw=False) -> str|bytes:
        if self._isempty:
            return strconv("",raw)
        ref_struct = self.struct.struct.url
        if ref_struct.allocated == 0:
            return strconv("",raw)

        url = tobytes(url)
        url_struct = _reliq_url_struct()

        libreliq.reliq_url_parse(url,len(url),cast(ref_struct.scheme.b,c_char_p),ref_struct.scheme.s,False,byref(url_struct))
        libreliq.reliq_url_join(byref(ref_struct),byref(url_struct),byref(url_struct))

        ret = bytes(url_struct.url)

        libreliq.reliq_url_free(byref(url_struct))

        return strconv(ret,raw)


    def json(self, script: typing.Union[str,bytes,Path,reliqExpr]) -> dict:
        expr = self._convscript(script)
        expr.correct_scheme()
        return json.loads(self.search(expr,raw=True))

    def filter(self,script: typing.Union[str,bytes,Path,reliqExpr],independent: bool=False) -> "reliq":
        rtype = self.type
        if rtype in self.Type.empty|self.Type.unknown:
            return self

        expr = self._convscript(script)

        compressed = c_void_p()
        compressedl = c_size_t()

        struct = self.struct.struct

        input = None
        inputl = 0
        compr_buffer = None

        if rtype in self.Type.single:
            hnode = (self.single.chnode-struct.nodes)//chnode_sz
            parent = self.single.cparent
            if parent is None:
                parent = UINT32_MAX
            else:
                parent = (parent-struct.nodes)//chnode_sz
            compr_buffer = _reliq_compressed_struct(hnode,parent)
            input = byref(compr_buffer)
            inputl = 1
        elif rtype is self.Type.list:
            input = self.compressed.compressed
            inputl = self.compressed.size

        err = libreliq.reliq_exec(byref(struct),input,inputl,expr.expr,byref(compressed),byref(compressedl))

        if compressed:
            if not err:
                if independent:
                    nstruct = reliq_struct(libreliq.reliq_from_compressed_independent(compressed,compressedl,byref(struct)))
                    data = reliq_str(nstruct.struct.data,nstruct.struct.datal)
                    ret = self._init_independent(data,nstruct,self.ref)

                    libreliq.reliq_std_free(compressed,0)
                else:
                    ret = self._new(self)
                    ret.compressed = reliq_compressed_list(struct.nodes,compressed,compressedl)
        else:
            ret = self._new(None)
            libreliq.reliq_std_free(compressed,0)

        if err:
            raise self._create_error(err)
        return ret
