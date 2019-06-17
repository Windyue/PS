# -*- coding: utf-8 -*-
# @Author: Theo Lemaire
# @Email: theo.lemaire@epfl.ch
# @Date:   2018-10-01 20:40:28
# @Last Modified by:   Theo Lemaire
# @Last Modified time: 2019-06-17 17:51:17

import numpy as np
import matplotlib.pyplot as plt

from ..core import getModel
from ..utils import *
from ..constants import *
from .pltutils import *


class PhaseDiagram(ComparativePlot):

    phaseplotvars = {
        'Vm': {
            'label': 'V_m\ (mV)',
            'dlabel': 'dV/dt\ (V/s)',
            'factor': 1e0,
            'lim': (-80.0, 50.0),
            'dfactor': 1e-3,
            'dlim': (-300, 700),
            'thr_amp': SPIKE_MIN_VAMP,
            'thr_prom': SPIKE_MIN_VPROM
        },
        'Qm': {
            'label': 'Q_m\ (nC/cm^2)',
            'dlabel': 'I\ (A/m^2)',
            'factor': 1e5,
            'lim': (-80.0, 50.0),
            'dfactor': 1e0,
            'dlim': (-2, 5),
            'thr_amp': SPIKE_MIN_QAMP,
            'thr_prom': SPIKE_MIN_QPROM
        }
    }

    def __init__(self, filepaths, varname):
        super().__init__(filepaths, varname)
        print(self.varname)

    def createBackBone(self, pltvar, rel_tbounds, fs, pretty_axes):
                # Create figure
        fig, axes = plt.subplots(1, 2, figsize=(8, 4))
        for ax in axes:
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)

        # 1st axis: variable as function of time
        ax = axes[0]
        ax.set_xlabel('$\\rm time\ (ms)$', fontsize=fs)
        ax.set_ylabel('$\\rm {}$'.format(pltvar['label']), fontsize=fs)
        ax.set_xlim(rel_tbounds * 1e3)
        ax.set_ylim(pltvar['lim'])
        if pretty_axes:
            ax.set_xticks(rel_tbounds * 1e3)
            ax.set_yticks(pltvar['lim'])
            ax.set_xticklabels(['{:+.1f}'.format(x) for x in ax.get_xticks()])
            ax.set_yticklabels(['{:+.0f}'.format(x) for x in ax.get_yticks()])

        # 2nd axis: phase plot (derivative of variable vs variable)
        ax = axes[1]
        ax.set_xlabel('$\\rm {}$'.format(pltvar['label']), fontsize=fs)
        ax.set_ylabel('$\\rm {}$'.format(pltvar['dlabel']), fontsize=fs)
        ax.set_xlim(pltvar['lim'])
        ax.set_ylim(pltvar['dlim'])
        ax.plot([0, 0], [pltvar['dlim'][0], pltvar['dlim'][1]], '--', color='k', linewidth=1)
        ax.plot([pltvar['lim'][0], pltvar['lim'][1]], [0, 0], '--', color='k', linewidth=1)
        if pretty_axes:
            ax.set_xticks(pltvar['lim'])
            ax.set_yticks(pltvar['dlim'])
            ax.set_xticklabels(['{:+.0f}'.format(x) for x in ax.get_xticks()])
            ax.set_yticklabels(['{:+.0f}'.format(x) for x in ax.get_yticks()])

        for ax in axes:
            for item in ax.get_xticklabels() + ax.get_yticklabels():
                item.set_fontsize(fs)

        return fig, axes

    def checkInputs(self, labels):
        self.checkLabels(labels)

    def extractSpikesData(self, t, y, tbounds, rel_tbounds, tspikes):
        spikes_tvec, spikes_yvec, spikes_dydtvec = [], [], []
        for j, (tspike, tbound) in enumerate(zip(tspikes, tbounds)):
            left_bound = max(tbound[0], rel_tbounds[0] + tspike)
            right_bound = min(tbound[1], rel_tbounds[1] + tspike)
            inds = np.where((t > left_bound) & (t < right_bound))[0]
            spikes_tvec.append(t[inds] - tspike)
            spikes_yvec.append(y[inds])
            dinds = np.hstack(([inds[0] - 1], inds, [inds[-1] + 1]))
            dydt = np.diff(y[dinds]) / np.diff(t[dinds])
            spikes_dydtvec.append((dydt[:-1] + dydt[1:]) / 2)  # average of the two
        return spikes_tvec, spikes_yvec, spikes_dydtvec

    def addLegend(self, fig, axes, handles, labels, fs):
        fig.subplots_adjust(top=0.8)
        if len(self.filepaths) > 1:
            axes[0].legend(handles, labels, fontsize=fs, frameon=False,
                           loc='upper center', bbox_to_anchor=(1.0, 1.35))
        else:
            fig.suptitle(labels[0], fontsize=fs)

    def render(self, no_offset=False, no_first=False, labels=None, colors=None,
               fs=15, lw=2, trange=None, rel_tbounds=None, pretty=True):

        self.checkInputs(labels)

        if rel_tbounds is None:
            rel_tbounds = np.array((-1.5e-3, 1.5e-3))

        # Check pltvar
        if self.varname not in self.phaseplotvars:
            raise KeyError(
                'Unknown plot variable: "{}". Possible plot variables are: {}'.format(
                    self.varname, ', '.join(['"{}"'.format(p) for p in self.phaseplotvars.keys()])))
        pltvar = self.phaseplotvars[self.varname]

        fig, axes = self.createBackBone(pltvar, rel_tbounds, fs, pretty)
        handles, comp_values, full_labels = [], [], []

        # For each file
        for i, filepath in enumerate(self.filepaths):

            # Load data
            data, meta = self.getData(filepath, trange=trange)
            meta.pop('tcomp')
            full_labels.append(figtitle(meta))

            # Extract model
            model = getModel(meta)

            # Check consistency of sim types and check differing inputs
            comp_values = self.checkConsistency(meta, comp_values)

            # Extract time and y-variable
            t = data['t'].values
            y = data[self.varname].values

            # Prominence-based spike detection
            tspikes, yspikes, _, _, tbounds = self.getSpikes(
                data, key=self.varname, mph=pltvar['thr_amp'], mpp=pltvar['thr_prom'])
            nspikes = tspikes.size

            if nspikes == 0:
                logger.warning('No spikes detected')
            else:
                # Store spikes in dedicated lists
                spikes_tvec, spikes_yvec, spikes_dydtvec = self.extractSpikesData(
                    t, y, tbounds, rel_tbounds, tspikes)

                # Plot spikes temporal profiles and phase-plane diagrams
                for j in range(nspikes):
                    if colors is None:
                        color = 'C{}'.format(i if len(self.filepaths) > 1 else j % 10)
                    else:
                        color = colors[i]
                    lh = axes[0].plot(
                        spikes_tvec[j] * 1e3, spikes_yvec[j] * pltvar['factor'],
                        linewidth=lw, c=color)[0]
                    axes[1].plot(
                        spikes_yvec[j] * pltvar['factor'], spikes_dydtvec[j] * pltvar['dfactor'],
                        linewidth=lw, c=color)

                handles.append(lh)

        # Determine labels
        if self.comp_ref_key is not None:
            self.comp_info = model.inputVars().get(self.comp_ref_key, None)
        comp_values, comp_labels = self.getCompLabels(comp_values)
        labels = self.chooseLabels(labels, comp_labels, full_labels)

        fig.tight_layout()

        # Add legend
        self.addLegend(fig, axes, handles, labels, fs)

        return fig
