# -*- coding: utf-8 -*-
# @Author: Theo Lemaire
# @Email: theo.lemaire@epfl.ch
# @Date:   2019-06-04 18:24:29
# @Last Modified by:   Theo Lemaire
# @Last Modified time: 2020-09-28 13:39:41

import abc
import csv
from itertools import product
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import copy

from ..core import NeuronalBilayerSonophore, PulsedProtocol, AcousticDrive, LogBatch, Batch
from ..utils import logger, si_format, isIterable
from .pltutils import cm2inch, setNormalizer
from .timeseries import GroupedTimeSeries
from ..postpro import detectSpikes


class XYMap(LogBatch):
    ''' Generic 2D map object interface. '''

    offset_options = {
        'lr': (1, -1),
        'ur': (1, 1),
        'll': (-1, -1),
        'ul': (-1, 1)
    }

    def __init__(self, root, xvec, yvec):
        self.root = root
        self.xvec = xvec
        self.yvec = yvec
        super().__init__([list(pair) for pair in product(self.xvec, self.yvec)], root=root)

    def checkVector(self, name, value):
        if not isIterable(value):
            raise ValueError(f'{name} vector must be an iterable')
        if not isinstance(value, np.ndarray):
            value = np.asarray(value)
        if len(value.shape) > 1:
            raise ValueError(f'{name} vector must be one-dimensional')
        return value

    @property
    def in_key(self):
        return self.xkey

    @property
    def unit(self):
        return self.xunit

    @property
    def xvec(self):
        return self._xvec

    @xvec.setter
    def xvec(self, value):
        self._xvec = self.checkVector('x', value)

    @property
    def yvec(self):
        return self._yvec

    @yvec.setter
    def yvec(self, value):
        self._yvec = self.checkVector('x', value)

    @property
    @abc.abstractmethod
    def xkey(self):
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def xfactor(self):
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def xunit(self):
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def ykey(self):
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def yfactor(self):
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def yunit(self):
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def zkey(self):
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def zunit(self):
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def zfactor(self):
        raise NotImplementedError

    @property
    def out_keys(self):
        return [f'{self.zkey} ({self.zunit})']

    @property
    def in_labels(self):
        return [f'{self.xkey} ({self.xunit})', f'{self.ykey} ({self.yunit})']

    def getLogData(self):
        ''' Retrieve the batch log file data (inputs and outputs) as a dataframe. '''
        return pd.read_csv(self.fpath, sep=self.delimiter).sort_values(self.in_labels)

    def getInput(self):
        ''' Retrieve the logged batch inputs as an array. '''
        return self.getLogData()[self.in_labels].values

    def getOutput(self):
        return np.reshape(super().getOutput(), (self.xvec.size, self.yvec.size)).T

    def writeLabels(self):
        with open(self.fpath, 'w') as csvfile:
            writer = csv.writer(csvfile, delimiter=self.delimiter)
            writer.writerow([*self.in_labels, *self.out_keys])

    def isEntry(self, comb):
        ''' Check if a given input is logged in the batch log file. '''
        inputs = self.getInput()
        if len(inputs) == 0:
            return False
        imatches_x = np.where(np.isclose(inputs[:, 0], comb[0], rtol=self.rtol, atol=self.atol))[0]
        imatches_y = np.where(np.isclose(inputs[:, 1], comb[1], rtol=self.rtol, atol=self.atol))[0]
        imatches = list(set(imatches_x).intersection(imatches_y))
        if len(imatches) == 0:
            return False
        return True

    @property
    def inputscode(self):
        ''' String describing the batch inputs. '''
        xcode = self.rangecode(self.xvec, self.xkey, self.xunit)
        ycode = self.rangecode(self.yvec, self.ykey, self.yunit)
        return '_'.join([xcode, ycode])

    @staticmethod
    def getScaleType(x):
        xmin, xmax, nx = x.min(), x.max(), x.size
        if np.all(np.isclose(x, np.logspace(np.log10(xmin), np.log10(xmax), nx))):
            return 'log'
        else:
            return 'lin'
        # elif np.all(np.isclose(x, np.linspace(xmin, xmax, nx))):
        #     return 'lin'
        # else:
        #     raise ValueError('Unknown distribution type')

    @property
    def xscale(self):
        return self.getScaleType(self.xvec)

    @property
    def yscale(self):
        return self.getScaleType(self.yvec)

    @staticmethod
    def computeMeshEdges(x, scale):
        ''' Compute the appropriate edges of a mesh that quads a linear or logarihtmic distribution.

            :param x: the input vector
            :param scale: the type of distribution ('lin' for linear, 'log' for logarihtmic)
            :return: the edges vector
        '''
        if scale == 'log':
            x = np.log10(x)
            range_func = np.logspace
        else:
            range_func = np.linspace
        dx = x[1] - x[0]
        n = x.size + 1
        return range_func(x[0] - dx / 2, x[-1] + dx / 2, n)

    @abc.abstractmethod
    def compute(self, x):
        ''' Compute the necessary output(s) for a given inputs combination. '''
        raise NotImplementedError

    def run(self, **kwargs):
        super().run(**kwargs)
        self.getLogData().to_csv(self.filepath(), sep=self.delimiter, index=False)

    def getOnClickXY(self, event):
        ''' Get x and y values from from x and y click event coordinates. '''
        x = self.xvec[np.searchsorted(self.xedges, event.xdata) - 1]
        y = self.yvec[np.searchsorted(self.yedges, event.ydata) - 1]
        return x, y

    def onClick(self, event):
        ''' Exexecute specific action when the user clicks on a cell in the 2D map. '''
        pass

    @property
    @abc.abstractmethod
    def title(self):
        raise NotImplementedError

    def getZBounds(self):
        matrix = self.getOutput()
        zmin, zmax = np.nanmin(matrix), np.nanmax(matrix)
        logger.info(
            f'{self.zkey} range: {zmin:.0f} - {zmax:.0f} {self.zunit}')
        return zmin, zmax

    def checkZbounds(self, zbounds):
        zmin, zmax = self.getZBounds()
        if zmin < zbounds[0]:
            logger.warning(
                f'Minimal {self.zkey} ({zmin:.0f} {self.zunit}) is below defined lower bound ({zbounds[0]:.0f} {self.zunit})')
        if zmax > zbounds[1]:
            logger.warning(
                f'Maximal {self.zkey} ({zmax:.0f} {self.zunit}) is above defined upper bound ({zbounds[1]:.0f} {self.zunit})')

    def addInsets(self, ax, insets, fs, minimal=False):
        xyoffset = np.array([0, 0.1])
        axis_to_data = ax.transAxes + ax.transData.inverted()
        data_to_axis = axis_to_data.inverted()
        for k, xydata in insets.items():
            ax.scatter(*xydata, s=20, facecolor='k', edgecolor='none')
            if not minimal:
                xyaxis = np.array(data_to_axis.transform(xydata))
                ax.annotate(
                    k, xy=xyaxis, xytext=xyaxis + xyoffset, xycoords=ax.transAxes,
                    fontsize=fs, arrowprops={'facecolor': 'black', 'arrowstyle': '-'},
                    ha='right')

    def render(self, xscale='lin', yscale='lin', zscale='lin', zbounds=None, fs=8, cmap='viridis',
               interactive=False, figsize=None, insets=None, inset_offset=0.05,
               extend_under=False, extend_over=False, ax=None, cbarax=None, title=None,
               minimal=False, levels=None):

        # Compute Z normalizer
        mymap = copy.copy(plt.get_cmap(cmap))
        if not extend_under:
            mymap.set_under('silver')
        if not extend_over:
            mymap.set_over('silver')
        if zbounds is None:
            zbounds = self.getZBounds()
        else:
            self.checkZbounds(zbounds)
        norm, sm = setNormalizer(mymap, zbounds, zscale)
        nan_eq = zbounds[0] - 1 if zscale == 'lin' else 0.5 * zbounds[0]

        # Compute mesh edges
        self.xedges = self.computeMeshEdges(self.xvec, xscale)
        self.yedges = self.computeMeshEdges(self.yvec, yscale)

        # Create figure if required
        if ax is None:
            if figsize is None:
                figsize = cm2inch(12, 7)
            fig, ax = plt.subplots(figsize=figsize)
            fig.subplots_adjust(left=0.15, bottom=0.15, right=0.8, top=0.92)
        else:
            fig = ax.get_figure()

        # Set axis properties
        if title is None:
            title = self.title
        ax.set_title(title, fontsize=fs)
        if minimal:
            ax.set_xticks([])
            ax.set_yticks([])
            ax.tick_params(axis='both', which='both', bottom=False, left=False,
                           labelbottom=False, labelleft=False)
        else:
            ax.set_xlabel(f'{self.xkey} ({self.xunit})', fontsize=fs, labelpad=-0.5)
            ax.set_ylabel(f'{self.ykey} ({self.yunit})', fontsize=fs)
        for item in ax.get_xticklabels() + ax.get_yticklabels():
            item.set_fontsize(fs)
        if xscale == 'log':
            ax.set_xscale('log')
        if yscale == 'log':
            ax.set_yscale('log')

        # Retrieve data and replace NaNs with specific out-of-bounds value
        data = self.getOutput()
        data[np.isnan(data)] = nan_eq

        # Plot map with specific color code
        ax.pcolormesh(self.xedges, self.yedges, data, cmap=mymap, norm=norm)

        # Add contour levels if needed
        if levels is not None:
            CS = ax.contour(
                self.xvec, self.yvec, data, levels, colors='k')
            ax.clabel(CS, fontsize=fs, fmt=lambda x: f'{x:g}', inline_spacing=2)

        # Add potential insets
        if insets is not None:
            self.addInsets(ax, insets, fs, minimal=minimal)

        # Plot z-scale colorbar
        if cbarax is None:
            pos1 = ax.get_position()  # get the map axis position
            cbarax = fig.add_axes([pos1.x1 + 0.02, pos1.y0, 0.03, pos1.height])
        if not extend_under and not extend_over:
            extend = 'neither'
        elif extend_under and extend_over:
            extend = 'both'
        else:
            extend = 'max' if extend_over else 'min'
        self.cbar = plt.colorbar(sm, cax=cbarax, extend=extend)
        cbarax.set_ylabel(f'{self.zkey} ({self.zunit})', fontsize=fs)
        for item in cbarax.get_yticklabels():
            item.set_fontsize(fs)

        if interactive:
            fig.canvas.mpl_connect('button_press_event', lambda event: self.onClick(event))

        return fig


