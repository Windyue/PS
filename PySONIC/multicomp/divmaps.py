# -*- coding: utf-8 -*-
# @Author: Theo Lemaire
# @Email: theo.lemaire@epfl.ch
# @Date:   2020-06-29 18:11:24
# @Last Modified by:   Theo Lemaire
# @Last Modified time: 2020-09-24 20:34:59

import os
import numpy as np
import matplotlib.pyplot as plt

from ..utils import logger, bounds, si_format
from ..plt import XYMap


class DivergenceMap(XYMap):
    ''' Interface to a 2D map showing divergence of the SONIC output from a
        cycle-averaged NICE output, for various combinations of parameters.
    '''
    zunit = 'mV'
    zfactor = 1e0

    def __init__(self, root, benchmark, eval_mode, *args, tstop=None, **kwargs):
        self.benchmark = benchmark.copy()
        self.eval_mode = eval_mode
        self.tstop = tstop
        super().__init__(root, *args, **kwargs)

    @property
    def zkey(self):
        return self.eval_mode

    @property
    def suffix(self):
        return self.eval_mode

    @property
    def tstop(self):
        if self._tstop is None:
            return self.benchmark.passive_tstop
        return self._tstop

    @tstop.setter
    def tstop(self, value):
        self._tstop = value

    def descPair(self, x1, x2):
        raise NotImplementedError

    def updateBenchmark(self, x):
        raise NotImplementedError

    def logDiv(self, x, div):
        ''' Log divergence for a particular inputs combination. '''
        logger.info(f'{self.descPair(*x)}: {self.eval_mode} = {div:.2e} mV')

    def compute(self, x):
        self.updateBenchmark(x)
        t, sol = self.benchmark.simAllMethods(self.tstop)
        div = self.benchmark.divergence(t, sol, eval_mode=self.eval_mode)  # mV
        self.logDiv(x, div)
        return div

    def onClick(self, event):
        ''' Execute action when the user clicks on a cell in the 2D map. '''
        x = self.getOnClickXY(event)

        # Update bechmark object to slected configuration
        self.updateBenchmark(x)

        # Get divergence output from log
        ix, iy = [np.where(vec == val)[0][0] for vec, val in zip([self.xvec, self.yvec], x)]
        div_log = self.getOutput()[iy, ix]  # mV

        # Simulate model and re-compute divergence
        t, sol = self.benchmark.simAllMethods(self.tstop)
        div = self.benchmark.divergence(t, sol, eval_mode=self.eval_mode)  # mV

        # Raise error if computed divergence does not match log reference
        if not np.isclose(div_log, div):
            err_str = 'computed {} ({:.2e} mV) does not match log reference ({:.2e} mV)'
            raise ValueError(err_str.format(self.eval_mode, div, div_log))

        # Log divergence
        self.logDiv(x, div)

        # Show related plot
        fig = self.benchmark.plot(t, sol)
        fig.axes[0].set_title(self.descPair(*x))
        plt.show()

    def render(self, zscale='log', levels=None, zbounds=(1e-1, 1e1),
               extend_under=True, extend_over=True, cmap='Spectral_r', figsize=(6, 4), fs=12,
               **kwargs):
        ''' Render and add specific contour levels. '''
        fig = super().render(
            zscale=zscale, zbounds=zbounds, extend_under=extend_under, extend_over=extend_over,
            cmap=cmap, figsize=figsize, fs=fs, **kwargs)
        if levels is not None:
            ax = fig.axes[0]
            fmt = lambda x: f'{x:g}'  # ' mV'
            CS = ax.contour(
                self.xvec, self.yvec, self.getOutput(), levels, colors='k')
            ax.clabel(CS, fontsize=fs, fmt=fmt, inline_spacing=2)
        return fig


