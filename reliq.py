#!/usr/bin/env python3
# by Dominik Stanisław Suchora <suchora.dominik7@gmail.com>
# License: GNU GPLv3

from ctypes import *
import ctypes.util

libreliq = CDLL("libreliq.so") #find_library finds nothing
cstdlib = CDLL(ctypes.util.find_library("c"))

class _reliq_cstr_struct(Structure):
    _fields_ = [('b',c_void_p),('s',c_size_t)]

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

class reliq():
    def __init__(self,html,_parse=True):
        if html is not None:
            self.data = html.encode("utf-8")
        self.data_v = c_void_p();
        self.data_s = c_size_t();
        self.selfallocated = False
        if _parse:
            self.struct = libreliq.reliq_init(cast(self.data,c_void_p),len(self.data),None)

    def __len__(self):
        return self.struct.nodesl

    def __getitem__(self,item):
        return self.struct.nodes[item]

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
        if self.selfallocated:
            return string_at(self.data_v,self.data_s.value).decode()
        return self.data.decode()

    def _create_error(err):
        p_err = err.contents
        ret = ValueError('failed {}: {}'.format(p_err.code,p_err.msg.decode()))
        cstdlib.free(err);
        return ret

    def _comp(script):
        s = script.encode("utf-8");

        exprs = _reliq_exprs_struct();
        err = libreliq.reliq_ecomp(cast(s,c_void_p),len(s),byref(exprs))
        if err:
            libreliq.reliq_efree(byref(exprs))
            raise reliq._create_error(err)
            return None
        return exprs

    def search(self,script):
        exprs = reliq._comp(script)

        src = c_void_p()
        srcl = c_size_t()

        err = libreliq.reliq_exec_str(byref(self.struct),byref(src),byref(srcl),byref(exprs));

        ret = None;

        if src:
            if not err:
                ret = string_at(src,srcl.value).decode()
            cstdlib.free(src)

        libreliq.reliq_efree(byref(exprs))
        if err:
            raise reliq._create_error(err)
        return ret

    def fsearch(script,html):
        exprs = reliq._comp(script)

        src = c_void_p()
        srcl = c_size_t()

        h = html.encode("utf-8");
        err = libreliq.reliq_fexec_str(cast(h,c_void_p),len(h),byref(src),byref(srcl),byref(exprs),None);

        ret = None;

        if src:
            if not err:
                ret = string_at(src,srcl.value).decode()
            cstdlib.free(src)

        libreliq.reliq_efree(byref(exprs))
        if err:
            raise reliq._create_error(err)
        return ret

    def filter(self,script,independent=False):
        exprs = reliq._comp(script)

        compressed = c_void_p()
        compressedl = c_size_t()

        err = libreliq.reliq_exec(byref(self.struct),byref(compressed),byref(compressedl),byref(exprs));

        ret = None;

        if compressed:
            if not err:
                ret = reliq(None,False);
                if independent:
                    ptr = c_void_p();
                    size = c_size_t();
                    ret.struct = libreliq.reliq_from_compressed_independent(compressed,compressedl,byref(ptr),byref(size))
                    ret.data_v = ptr
                    ret.data_s = size
                    ret.selfallocated = True
                else:
                    ret.struct = libreliq.reliq_from_compressed(compressed,compressedl,byref(self.struct))
                    ret.data = self.data

            cstdlib.free(compressed)

        libreliq.reliq_efree(byref(exprs))
        if err:
            raise reliq._create_error(err)
        return ret

    def __del__(self):
        libreliq.reliq_free(byref(self.struct))
        if self.selfallocated:
            cstdlib.free(self.data_v)
