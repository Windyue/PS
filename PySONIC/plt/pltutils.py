# -*- coding: utf-8 -*-
# @Author: Theo Lemaire
# @Date:   2017-08-21 14:33:36
# @Last Modified by:   Theo Lemaire
# @Last Modified time: 2019-03-15 00:18:45

''' Dictionary of plotting settings for output variables of the model.  '''

import re
import numpy as np
import matplotlib

from ..core import BilayerSonophore, NeuronalBilayerSonophore
from ..neurons import getNeuronsDict

# Matplotlib parameters
matplotlib.rcParams['pdf.fonttype'] = 42
matplotlib.rcParams['ps.fonttype'] = 42
matplotlib.rcParams['font.family'] = 'arial'

rgxp = re.compile('(ESTIM|ASTIM)_([A-Za-z]*)_(.*).pkl')
rgxp_mech = re.compile('(MECH)_(.*).pkl')


def cm2inch(*tupl):
    inch = 2.54
    if isinstance(tupl[0], tuple):
        return tuple(i / inch for i in tupl[0])
    else:
        return tuple(i / inch for i in tupl)


def getTimePltVar(tscale):
    ''' Return time plot variable for a given temporal scale. '''
    return {
        'desc': 'time',
        'label': 'time',
        'unit': tscale,
        'factor': {'ms': 1e3, 'us': 1e6}[tscale],
        'onset': {'ms': 1e-3, 'us': 1e-6}[tscale]
    }


def getSimType(fname):
    ''' Get sim type from filename. '''
    for exp in [rgxp, rgxp_mech]:
        mo = exp.fullmatch(fname)
        if mo:
            sim_type = mo.group(1)
            if sim_type not in ('MECH', 'ASTIM', 'ESTIM'):
                raise ValueError('Invalid simulation type: {}'.format(sim_type))
            return sim_type
    raise ValueError('Error: "{}" file does not match regexp pattern'.format(fname))


def getObject(sim_type, meta):
    if sim_type == 'MECH':
        obj = BilayerSonophore(meta['a'], meta['Cm0'], meta['Qm0'])
    else:
        obj = getNeuronsDict()[meta['neuron']]()
        if sim_type == 'ASTIM':
            obj = NeuronalBilayerSonophore(meta['a'], obj, meta['Fdrive'])
    return obj


def getStimPulses(t, states):
    ''' Determine the onset and offset times of pulses from a stimulation vector.

        :param t: time vector (s).
        :param states: a vector of stimulation state (ON/OFF) at each instant in time.
        :return: 3-tuple with number of patches, timing of STIM-ON an STIM-OFF instants.
    '''

    # Compute states derivatives and identify bounds indexes of pulses
    dstates = np.diff(states)
    ipulse_on = np.insert(np.where(dstates > 0.0)[0] + 1, 0, 0)
    ipulse_off = np.where(dstates < 0.0)[0] + 1
    if ipulse_off.size < ipulse_on.size:
        ioff = t.size - 1
        if ipulse_off.size == 0:
            ipulse_off = np.array([ioff])
        else:
            ipulse_off = np.insert(ipulse_off, ipulse_off.size - 1, ioff)

    # Get time instants for pulses ON and OFF
    npulses = ipulse_on.size
    tpulse_on = t[ipulse_on]
    tpulse_off = t[ipulse_off]

    # return 3-tuple with #pulses, pulse ON and pulse OFF instants
    return npulses, tpulse_on, tpulse_off


def plotStimPatches(ax, tpatch_on, tpatch_off, tfactor):
    for j in range(tpatch_on.size):
        ax.axvspan(tpatch_on[j] * tfactor, tpatch_off[j] * tfactor,
                   edgecolor='none', facecolor='#8A8A8A', alpha=0.2)


def extractPltVar(obj, pltvar, df, meta, nsamples, name):
    if 'func' in pltvar:
        s = 'obj.{}'.format(pltvar['func'])
        try:
            var = eval(s)
        except AttributeError:
            var = eval(s.replace('obj', 'obj.neuron'))
    elif 'key' in pltvar:
        var = df[pltvar['key']]
    elif 'constant' in pltvar:
        var = eval(pltvar['constant']) * np.ones(nsamples)
    else:
        var = df[name]

    if var.size == nsamples - 2:
        var = np.hstack((np.array([pltvar.get('y0', var[0])] * 2), var))
    var *= pltvar.get('factor', 1)

    return var



tmp = {
    'Nai': {
        'desc': 'sumbmembrane Na+ concentration',
        'label': '[Na^+]_i',
        'unit': 'uM',
        'factor': 1e6
    },

    'Nai_arb': {
        'key': 'Nai',
        'desc': 'submembrane Na+ concentration',
        'label': '[Na^+]',
        'unit': 'arb.',
        'factor': 1
    },

    'C_Na_arb_activation': {
        'key': 'A_Na',
        'desc': 'Na+ dependent PumpNa current activation',
        'label': 'A_{Na^+}',
        'unit': 'arb',
        'factor': 1
    },

    'C_Ca_arb': {
        'key': 'C_Ca',
        'desc': 'submembrane Ca2+ concentration',
        'label': '[Ca^{2+}]',
        'unit': 'arb.',
        'factor': 1
    },

    'C_Ca_arb_activation': {
        'key': 'A_Ca',
        'desc': 'Ca2+ dependent Potassium current activation',
        'label': 'A_{Ca^{2+}}',
        'unit': 'arb',
        'factor': 1
    },

}
