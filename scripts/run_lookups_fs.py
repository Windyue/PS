#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author: Theo Lemaire
# @Date:   2017-06-02 17:50:10
# @Email: theo.lemaire@epfl.ch
# @Last Modified by:   Theo Lemaire
# @Last Modified time: 2019-03-14 23:38:55

''' Create lookup table for specific neuron. '''

import os
import pickle
import logging
import numpy as np
from argparse import ArgumentParser

from PySONIC.utils import logger, getNeuronLookupsFile
from PySONIC.batches import createQueue, runBatch
from PySONIC.neurons import getNeuronsDict
from PySONIC.core import NeuronalBilayerSonophore


# Default parameters
defaults = dict(
    neuron='RS',
    radius=32.0,  # nm
    freq=500,  # kHz
    amp=np.insert(np.logspace(np.log10(0.1), np.log10(600), num=50), 0, 0.0),  # kPa
)


def computeAStimLookups(neuron, a, Fdrive, Aref, Qref, fsref, mpi=False, loglevel=logging.INFO):

    # Check validity of input parameters
    for key, values in {'coverage fractions': fsref, 'amplitudes': Aref}.items():
        if not (isinstance(values, list) or isinstance(values, np.ndarray)):
            raise TypeError('Invalid {} (must be provided as list or numpy array)'.format(key))
        if not all(isinstance(x, float) for x in values):
            raise TypeError('Invalid {} (must all be float typed)'.format(key))
        if len(values) == 0:
            raise ValueError('Empty {} array'.format(key))
        if key is 'coverage fractions' and min(values) <= 0:
            raise ValueError('Invalid {} (must all be strictly positive)'.format(key))
        if key is 'amplitudes' and min(values) < 0:
            raise ValueError('Invalid {} (must all be positive or null)'.format(key))

    # populate inputs dictionary
    inputs = dict(
        fs=fsref,  # (-)
        A=Aref,  # Pa
        Q=Qref  # C/m2
    )

    # create simulation queue
    nA, nQ, nfs = len(Aref), len(Qref), len(fsref)
    queue = createQueue(([Fdrive], Aref, Qref, fsref))

    # run simulations and populate outputs (list of lists)
    logger.info('Starting simulation batch for %s neuron', neuron.name)
    nbls = NeuronalBilayerSonophore(a, neuron)
    outputs = runBatch(nbls, 'computeEffVars', queue, mpi=mpi, loglevel=loglevel)
    outputs = np.array(outputs).T

    # Split comp times and lookups
    tcomps = outputs[0]
    outputs = outputs[1:]

    # Reshape comp times into 4D array
    tcomps = tcomps.reshape(nA, nQ, nfs)

    # reshape outputs into 4D arrays and add them to lookups dictionary
    logger.info('Reshaping output into lookup tables')

    keys = ['V', 'ng'] + neuron.rates
    assert len(keys) == len(outputs), 'Lookup keys not matching array size'
    lookups = {}
    for key, output in zip(keys, outputs):
        lookups[key] = output.reshape(nA, nQ, nfs)

    # Store inputs, lookup data and comp times in dictionary
    df = {
        'input': inputs,
        'lookup': lookups,
        'tcomp': tcomps
    }

    return df


def main():
    ap = ArgumentParser()

    # Runtime options
    ap.add_argument('--mpi', default=False, action='store_true', help='Use multiprocessing')
    ap.add_argument('-v', '--verbose', default=False, action='store_true', help='Increase verbosity')
    ap.add_argument('-t', '--test', default=False, action='store_true', help='Test configuration')

    # Stimulation parameters
    ap.add_argument('-n', '--neuron', type=str, default=defaults['neuron'],
                    help='Neuron name (string)')
    ap.add_argument('-a', '--radius', type=float, default=defaults['radius'],
                    help='Sonophore radius (nm)')
    ap.add_argument('-f', '--freq', type=float, default=defaults['freq'],
                    help='US frequency (kHz)')
    ap.add_argument('-A', '--amp', nargs='+', type=float,
                    help='Acoustic pressure amplitude (kPa)')

    # Parse arguments
    args = {key: value for key, value in vars(ap.parse_args()).items() if value is not None}
    loglevel = logging.DEBUG if args['verbose'] is True else logging.INFO
    logger.setLevel(loglevel)
    mpi = args['mpi']
    neuron_str = args['neuron']
    a = args['radius'] * 1e-9  # m
    Fdrive = args['freq'] * 1e3  # Hz
    amps = np.array(args.get('amp', defaults['amp'])) * 1e3  # Pa
    fs = np.linspace(0, 100, 101) * 1e-2  # (-)

    # Check neuron name validity
    if neuron_str not in getNeuronsDict():
        logger.error('Unknown neuron type: "%s"', neuron_str)
        return
    neuron = getNeuronsDict()[neuron_str]()
    charges = np.arange(neuron.Qbounds()[0], neuron.Qbounds()[1] + 1e-5, 1e-5)  # C/m2

    if args['test']:
        fs = np.array([fs.min(), fs.max()])
        amps = np.array([amps.min(), amps.max()])
        charges = np.array([charges.min(), 0., charges.max()])

    # Check if lookup file already exists
    lookup_path = getNeuronLookupsFile(neuron.name, a=a, Fdrive=Fdrive, fs=True)

    if os.path.isfile(lookup_path):
        logger.warning('"%s" file already exists and will be overwritten. ' +
                       'Continue? (y/n)', lookup_path)
        user_str = input()
        if user_str not in ['y', 'Y']:
            logger.error('%s Lookup creation canceled', neuron.name)
            return

    # compute lookups
    df = computeAStimLookups(
        neuron, a, Fdrive, amps, charges, fs, mpi=mpi, loglevel=loglevel)

    # Save dictionary in lookup file
    logger.info('Saving %s neuron lookup table in file: "%s"', neuron.name, lookup_path)
    with open(lookup_path, 'wb') as fh:
        pickle.dump(df, fh)


if __name__ == '__main__':
    main()