class ActivationMap(XYMap):

    xkey = 'Duty cycle'
    xfactor = 1e2
    xunit = '%'
    ykey = 'Amplitude'
    yfactor = 1e-3
    yunit = 'kPa'
    onclick_colors = None

    def __init__(self, root, pneuron, a, fs, f, tstim, PRF, amps, DCs):
        self.nbls = NeuronalBilayerSonophore(a, pneuron)
        self.drive = AcousticDrive(f, None)
        self.pp = PulsedProtocol(tstim, 0., PRF, .5)
        self.fs = fs
        super().__init__(root, DCs * self.xfactor, amps * self.yfactor)

    @property
    def sim_args(self):
        return [self.drive, self.pp, self.fs, 'sonic', None]

    @property
    def title(self):
        s = 'Activation map - {} neuron @ {}Hz, {}Hz PRF ({}m sonophore'.format(
            self.nbls.pneuron.name, *si_format([self.drive.f, self.pp.PRF, self.nbls.a]))
        if self.fs < 1:
            s = f'{s}, {self.fs * 1e2:.0f}% coverage'
        return f'{s})'

    def corecode(self):
        corecodes = self.nbls.filecodes(*self.sim_args)
        del corecodes['nature']
        if 'DC' in corecodes:
            del corecodes['DC']
        return '_'.join(filter(lambda x: x is not None, corecodes.values()))

    def compute(self, x):
        ''' Compute firing rate from simulation output '''
        # Adapt drive and pulsed protocol
        self.pp.DC = x[0] / self.xfactor
        self.drive.A = x[1] / self.yfactor

        # Get model output, running simulation if needed
        data, _ = self.nbls.getOutput(*self.sim_args, outputdir=self.root)
        return self.xfunc(data)

    @abc.abstractmethod
    def xfunc(self, data):
        raise NotImplementedError

    def addThresholdCurve(self, ax, fs, mpi=False):
        queue = [[
            self.drive,
            PulsedProtocol(self.pp.tstim, self.pp.toffset, self.pp.PRF, DC / self.xfactor),
            self.fs, 'sonic', None] for DC in self.xvec]
        batch = Batch(self.nbls.titrate, queue)
        Athrs = np.array(batch.run(mpi=mpi, loglevel=logger.level))
        ax.plot(self.xvec, Athrs * self.yfactor, '-', color='#F26522', linewidth=3,
                label='threshold amplitudes')
        ax.legend(loc='lower center', frameon=False, fontsize=fs)

    @property
    @abc.abstractmethod
    def onclick_pltscheme(self):
        raise NotImplementedError

    def onClick(self, event):
        ''' Execute action when the user clicks on a cell in the 2D map. '''
        DC, A = self.getOnClickXY(event)
        self.plotTimeseries(DC, A)
        plt.show()

    def plotTimeseries(self, DC, A, **kwargs):
        ''' Plot related timeseries for a given duty cycle and amplitude. '''
        self.drive.A = A / self.yfactor
        self.pp.DC = DC / self.xfactor

        # Get model output, running simulation if needed
        data, meta = self.nbls.getOutput(*self.sim_args, outputdir=self.root)

        # Plot timeseries of appropriate variables
        timeseries = GroupedTimeSeries([(data, meta)], pltscheme=self.onclick_pltscheme)
        return timeseries.render(colors=self.onclick_colors, **kwargs)[0]

    def render(self, yscale='log', thresholds=False, mpi=False, **kwargs):
        fig = super().render(yscale=yscale, **kwargs)
        if thresholds:
            self.addThresholdCurve(fig.axes[0], fs=12, mpi=mpi)
        return fig


