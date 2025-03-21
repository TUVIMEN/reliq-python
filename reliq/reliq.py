#!/usr/bin/env python3
# by Dominik Stanisław Suchora <suchora.dominik7@gmail.com>
# License: GNU GPLv3

import os
from ctypes import *
#import ctypes.util
import typing
from typing import Optional, Tuple
from enum import Flag, auto

class ReliqError(Exception):
    pass

libreliq_name = 'libreliq.so'
libreliq_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),libreliq_name)
if not os.path.exists(libreliq_path):
    libreliq_path = libreliq_name
libreliq = CDLL(libreliq_path)

#cstdlib = CDLL(ctypes.util.find_library("c"))

class reliq_str():
    def __init__(self,string: str | bytes | c_void_p,size=0):
        if isinstance(string,str):
            string = string.encode("utf-8")

        if isinstance(string,bytes) and size == 0:
            size = len(string)

        self.string = string
        self.data = string

        self.size = size

    def __str__(self):
        string = self.string
        if isinstance(string,c_void_p):
            string = string_at(string,self.size).decode()
        return string.decode()

    def __del__(self):
        if isinstance(self.string,c_void_p):
            libreliq.reliq_std_free(self.string,0)

class _reliq_cstr_struct(Structure):
    _fields_ = [('b',c_void_p),('s',c_size_t)]

    def __bytes__(self):
        return string_at(self.b,self.s)

    def __str__(self):
        return bytes(self).decode()

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

    def desc(self) -> int:
        return self.tag_count+self.text_count+self.comment_count

    def ntype(self) -> "reliqType":
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

    def __str__(self):
        return string_at(self.all.b,self.all.s).decode()

class _reliq_error_struct(Structure):
    _fields_ = [('msg',c_char*512),('code',c_int)]

