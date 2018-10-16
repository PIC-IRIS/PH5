#!/usr/bin/env python
#
# Handle shot or array inputs from an external text file
#
# Steve Azevedo, November 2017
#

from ph5.core import kefx

PROG_VERSION = '2017.310 Developmental'


class External (object):
    def __init__(self, filename=None):
        self.filename = filename
        self.kx = kef_open(filename)
        self._make_Event_t()

    def _make_Event_t(self):
        from os.path import basename
        Event_t = {}
        for p, kv in self.kx:
            name = basename(p)
            if name not in Event_t:
                Event_t[name] = {}
            if 'order' not in Event_t[name]:
                Event_t[name]['order'] = []
                Event_t[name]['byid'] = {}
            Event_t[name]['order'].append(kv['id_s'])
            Event_t[name]['byid'][kv['id_s']] = cast(kv)
            Event_t[name]['keys'] = kv.keys()

        self.Event_t = Event_t
#
# Mix-ins
#


def kef_open(filename):
    try:
        kx = kefx.Kef(filename)
        kx.open()
        kx.read()
        kx.rewind()
    except Exception as e:
        raise kefx.KefError(e.message)

    return kx


def cast(kv):
    kk = kv.keys()
    for k in kk:
        t = k[-2:]
        # Cast to integer
        if t == '_i' or t == '_l':
            kv[k] = int(kv[k])
        # Cast to float
        if t == '_d' or t == '_f':
            kv[k] = float(kv[k])
        # Else leave as string
    return kv


if __name__ == '__main__':
    ex = External('/home/azevedo/Data/SIIOS/Event_t_all.kef')
