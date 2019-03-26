
import inspect
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm, colors

from ..postpro import getStableFixedPoints
from ..core import NeuronalBilayerSonophore
from .pltutils import *


def plotVarDynamics(neuron, a, Fdrive, Adrive, charges, varname, varrange, fs=12):
    ''' Plot the QSS-aproximated derivative of a specific variable as function of
        the variable itself, as well as equilibrium values, for various membrane
        charge densities at a given acoustic amplitude.

        :param neuron: neuron object
        :param a: sonophore radius (m)
        :param Fdrive: US frequency (Hz)
        :param Adrive: US amplitude (Pa)
        :param charges: charge density vector (C/m2)
        :param varname: name of variable to plot
        :param varrange: range over which to compute the derivative
        :return: figure handle
    '''

    # Extract information about variable to plot
    pltvar = neuron.getPltVars()[varname]

    # Get methods to compute derivative and steady-state of variable of interest
    derX_func = getattr(neuron, 'der{}{}'.format(varname[0].upper(), varname[1:]))
    Xinf_func = getattr(neuron, '{}inf'.format(varname))
    derX_args = inspect.getargspec(derX_func)[0][1:]
    Xinf_args = inspect.getargspec(Xinf_func)[0][1:]

    # Get dictionary of charge and amplitude dependent QSS variables
    nbls = NeuronalBilayerSonophore(a, neuron, Fdrive)
    _, Qref, Vmeff, QS_states = nbls.quasiSteadyStates(Fdrive, amps=Adrive, charges=charges)
    df = {k: QS_states[i] for i, k in enumerate(neuron.states)}
    df['Vm'] = Vmeff

    # Create figure
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.set_title('{} neuron - QSS {} dynamics @ {:.2f} kPa'.format(
        neuron.name, pltvar['desc'], Adrive * 1e-3), fontsize=fs)
    ax.set_xscale('log')
    for key in ['top', 'right']:
        ax.spines[key].set_visible(False)
    ax.set_xlabel('$\\rm {}\ ({})$'.format(pltvar['label'], pltvar.get('unit', '')),
                  fontsize=fs)
    ax.set_ylabel('$\\rm QSS\ d{}/dt\ ({}/s)$'.format(pltvar['label'], pltvar.get('unit', '1')),
                  fontsize=fs)
    ax.set_ylim(-40, 40)
    ax.axhline(0, c='k', linewidth=0.5)

    y0_str = '{}0'.format(varname)
    if hasattr(neuron, y0_str):
        ax.axvline(getattr(neuron, y0_str) * pltvar.get('factor', 1),
                   label=y0_str, c='k', linewidth=0.5)

    # For each charge value
    icolor = 0
    for j, Qm in enumerate(charges):
        lbl = 'Q = {:.0f} nC/cm2'.format(Qm * 1e5)

        # Compute variable derivative as a function of its value, as well as equilibrium value,
        # keeping other variables at quasi steady-state
        derX_inputs = [varrange if arg == varname else df[arg][j] for arg in derX_args]
        Xinf_inputs = [df[arg][j] for arg in Xinf_args]
        dX_QSS = neuron.derCai(*derX_inputs)
        Xeq_QSS = neuron.Caiinf(*Xinf_inputs)

        # Plot variable derivative and its root as a function of the variable itself
        c = 'C{}'.format(icolor)
        ax.plot(varrange * pltvar.get('factor', 1), dX_QSS * pltvar.get('factor', 1), c=c, label=lbl)
        ax.axvline(Xeq_QSS * pltvar.get('factor', 1), linestyle='--', c=c)
        icolor += 1

    ax.legend(frameon=False, fontsize=fs - 3)
    for item in ax.get_xticklabels() + ax.get_yticklabels():
        item.set_fontsize(fs)
    fig.tight_layout()

    fig.canvas.set_window_title('{}_QSS_{}_dynamics_{:.2f}kPa'.format(
        neuron.name, varname, Adrive * 1e-3))

    return fig


