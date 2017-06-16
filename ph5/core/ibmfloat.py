#!/usr/bin/env pnpython3

#
#   Convert 32 bit IBM floats to 32 bit IEEE floats and visa versa in pure python
#   Note:
#
#   Steve Azevedo, March 2007
#   Original C versions from David Okaya, and Jim Fowler July 1992
#

import sys, os
'''
val = sys.version_info[:2]
#   For python 2.4
if val[0] == 2 and val[1] == 4 :
    sys.path.append (os.path.join (os.environ['KITCHEN'], "apps", "pn2", "construct-2.0-2.4.zip"))
#   For python 2.5
if val[0] == 2 and val[1] > 4 :
    sys.path.append (os.path.join (os.environ['KITCHEN'], "apps", "pn2", "construct-2.00-py2.5.egg"))
'''
#   For testing with python 2.5
#sys.path.append (os.path.join (".", "construct-2.00-py2.5.egg"))
import construct

PROG_VERSION = '2015.092'

#   Masks
##IBMSIGN  = 0x80000000
##IBMEXP   = 0x7F000000
##IBMMANT  = 0x00FFFFFF

##IEEESIGN = 0x80000000
##IEEEEXP  = 0x78F00000
##IEEEMANT = 0x007FFFFF

##sign = lambda n, s : [1, -1][bool (n & s)]

def ibm () :
    IBM = construct.BitStruct ("IBM",
                               construct.BitField ("s", 1),
                               construct.BitField ("e", 7),
                               construct.BitField ("m", 24))
    return IBM

def ieee () :
    IEEE = construct.BitStruct ("IEEE",
                                construct.BitField ("s", 1),
                                construct.BitField ("e", 8),
                                construct.BitField ("m", 23))
    return IEEE

def pfloat () :
    PFLOAT = construct.Struct ("PFLOAT",
                               construct.BFloat32 ("x"))
    return PFLOAT

def puint () :
    PINT = construct.Struct ("PINT",
                             construct.UBInt32 ("x"))
    return PINT

def psint () :
    PINT = construct.Struct ("PINT",
                             construct.SBInt32 ("x"))
    return PINT

def ibm2ieee32 (ibm_float) :
    #   IBM Float to IEEE Float (32 bit)
    #   IBM bit pattern:
    #   SEEEEEEE MMMMMMMM MMMMMMMM MMMMMMMM
    #
    ibm_s = ibm ()
    b = ibm_s.parse (ibm_float)
    ieee_s = ieee ()
    #s = sign (0x00000001, n.s)
    #   This returns a python float which might not be what we want,
    #   but it shows how we use the bits.
    #valuep = s * (16 ** (n.e - 64)) * (float (n.m) / float (2 ** 24))
    #
    mapi = 0x00800000
    i = b.e
    i = i - 64
    i = i * 4
    
    m = b.m
    if m == 0 :
        return ieee_s.build (construct.Container (s=0, e=0, m=0))
    while (m & mapi) == 0 :
        m = m << 1
        i -= 1
    
    i -= 1
    c = construct.Container (s = b.s, e = i + 127, m = m)
    value = ieee_s.build (c)
    #
    return value

def ieee2ibm32 (ieee_float) :
    #   IEEE Float to IBM Float (32 bit)
    #   IEEE bit pattern:
    #   SEEEEEEE EMMMMMMM MMMMMMM MMMMMMM
    ieee_s = ieee ()
    e = ieee_s.parse (ieee_float)
    ibm_s = ibm ()
    #s = sign (0x00000001, n.s)
    #   ...
    #valuei = s * (2 ** (n.e - 127)) * (1.0 + (float (n.m) / float (2 ** 23)))
    #
    mapi = 0x00800000
    m = e.m
    m = m | mapi
    
    i = e.e
    i -= 127
    i += 1
    
    while (i % 4) != 0 :
        m = m >> 1
        i += 1
        
    i /= 4
    i += 64
    
    c = construct.Container (s = e.s, e = i, m = m)
    value = ibm_s.build (c)
    #
    return value

if __name__ == '__main__' :
    #import binascii
    pint_s = pint ()
    pfloat_s = pfloat ()
    #   -177.623764038
    print "IBM:  ", hex (0xc2b19faf)
    v = ibm2ieee32 ("\xC2\xB1\x9F\xAF")
    n = pint_s.parse (v)
    f = pfloat_s.parse (v)
    print "IEEE: ", hex (n.x), f.x
    v = ieee2ibm32 (v)
    n = pint_s.parse (v)
    print "IBM:  ", hex (n.x)
    
