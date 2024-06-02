#!/usr/bin/env python3
# by Dominik Stanisław Suchora <suchora.dominik7@gmail.com>
# License: GNU GPLv3

from ctypes import *
import ctypes.util
from typing import Union

libreliq = CDLL("libreliq.so") #find_library finds nothing
cstdlib = CDLL(ctypes.util.find_library("c"))

class _reliq_str():
    def __init__(self,string: Union[str,bytes,c_void_p],size=0,selfallocated=False):
        if isinstance(string,str):
            string = string.encode("utf-8")

        self.string = string
        self.data = string

        if isinstance(string,bytes):
            size = len(self.data)
            self.data = cast(self.data,c_void_p)
        self.size = size

    def __str__(self):
        string = self.string
        if isinstance(string,c_void_p):
            string = string_at(string,self.size).decode()
        return string.decode()

    def __del__(self):
        if isinstance(self.string,c_void_p):
            cstdlib.free(self.string)

class _reliq_cstr_struct(Structure):
    _fields_ = [('b',c_void_p),('s',c_size_t)]

    def __bytes__(self):
        return string_at(self.b,self.s)

    def __str__(self):
        return bytes(self).decode()

class _reliq_cstr_pair_struct(Structure):
    _fields_ = [('f',_reliq_cstr_struct),('s',_reliq_cstr_struct)]

class _reliq_hnode_struct(Structure):
    _fields_ = [('all',_reliq_cstr_struct),
                ('tag',_reliq_cstr_struct),
                ('insides',_reliq_cstr_struct),
                ('attribs',POINTER(_reliq_cstr_pair_struct)),
                ('child_count',c_uint),
                ('attribsl',c_ushort),
                ('lvl',c_ushort)]

    def __str__(self):
        return string_at(self.all.b,self.all.s).decode()

class _reliq_error_struct(Structure):
    _fields_ = [('msg',c_char*512),('code',c_int)]

class _reliq_exprs_struct(Structure):
    _fields_ = [('b',c_void_p),('s',c_size_t)]

class _reliq_struct(Structure):
    _fields_ = [('data',c_void_p),
                ('nodes',POINTER(_reliq_hnode_struct)),
                ('output',c_void_p),
                ('expr',c_void_p),
                ('attrib_buffer',c_void_p),
                ('nodef',c_void_p),
                ('nodefl',c_size_t),
                ('nodesl',c_size_t),
                ('size',c_size_t),
                ('flags',c_ubyte)]

cstdlib_functions = [
    (
        cstdlib.free,
        None,
        [c_void_p]
    )
]

libreliq_functions = [
    (
		libreliq.reliq_init,
		_reliq_struct,
		[c_void_p,c_size_t,c_void_p]
    ),(
		libreliq.reliq_free,
		None,
		[POINTER(_reliq_struct)]
    ),(
        libreliq.reliq_ecomp,
        POINTER(_reliq_error_struct),
        [c_void_p,c_size_t,POINTER(_reliq_exprs_struct)]
    ),(
        libreliq.reliq_efree,
        None,
        [POINTER(_reliq_exprs_struct)]
    ),(
		libreliq.reliq_exec,
		POINTER(_reliq_error_struct),
		[POINTER(_reliq_struct),POINTER(c_void_p),POINTER(c_size_t),POINTER(_reliq_exprs_struct)]
    ),(
		libreliq.reliq_exec_str,
		POINTER(_reliq_error_struct),
		[POINTER(_reliq_struct),POINTER(c_void_p),POINTER(c_size_t),POINTER(_reliq_exprs_struct)]
    ),(
        libreliq.reliq_fexec_str,
        POINTER(_reliq_error_struct),
        [c_void_p,c_size_t,POINTER(c_void_p),POINTER(c_size_t),POINTER(_reliq_exprs_struct),c_void_p]
    ),(
        libreliq.reliq_from_compressed,
        _reliq_struct,
        [c_void_p,c_size_t,POINTER(_reliq_struct)]
    ),(
        libreliq.reliq_from_compressed_independent,
        _reliq_struct,
        [c_void_p,c_size_t,POINTER(c_void_p),POINTER(c_size_t)]
    )

]

def def_functions(functions):
    for i in functions:
        i[0].restype = i[1]
        i[0].argtypes = i[2]

def_functions(cstdlib_functions)
def_functions(libreliq_functions)

