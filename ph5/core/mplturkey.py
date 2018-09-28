#!/usr/bin/env pnpython3


import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as font_manager
import matplotlib.dates as mdates

from ph5.core import timedoy

PROG_VERSION = "2015.050 Developmental"


class Shot (object):
    __slots__ = ('id_s', 'time')


class Bars (object):
    '''
       left  = start time as timedoy object
       right = end time as timedoy object
    '''
    __slots__ = ('left', 'right')


class BarInfo (object):
    '''
       label = station ID
       bars  = list of Bars objects sorted on left
       deploy = deploy time as timedoy object
       pickup = pickup time as timedoy object
    '''
    __slots__ = ('label', 'das', 'bars', 'deploy', 'pickup')

    def __init__(self, label):
        self.label = label
        self.bars = []


class BarData (object):
    '''
       array    = PH5 array ID
       min      = minimum of BarInfo.deploy
       max      = maximum of BarInfo.pickup
       bar_info = list of BarInfo objects sorted on label
    '''
    __slots__ = ('array', 'min', 'max', 'bar_info', 'shots')

    def __init__(self):
        self.min = timedoy.TimeDOY(year=2019,
                                   month=0o1,
                                   day=0o1,
                                   hour=0,
                                   minute=0,
                                   second=0,
                                   microsecond=0,
                                   doy=None,
                                   epoch=None,
                                   dtobject=None)
        self.max = timedoy.TimeDOY(year=1970,
                                   month=0o1,
                                   day=0o1,
                                   hour=0,
                                   minute=0,
                                   second=0,
                                   microsecond=0,
                                   doy=None,
                                   epoch=None,
                                   dtobject=None)
        self.bar_info = []
        self.shots = []


class Turkey (object):

    # Red Yellow Green diverging colormap
    # from http://colorbrewer2.org/
    RdYlGr = ['#d73027', '#f46d43', '#fdae61',
              '#fee08b', '#ffffbf', '#d9ef8b',
              '#a6d96a', '#66bd63', '#1a9850']

    RdYlGr = ['#f7fcf5', '#e5f5e0', '#c7e9c0',
              '#a1d99b', '#74c476', '#41ab5d',
              '#238b45', '#006d2c', '#00441b']

    RdYlGr = ['#e5f5e0', '#a1d99b', '#31a354',
              '#e5f5e0', '#a1d99b', '#31a354',
              '#e5f5e0', '#a1d99b', '#31a354', ]

    POS_START = 1.0
    POS_STEP = 0.25

    def __init__(self, bar_data):
        self._figure = plt.figure()
        self._axes = self._figure.add_axes([.05, .10, .90, .85])
        self._bd = bar_data

    def _positions(self, count):
        '''
        For given *count* number of positions, get array for the positions.
        '''
        end = count * Turkey.POS_STEP + Turkey.POS_START
        pos = np.arange(Turkey.POS_START, end, Turkey.POS_STEP)
        return pos

    def _format_date(self, tdoy):
        '''
        Convert to MatPlotLib date
        '''
        mpl_date = mdates.date2num(tdoy.dtobject)
        return mpl_date

    def _configure_yaxis(self):
        '''y axis'''
        sta_labels = [bi.label for bi in self._bd.bar_info]
        das_labels = [bi.das for bi in self._bd.bar_info]
        stadas = ['deploy/pickup']
        for i in range(len(das_labels)):
            stadas.append("{0}/{1}".format(sta_labels[i], das_labels[i]))

        pos = self._positions(len(stadas) + 1)
        self._axes.set_yticks(pos)
        ylabels = self._axes.set_yticklabels(stadas)
        plt.setp(ylabels, size='xx-small')

    def _configure_xaxis(self):
        ''''x axis'''
        # make x axis date axis
        self._axes.xaxis_date()

        rule = mdates.rrulewrapper(mdates.HOURLY, interval=3)
        loc = mdates.RRuleLocator(rule)
        formatter = mdates.DateFormatter("%y-%m-%d %H:%M:%S")

        self._axes.xaxis.set_major_locator(loc)
        self._axes.xaxis.set_major_formatter(formatter)
        xlabels = self._axes.get_xticklabels()
        plt.setp(xlabels, rotation=30, size='x-small')

    def _set_legend(self):
        '''
        Tweak font to be small and place *legend*
        in the upper right corner of the figure
        '''
        font = font_manager.FontProperties(size='small')
        self._axes.legend(loc='upper right', prop=font)

    def _configure_figure(self):
        self._configure_xaxis()
        self._configure_yaxis()

        self._axes.grid(True, color='gray')
        self._figure.autofmt_xdate()

    def _bars(self):
        plot_left = self._format_date(self._bd.min)
        plot_right = self._format_date(self._bd.max)
        len(self._bd.bar_info)
        bottom = (0 * Turkey.POS_STEP) + Turkey.POS_START
        width = plot_right - plot_left
        self._axes.barh(bottom, width, left=plot_left, height=0.25,
                        align='center', label='deploy/pickup', color='#e34a33')
        i = 1
        for bi in self._bd.bar_info:
            bi.label
            deploy = self._format_date(bi.deploy)
            pickup = self._format_date(bi.pickup)
            for b in bi.bars:
                bottom = (i * Turkey.POS_STEP) + Turkey.POS_START
                bar_left = self._format_date(b.left)
                bar_right = self._format_date(b.right)
                width = bar_right - bar_left
                if not covered(deploy, pickup, bar_left, bar_right):
                    continue
                self._axes.barh(bottom, width, left=bar_left, height=0.25,
                                align='center',
                                color='#2ca25f',
                                edgecolor='#99d8c9')
            i += 1

    def _shots(self):
        for sh in self._bd.shots:
            time = self._format_date(sh.time)
            minn = self._format_date(self._bd.min)
            maxx = self._format_date(self._bd.max)
            if time < minn or time > maxx:
                continue

            self._axes.annotate(sh.id_s, xy=(time, 1.5),
                                size='x-small', rotation=90)

    def show(self):
        self._bars()
        self._configure_figure()
        plt.ylabel('Station/DAS')
        plt.xlabel('Deployment')
        plt.title("Shot Coverage\nPH5 Array: {0}".format(self._bd.array))
        self._shots()
        plt.xlim((self._format_date(self._bd.min),
                  self._format_date(self._bd.max)))
        plt.show()

# mixins


def covered(deploy, pickup, start, stop):
    # Window start time is within deploy and pickup
    if start >= deploy and start <= pickup:
        return True
    # Window stop time is within deploy and pickup
    elif stop >= deploy and stop <= pickup:
        return True
    # Entire window is within deploy and pickup times
    elif start >= deploy and stop <= pickup:
        return True

    return False


if __name__ == '__main__':
    pass