class FiringRateMap(ActivationMap):

    zkey = 'Firing rate'
    zunit = 'Hz'
    zfactor = 1e0
    suffix = 'FRmap'
    onclick_pltscheme = {'V_m\ |\ Q_/C_{m0}': ['Vm', 'Qm/Cm0']}
    onclick_colors = ['darkgrey', 'k']

    def xfunc(self, data):
        ''' Detect spikes in data and compute firing rate. '''
        ispikes, _ = detectSpikes(data)
        if ispikes.size > 1:
            t = data['t'].values
            sr = 1 / np.diff(t[ispikes])
            return np.mean(sr)
        else:
            return np.nan

    def render(self, zscale='log', **kwargs):
        return super().render(zscale=zscale, **kwargs)


class CalciumMap(ActivationMap):

    zkey = '[Ca2+]i'
    zunit = 'uM'
    zfactor = 1e6
    suffix = 'Camap'
    onclick_pltscheme = {'Cai': ['Cai']}

    def xfunc(self, data):
        ''' Detect spikes in data and compute firing rate. '''
        Cai = data['Cai'].values * self.zfactor  # uM
        return np.mean(Cai)

    def render(self, zscale='log', **kwargs):
        return super().render(zscale=zscale, **kwargs)


map_classes = {
    'FR': FiringRateMap,
    'Cai': CalciumMap
}


def getActivationMap(key, *args, **kwargs):
    if key not in map_classes:
        raise ValueError(f'{key} is not a valid map type')
    return map_classes[key](*args, **kwargs)