class reliq_hnode():
    def __init__(self,struct: _reliq_hnode_struct,data: _reliq_str):
        self.struct = _reliq_hnode_struct();
        memmove(byref(self.struct),byref(struct),sizeof(_reliq_hnode_struct))

        attribsl = struct.attribsl
        self.attr = None
        if attribsl > 0:
            attribs_type = _reliq_cstr_pair_struct*attribsl;
            self.attr = attribs_type()
            memmove(self.attr,struct.attribs,sizeof(attribs_type))

        self.data = data

    def all(self) -> str:
        return str(self.struct.all)

    def __str__(self):
        return self.all()

    def tag(self) -> str:
        return str(self.struct.tag)

    def insides(self) -> str:
        return str(self.struct.insides)

    def child_count(self) -> int:
        return self.struct.child_count

    def lvl(self) -> int:
        return self.struct.lvl

    def attribsl(self) -> int:
        return self.struct.attribsl

    def attribs(self) -> str:
        ret = {}
        length = self.attribsl()
        i = 0
        attr = self.attr

        while i < length:
            key = str(attr[i].f)
            t = ""
            prev = ret.get(key)
            if prev is not None:
                t += ret.get(key);
            if len(t) > 0:
                t += " "
            t += str(attr[i].s)
            ret[key] = t
            i += 1
        return ret

    #!todo nodes(), text()

class reliq():
    def __init__(self,html: Union[str,bytes]):
        self.data = None
        self.struct = None
        if html is None:
            return

        self.data = _reliq_str(html,len(html))
        self.struct = libreliq.reliq_init(self.data.data,self.data.size,None)

    def __len__(self):
        return self.struct.nodesl

    def __getitem__(self,item):
        return reliq_hnode(self.struct.nodes[item],self.data)

    def __str__(self):
        i = 0
        nodes = self.struct.nodes
        nodesl = self.struct.nodesl
        ret = ""
        while i < nodesl:
            ret += str(nodes[i])
            i += nodes[i].child_count+1
        return ret

    def contents(self):
        return str(self.data)

    def _create_error(err: POINTER(_reliq_error_struct)):
        p_err = err.contents
        ret = ValueError('failed {}: {}'.format(p_err.code,p_err.msg.decode()))
        cstdlib.free(err);
        return ret

    class expr():
        def __init__(self,script: str):
            self.exprs = None
            s = script.encode("utf-8");

            exprs = _reliq_exprs_struct();
            err = libreliq.reliq_ecomp(cast(s,c_void_p),len(s),byref(exprs))
            if err:
                libreliq.reliq_efree(byref(exprs))
                raise reliq._create_error(err)
                exprs = None
            self.exprs = exprs

        def _extract(self):
            return self.exprs

        def __del__(self):
            if self.exprs is not None:
                libreliq.reliq_efree(byref(self.exprs))

    def search(self,script: Union[str,"reliq.expr"]) -> str:
        e = script
        if not isinstance(script,reliq.expr):
            e = reliq.expr(script)
        exprs = e._extract()

        src = c_void_p()
        srcl = c_size_t()

        err = libreliq.reliq_exec_str(byref(self.struct),byref(src),byref(srcl),byref(exprs));

        ret = None;

        if src:
            if not err:
                ret = string_at(src,srcl.value).decode()
            cstdlib.free(src)

        if err:
            raise reliq._create_error(err)
        return ret

    def fsearch(script: Union[str,"reliq.expr"],html: Union[str,bytes]) -> str:
        e = script
        if not isinstance(script,reliq.expr):
            e = reliq.expr(script)
        exprs = e._extract()

        src = c_void_p()
        srcl = c_size_t()

        h = html
        if isinstance(h,str):
            h = html.encode("utf-8");
        err = libreliq.reliq_fexec_str(cast(h,c_void_p),len(h),byref(src),byref(srcl),byref(exprs),None);

        ret = None;

        if src:
            if not err:
                ret = string_at(src,srcl.value).decode()
            cstdlib.free(src)

        if err:
            raise reliq._create_error(err)
        return ret

    def filter(self,script: Union[str,"reliq.expr"],independent=False) -> "reliq":
        e = script
        if not isinstance(script,reliq.expr):
            e = reliq.expr(script)
        exprs = e._extract()

        compressed = c_void_p()
        compressedl = c_size_t()

        err = libreliq.reliq_exec(byref(self.struct),byref(compressed),byref(compressedl),byref(exprs));

        ret = None;

        if compressed:
            if not err:
                ret = reliq(None);
                if independent:
                    ptr = c_void_p();
                    size = c_size_t();
                    ret.struct = libreliq.reliq_from_compressed_independent(compressed,compressedl,byref(ptr),byref(size))
                    ret.data = _reliq_str(ptr,size)
                else:
                    ret.struct = libreliq.reliq_from_compressed(compressed,compressedl,byref(self.struct))
                    ret.data = self.data

            cstdlib.free(compressed)

        if err:
            raise reliq._create_error(err)
        return ret

    def __del__(self):
        if self.struct is not None:
            libreliq.reliq_free(byref(self.struct))