class ModelDivergenceMap(DivergenceMap):
    ''' Divergence map of a passive model for various combinations of
        membrane time constants (taum) and axial time constant (tauax)
    '''

    xkey = 'tau_m'
    xfactor = 1e0
    xunit = 's'
    ykey = 'tau_ax'
    yfactor = 1e0
    yunit = 's'
    ga_default = 1e0  # mS/cm2

    @property
    def title(self):
        return f'Model divmap (f = {self.benchmark.fstr}, gamma = {self.benchmark.gammastr})'

    def corecode(self):
        gstr = '_'.join(self.benchmark.gammalist)
        code = f'model_divmap_f{self.benchmark.fstr}_gamma{gstr}'
        return code.replace(' ', '')

    def descPair(self, taum, tauax):
        return f'taum = {si_format(taum, 2)}s, tauax = {si_format(tauax, 2)}s'

    def updateBenchmark(self, x):
        self.benchmark.setTimeConstants(*x)

    def render(self, xscale='log', yscale='log', add_periodicity=True, insets=None, **kwargs):
        ''' Render with insets and drive periodicty indicator. '''
        fig = super().render(xscale=xscale, yscale=yscale, **kwargs)
        fig.canvas.set_window_title(self.corecode())
        ax = fig.axes[0]
        axis_to_data = ax.transAxes + ax.transData.inverted()
        data_to_axis = axis_to_data.inverted()

        # Indicate periodicity if required
        if add_periodicity:
            T_US = 1 / self.benchmark.Fdrive
            xyTUS = data_to_axis.transform((T_US, T_US))
            for i, k in enumerate(['h', 'v']):
                getattr(ax, f'ax{k[0]}line')(T_US, color='k', linestyle='-', linewidth=1)
                xy = np.empty(2)
                xy_offset = np.empty(2)
                xy[i] = xyTUS[i]
                xy[1 - i] = 0.
                xy_offset[i] = 0.
                xy_offset[1 - i] = 0.2
                ax.annotate(
                    'TUS', xy=xy, xytext=xy - xy_offset, xycoords=ax.transAxes, fontsize=10,
                    arrowprops={'facecolor': 'black', 'arrowstyle': '-'}, **{f'{k}a': 'center'})

        # Add potential insets
        if insets is not None:
            for k, (taum, tauax) in insets.items():
                xy = data_to_axis.transform((taum, tauax))
                ax.scatter(*xy, transform=ax.transAxes, facecolor='k', edgecolor='none',
                           linestyle='--', lw=1)
                ax.annotate(k, xy=xy, xytext=np.array(xy) + np.array([0, 0.1]),
                            xycoords=ax.transAxes, fontsize=10,
                            arrowprops={'facecolor': 'black', 'arrowstyle': '-'}, ha='right')

        return fig


class OldDriveDivergenceMap(DivergenceMap):
    ''' Divergence map of a specific (membrane model, axial coupling) pairfor various
        combinations of drive frequencies and drive amplitudes.
    '''

    xkey = 'f_US'
    xfactor = 1e0
    xunit = 'kHz'
    ykey = 'gamma'
    yfactor = 1e0
    yunit = '-'

    @property
    def title(self):
        return f'Drive divergence map - {self.benchmark.pneuron.name}, tauax = {self.benchmark.tauax:.2e} ms)'

    def corecode(self):
        if self.benchmark.isPassive():
            neuron_desc = f'passive_taum_{self.benchmark.taum:.2e}ms'
        else:
            neuron_desc = self.benchmark.pneuron.name
            if self.benchmark.passive:
                neuron_desc = f'passive_{neuron_desc}'
        code = f'drive_divmap_{neuron_desc}_tauax_{self.benchmark.tauax:.2e}ms'
        if self._tstop is not None:
            code = f'{code}_tstop{self.tstop:.2f}ms'
        return code

    def descPair(self, f_US, A_Cm):
        return f'f = {f_US:.2f} kHz, gamma = {A_Cm:.2f}'

    def updateBenchmark(self, x):
        f, gamma = x
        self.benchmark.setDrive(f, (gamma, 0.))

    def threshold_filename(self, method):
        fmin, fmax = bounds(self.xvec)
        return f'{self.corecode()}_f{fmin:.0f}kHz_{fmax:.0f}kHz_{self.xvec.size}_gammathrs_{method}.txt'

    def threshold_filepath(self, *args, **kwargs):
        return os.path.join(self.root, self.threshold_filename(*args, **kwargs))

    def addThresholdCurves(self, ax):
        ls = ['--', '-.']
        for j, method in enumerate(['effective', 'full']):
            fpath = self.threshold_filepath(method)
            if os.path.isfile(fpath):
                gamma_thrs = np.loadtxt(fpath)
            else:
                gamma_thrs = np.empty(self.xvec.size)
                for i, f in enumerate(self.xvec):
                    self.benchmark.f = f
                    gamma_thrs[i] = self.benchmark.titrate(self.tstop, method=method)
                np.savetxt(fpath, gamma_thrs)
            ylims = ax.get_ylim()
            ax.plot(self.xvec * self.xfactor, gamma_thrs * self.yfactor, ls[j], color='k')
            ax.set_ylim(ylims)

    def render(self, xscale='log', thresholds=False, **kwargs):
        fig = super().render(xscale=xscale, **kwargs)
        if thresholds:
            self.addThresholdCurves(fig.axes[0])
        return fig