class _reliq_struct(Structure):
    _fields_ = [('freedata',c_void_p),
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
		[POINTER(_reliq_struct),POINTER(c_void_p),POINTER(c_size_t),c_void_p]
    ),(
		libreliq.reliq_exec_str,
		POINTER(_reliq_error_struct),
		[POINTER(_reliq_struct),POINTER(c_void_p),POINTER(c_size_t),c_void_p]
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
        [c_void_p,c_size_t,POINTER(c_void_p),POINTER(c_size_t)]
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

class reliqType(Flag):
    plural = auto()
    tag = auto()
    textempty = auto()
    texterr = auto()
    text = auto()
    comment = auto()
    unknown = auto()
    textall = textempty | texterr | text

class reliq():
    def __init__(self,html: Optional[typing.Union[str,bytes,'reliq']]):
        self.data: Optional[reliq_str] = None
        self.struct: Optional[reliq_struct] = None
        self._element: Optional[c_void_p] = None
        self._element_d: Optional[_reliq_hnode_struct] = None

        if isinstance(html,reliq):
            self.data = html.data
            self.struct = html.struct
            self._element = html._element
            self._element_d = html._element_d
            return
        if html is None:
            return

        self.data = reliq_str(html)
        rq = _reliq_struct()
        err = libreliq.reliq_init(self.data.data,self.data.size,byref(rq))
        if err:
            raise reliq._create_error(err)
        self.struct = reliq_struct(rq)

    @staticmethod
    def _init_copy(data: reliq_str,struct: reliq_struct,element: c_void_p) -> 'reliq':
        ret = reliq(None)
        ret.data = data
        ret.struct = struct
        ret._element = element
        if element is None:
            ret._element_d = None
        else:
            ret._element_d = chnode_conv(struct.struct,element)
        return ret

    def _elnodes(self) -> Tuple[Optional[c_void_p],int]:
        if self.struct is None:
            return (None,0)

        nodesl = self.struct.struct.nodesl
        nodes = self.struct.struct.nodes

        if self._element is not None and self._element_d is not None:
            nodes = self._element
            nodesl = self._element_d.desc()+1

        return (nodes,nodesl)

    def __len__(self):
        if self.struct is None:
            return 0
        if self._element is not None:
            return self._element_d.desc()
        return self.struct.struct.nodesl


    def _isempty(self) -> bool:
        if self.struct is None:
            return True
        if self.data is None:
            return True
        return False

    def __getitem__(self,item) -> 'reliq':
        if self._isempty():
            raise IndexError("list index out of range")

        nodes, nodesl = self._elnodes()

        if self._element is not None:
            item += 1
        if item >= nodesl:
            raise IndexError("list index out of range")

        return reliq._init_copy(self.data,self.struct,nodes+item*chnode_sz)

    def full(self) -> list:
        if self._isempty():
            return []

        ret = []
        nodes, nodesl = self._elnodes()

        i = 0
        while i < nodesl:
            ret.append(reliq._init_copy(self.data,self.struct,nodes+i*chnode_sz))
            i += 1

        return ret

    def self(self) -> list:
        if self._isempty():
            return []

        ret = []
        nodes, nodesl = self._elnodes()

        i = 0
        while i < nodesl:
            n = reliq._init_copy(self.data,self.struct,nodes+i*chnode_sz)
            ret.append(n)
            hn = n._element_d
            i += hn.desc()+1

        return ret

    def children(self) -> list:
        if self._isempty():
            return []

        ret = []
        nodes, nodesl = self._elnodes()

        i = 1
        lvl = -1
        while i < nodesl:
            hn = chnode_conv(self.struct.struct,nodes+i*chnode_sz)
            if lvl == -1:
                lvl = hn.lvl

            if hn.lvl == lvl:
                n = reliq._init_copy(self.data,self.struct,nodes+i*chnode_sz)
                ret.append(n)
                hn = n._element_d
                i += hn.desc()+1
            else:
                i += 1

        return ret

    def descendants(self) -> list:
        if self._isempty():
            return []

        ret = []
        nodes, nodesl = self._elnodes()

        i = 1
        while i < nodesl:
            hn = chnode_conv(self.struct.struct,nodes+i*chnode_sz)
            if hn.lvl != 0:
                ret.append(reliq._init_copy(self.data,self.struct,nodes+i*chnode_sz))
            i += 1

        return ret

    def __str__(self):
        if self._isempty():
            return ""

        if self._element is not None:
            return str(self._element_d.all)

        nodes = self.struct.struct.nodes
        nodesl = self.struct.struct.nodesl
        ret = ""
        i = 0
        while i < nodesl:
            hn = chnode_conv(self.struct.struct,nodes+i*chnode_sz)
            ret += str(hn)
            i += hn.desc()+1
        return ret

    def tag(self) -> Optional[str]:
        if self.type() is not reliqType.tag:
            return None
        return str(self._element_d.tag)

    def starttag(self) -> Optional[str]:
        if self.type() is not reliqType.tag:
            return None
        x = _reliq_cstr_struct()
        l = c_size_t()
        x.b = libreliq.reliq_hnode_starttag(byref(self._element_d),byref(l))
        x.s = l
        return str(x)

    def endtag(self, strip=False) -> Optional[str]:
        if self.type() is not reliqType.tag:
            return None
        x = _reliq_cstr_struct()
        l = c_size_t()
        if strip:
            x.b = libreliq.reliq_hnode_endtag_strip(byref(self._element_d),byref(l))
        else:
            x.b = libreliq.reliq_hnode_endtag(byref(self._element_d),byref(l))
        if x.b == None:
            return None
        x.s = l
        return str(x)

    def insides(self) -> Optional[str]:
        if self.type() not in reliqType.tag|reliqType.comment:
            return None
        return str(self._element_d.insides)

    def desc(self) -> int: #count of descendants
        if self.type() is not reliqType.tag:
            return 0
        return self._element_d.desc()

    def tag_count(self) -> int: #count of tags inside
        if self.type() is not reliqType.tag:
            return 0
        return self._element_d.tag_count

    def text_count(self) -> int: #count of text nodes inside
        if self.type() is not reliqType.tag:
            return 0
        return self._element_d.text_count

    def comment_count(self) -> int: #count of comments inside
        if self.type() is not reliqType.tag:
            return 0
        return self._element_d.comment_count

    def lvl(self) -> int:
        if self.type() in reliqType.plural|reliqType.unknown:
            return 0
        return self._element_d.lvl

    def attribsl(self) -> int:
        if self.type() is not reliqType.tag:
            return 0
        return self._element_d.attribsl

    def attribs(self) -> dict:
        if self.type() is not reliqType.tag:
            return {}

        ret = {}
        length = self._element_d.attribsl
        i = 0
        attr = self._element_d.attribs

        while i < length:
            a = _reliq_attrib_struct()
            libreliq.reliq_cattrib_conv(byref(self.struct.struct),attr+i*cattrib_sz,byref(a))

            key = str(a.key)
            t = ""
            prev = ret.get(key)
            if prev is not None:
                t += ret.get(key)
            if len(t) > 0:
                t += " "
            t += str(a.value)
            ret[key] = t
            i += 1
        return ret

    def type(self) -> reliqType:
        if self._element is None:
            return reliqType.plural
        return self._element_d.ntype()

    def text(self,recursive: bool=False) -> str:
        if self.struct is None:
            return ""

        ret = ""
        nodes, nodesl = self._elnodes()
        i = 0
        lvl = -1
        while i < nodesl:
            hn = chnode_conv(self.struct.struct,nodes+i*chnode_sz)
            if lvl == -1:
                lvl = hn.lvl

            if hn.ntype() in reliqType.textall:
                ret += str(hn)

            if not recursive and hn.lvl == lvl+1:
                i += hn.desc()+1
            else:
                i += 1

        return ret

    @staticmethod
    def decode(string: str | bytes) -> str:
        if isinstance(string,str):
            string = string.encode("utf-8")
        src = c_void_p()
        srcl = c_size_t()

        libreliq.reliq_decode_entities_str(cast(string,c_void_p),len(string),byref(src),byref(srcl))
        ret = string_at(src,srcl.value).decode()
        libreliq.reliq_std_free(src,0)
        return ret


    def get_data(self) -> str:
        return str(self.data)

    @staticmethod
    def _create_error(err: POINTER(_reliq_error_struct)):
        p_err = err.contents
        ret = ReliqError('failed {}: {}'.format(p_err.code,p_err.msg.decode()))
        libreliq.reliq_std_free(err,0)
        return ret

    class expr():
        def __init__(self,script: str):
            self.exprs = None
            s = script.encode("utf-8")

            exprs = c_void_p()
            err = libreliq.reliq_ecomp(cast(s,c_void_p),len(s),byref(exprs))
            if err:
                raise reliq._create_error(err)
                exprs = None
            self.exprs = exprs

        def _extract(self):
            return self.exprs

        def __del__(self):
            if self.exprs is not None:
                libreliq.reliq_efree(self.exprs)

    def search(self,script: typing.Union[str,"reliq.expr"]) -> Optional[str]:
        if self.struct is None:
            return ""

        e = script
        if not isinstance(script,reliq.expr):
            e = reliq.expr(script)
        exprs = e._extract()

        src = c_void_p()
        srcl = c_size_t()

        struct = self.struct.struct
        if self._element is not None:
            struct = _reliq_struct()
            memmove(byref(struct),byref(self.struct.struct),sizeof(_reliq_struct))
            struct.nodesl = self._element_d.tag_count+self._element_d.text_count+self._element_d.comment_count+1
            struct.nodes = self._element

        err = libreliq.reliq_exec_str(byref(struct),byref(src),byref(srcl),exprs)

        ret = ""

        if src:
            if not err:
                ret = string_at(src,srcl.value).decode()
            libreliq.reliq_std_free(src,0)

        if err:
            raise reliq._create_error(err)
        return ret

    def filter(self,script: typing.Union[str,"reliq.expr"],independent: bool=False) -> "reliq":
        if self.struct is None:
            return self

        e = script
        if not isinstance(script,reliq.expr):
            e = reliq.expr(script)
        exprs = e._extract()

        compressed = c_void_p()
        compressedl = c_size_t()

        struct = self.struct.struct
        if self._element is not None:
            struct = _reliq_struct()
            memmove(byref(struct),byref(self.struct.struct),sizeof(_reliq_struct))
            struct.nodesl = self._element_d.tag_count+self._element_d.text_count+self._element_d.comment_count+1
            struct.nodes = self._element

        err = libreliq.reliq_exec(byref(struct),byref(compressed),byref(compressedl),exprs)

        if compressed:
            if not err:
                nstruct = None
                data = None
                if independent:
                    nstruct = reliq_struct(libreliq.reliq_from_compressed_independent(compressed,compressedl,byref(struct)))
                    data = reliq_str(nstruct.struct.data,nstruct.struct.datal)
                else:
                    nstruct = reliq_struct(libreliq.reliq_from_compressed(compressed,compressedl,byref(struct)))
                    data = self.data

                ret = reliq._init_copy(data,nstruct,None)
        else:
            ret = reliq(None)

        libreliq.reliq_std_free(compressed,0)

        if err:
            raise reliq._create_error(err)
        return ret