def plotVarsQSS(neuron, a, Fdrive, Adrive, fs=12):
    ''' Plot effective membrane potential, quasi-steady states and resulting membrane currents
        as a function of membrane charge density, for a given acoustic amplitudes.

        :param neuron: neuron object
        :param a: sonophore radius (m)
        :param Fdrive: US frequency (Hz)
        :param Adrive: US amplitude (Pa)
        :return: figure handle
    '''

    # Get neuron-specific pltvars
    pltvars = neuron.getPltVars()

    # Compute neuron-specific charge and amplitude dependent QS states at this amplitude
    nbls = NeuronalBilayerSonophore(a, neuron, Fdrive)
    _, Qref, Vmeff, QS_states = nbls.quasiSteadyStates(Fdrive, amps=Adrive)

    # Compute QSS currents
    currents = neuron.currents(Vmeff, QS_states)
    iNet = sum(currents.values())

    # Extract dimensionless states
    norm_QS_states = {}
    for i, label in enumerate(neuron.states):
        if 'unit' not in pltvars[label]:
            norm_QS_states[label] = QS_states[i]

    # Create figure
    fig, axes = plt.subplots(3, 1, figsize=(7, 9))
    axes[-1].set_xlabel('Charge Density (nC/cm2)', fontsize=fs)
    for ax in axes:
        for skey in ['top', 'right']:
            ax.spines[skey].set_visible(False)
        for item in ax.get_xticklabels() + ax.get_yticklabels():
            item.set_fontsize(fs)
        for item in ax.get_xticklabels(minor=True):
            item.set_visible(False)
    figname = '{} neuron - QSS dynamics @ {:.2f} kPa'.format(neuron.name, Adrive * 1e-3)
    fig.suptitle(figname, fontsize=fs)

    # Subplot: Vmeff
    ax = axes[0]
    ax.set_ylabel('$V_m^*$ (mV)', fontsize=fs)
    ax.plot(Qref * 1e5, Vmeff, color='k')
    ax.axhline(neuron.Vm0, linewidth=0.5, color='k')

    # Subplot: dimensionless quasi-steady states
    cset = plt.get_cmap('tab10').colors + plt.get_cmap('Dark2').colors
    ax = axes[1]
    ax.set_ylabel('$X_\infty$', fontsize=fs)
    ax.set_yticks([0, 0.5, 1])
    ax.set_ylim([-0.05, 1.05])
    for i, (label, QS_state) in enumerate(norm_QS_states.items()):
        ax.plot(Qref * 1e5, QS_state, label=label, c=cset[i])

    # Subplot: currents
    ax = axes[2]
    ax.set_ylabel('QSS currents (A/m2)', fontsize=fs)
    for k, I in currents.items():
        ax.plot(Qref * 1e5, I * 1e-3, label=k)
    ax.plot(Qref * 1e5, iNet * 1e-3, color='k', label='iNet')
    ax.axhline(0, color='k', linewidth=0.5)

    fig.tight_layout()
    fig.subplots_adjust(right=0.8)
    for ax in axes[1:]:
        ax.legend(loc='center right', fontsize=fs, frameon=False, bbox_to_anchor=(1.3, 0.5))

    fig.canvas.set_window_title(
        '{}_QSS_states_vs_Qm_{:.2f}kPa'.format(neuron.name, Adrive * 1e-3))

    return fig


def plotQSSVarVsAmp(neuron, a, Fdrive, varname, amps=None, plotQm0=True,
                    fs=12, cmap='viridis', yscale='lin', zscale='lin'):
    ''' Plot a specific QSS variable (state or current) as a function of
        membrane charge density, for various acoustic amplitudes.

        :param neuron: neuron object
        :param a: sonophore radius (m)
        :param Fdrive: US frequency (Hz)
        :param amps: US amplitudes (Pa)
        :param varname: extraction key for variable to plot
        :return: figure handle
    '''

    # Extract information about variable to plot
    pltvar = neuron.getPltVars()[varname]
    Qvar = neuron.getPltVars()['Qm']

    # Get dictionary of charge and amplitude dependent QSS variables
    nbls = NeuronalBilayerSonophore(a, neuron, Fdrive)
    Aref, Qref, Vmeff, QS_states = nbls.quasiSteadyStates(Fdrive, amps=amps)
    df = {k: QS_states[i] for i, k in enumerate(neuron.states)}
    df['Vm'] = Vmeff

    #  Define color code
    mymap = plt.get_cmap(cmap)
    zref = Aref * 1e-3
    if zscale == 'lin':
        norm = colors.Normalize(zref.min(), zref.max())
    elif zscale == 'log':
        norm = colors.LogNorm(zref.min(), zref.max())
    sm = cm.ScalarMappable(norm=norm, cmap=mymap)
    sm._A = []

    # Plot QSS profile of variable as a function of charge density for various amplitudes
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.set_title('{} neuron\nquasi steady-state {} vs. amplitude'.format(
        neuron.name, pltvar['desc']), fontsize=fs)
    ax.set_xlabel('{} ($\\rm {}$)'.format(Qvar['desc'], Qvar['unit']), fontsize=fs)
    ax.set_ylabel('$\\rm QSS\ {}\ ({})$'.format(pltvar['label'], pltvar.get('unit', '')),
                  fontsize=fs)
    if yscale == 'log':
        ax.set_yscale('log')
    for key in ['top', 'right']:
        ax.spines[key].set_visible(False)

    if plotQm0:
        ax.axvline(neuron.Qm0() * 1e5, label='$\\rm Q_{m0}$', c='silver')
    y0_str = '{}0'.format(varname)
    if hasattr(neuron, y0_str):
        ax.axhline(getattr(neuron, y0_str) * pltvar.get('factor', 1),
                   label=y0_str, c='k', linewidth=0.5)
    for i, Adrive in enumerate(Aref):
        var = extractPltVar(
            neuron, pltvar, pd.DataFrame({k: df[k][i] for k in df.keys()}), name=varname)
        ax.plot(Qref * Qvar['factor'], var, c=sm.to_rgba(Adrive * 1e-3), zorder=0)
        if varname == 'iNet':
            SFPs = getStableFixedPoints(Qref, -var)
            if SFPs is not None:
                ax.plot(SFPs.max() * Qvar['factor'], 0, '.', c='k', zorder=1)
    if varname == 'iNet':
        ax.axhline(0, color='k', linewidth=0.5)

    ax.legend(frameon=False, fontsize=fs)
    for item in ax.get_xticklabels() + ax.get_yticklabels():
        item.set_fontsize(fs)
    fig.tight_layout()

    # Plot US amplitude colorbar
    fig.subplots_adjust(bottom=0.15, top=0.9, right=0.80, hspace=0.5)
    cbarax = fig.add_axes([0.85, 0.15, 0.03, 0.75])
    fig.colorbar(sm, cax=cbarax)
    cbarax.set_ylabel('Amplitude (kPa)', fontsize=fs)
    for item in cbarax.get_yticklabels():
        item.set_fontsize(fs)

    fig.canvas.set_window_title('{}_QSS_{}_vs_amp'.format(neuron.name, varname))

    return fig