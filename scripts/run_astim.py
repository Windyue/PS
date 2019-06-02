#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author: Theo Lemaire
# @Date:   2017-02-13 18:16:09
# @Email: theo.lemaire@epfl.ch
# @Last Modified by:   Theo Lemaire
# @Last Modified time: 2019-06-02 15:48:03

''' Run A-STIM simulations of a specific point-neuron. '''

import os
import logging
import numpy as np
import matplotlib.pyplot as plt
from argparse import ArgumentParser

from PySONIC.core import NeuronalBilayerSonophore, Batch
from PySONIC.utils import logger, selectDirDialog, parseUSAmps, getInDict
from PySONIC.neurons import getNeuronsDict
from PySONIC.plt import plotBatch

# Default parameters
defaults = dict(
    neuron='RS',
    radius=[32.0],  # nm
    freq=[500.0],  # kHz
    amp=[100.0],  # kPa
    duration=[100.0],  # ms
    PRF=[100.0],  # Hz
    DC=[100.0],  # %
    offset=[50.],  # ms
    method='sonic'
)


def runAStimBatch(outdir, nbls, stim_params, method, mpi=False, loglevel=logging.INFO):
    ''' Run batch A-STIM simulations of the system for various neuron types and
        stimulation parameters.

        :param outdir: full path to output directory
        :param stim_params: dictionary containing sweeps for all stimulation parameters
        :param method: numerical integration method ("classic", "hybrid" or "sonic")
        :param mpi: boolean statting wether or not to use multiprocessing
        :param loglevel: logging level
        :return: list of full paths to the output files
    '''

    mandatory_params = ['freqs', 'durations', 'offsets', 'PRFs', 'DCs']
    for mparam in mandatory_params:
        if mparam not in stim_params:
            raise ValueError('Missing stimulation parameter field: "{}"'.format(mparam))

    logger.info("Starting A-STIM simulation batch")

    # Generate queue
    queue = nbls.simQueue(
        stim_params['freqs'],
        stim_params.get('amps', None),
        stim_params['durations'],
        stim_params['offsets'],
        stim_params['PRFs'],
        stim_params['DCs'],
        method
    )
    for item in queue:
        item.insert(0, outdir)

    # Run batch
    batch = Batch(nbls.runAndSave, queue)
    return batch(mpi=mpi, loglevel=loglevel)


def main():
    ap = ArgumentParser()

    # Runtime options
    ap.add_argument('--mpi', default=False, action='store_true', help='Use multiprocessing')
    ap.add_argument('-v', '--verbose', default=False, action='store_true',
                    help='Increase verbosity')
    ap.add_argument('-p', '--plot', type=str, nargs='+', help='Variables to plot')
    ap.add_argument('-o', '--outputdir', type=str, default=None, help='Output directory')
    ap.add_argument('-t', '--titrate', default=False, action='store_true', help='Perform titration')
    ap.add_argument('-m', '--method', type=str, default=defaults['method'],
                    help='Numerical integration method ("classic", "hybrid" or "sonic")')

    # Stimulation parameters
    ap.add_argument('-n', '--neuron', type=str, default=defaults['neuron'],
                    help='Neuron name (string)')
    ap.add_argument('-a', '--radius', nargs='+', type=float, help='Sonophore radius (nm)')
    ap.add_argument('-f', '--freq', nargs='+', type=float, help='US frequency (kHz)')
    ap.add_argument('-A', '--amp', nargs='+', type=float, help='Acoustic pressure amplitude (kPa)')
    ap.add_argument('--Arange', type=str, nargs='+', help='Amplitude range [scale min max n] (kPa)')
    ap.add_argument('-I', '--intensity', nargs='+', type=float, help='Acoustic intensity (W/cm2)')
    ap.add_argument('--Irange', type=str, nargs='+',
                    help='Intensity range [scale min max n] (W/cm2)')
    ap.add_argument('-d', '--duration', nargs='+', type=float, help='Stimulus duration (ms)')
    ap.add_argument('--offset', nargs='+', type=float, help='Offset duration (ms)')
    ap.add_argument('--PRF', nargs='+', type=float, help='PRF (Hz)')
    ap.add_argument('--DC', nargs='+', type=float, help='Duty cycle (%%)')
    ap.add_argument('--spanDC', default=False, action='store_true', help='Span DC from 1 to 100%')

    # Parse arguments
    args = {key: value for key, value in vars(ap.parse_args()).items() if value is not None}
    loglevel = logging.DEBUG if args['verbose'] is True else logging.INFO
    logger.setLevel(loglevel)
    outdir = getInDict(args, 'outputdir', selectDirDialog)
    if outdir == '':
        logger.error('No output directory selected')
        quit()
    mpi = args['mpi']
    titrate = args['titrate']
    method = args['method']
    neuron_str = args['neuron']
    radii = np.array(args.get('radius', defaults['radius'])) * 1e-9  # m

    try:
        amps = parseUSAmps(args, defaults)
    except ValueError as err:
        logger.error(err)
        quit()

    if args['spanDC']:
        DCs = np.arange(1, 101)  # %
    else:
        DCs = np.array(args.get('DC', defaults['DC']))  # %

    stim_params = dict(
        freqs=np.array(args.get('freq', defaults['freq'])) * 1e3,  # Hz
        amps=amps,  # Pa
        durations=np.array(args.get('duration', defaults['duration'])) * 1e-3,  # s
        PRFs=np.array(args.get('PRF', defaults['PRF'])),  # Hz
        DCs=DCs * 1e-2,  # (-)
        offsets=np.array(args.get('offset', defaults['offset'])) * 1e-3  # s
    )

    if titrate:
        stim_params['amps'] = None

    # Run A-STIM batch
    if neuron_str not in getNeuronsDict():
        logger.error('Unknown neuron type: "%s"', neuron_str)
        return
    neuron = getNeuronsDict()[neuron_str]()
    pkl_filepaths = []
    for a in radii:
        nbls = NeuronalBilayerSonophore(a, neuron)
        pkl_filepaths += runAStimBatch(outdir, nbls, stim_params, method,
                                       mpi=mpi, loglevel=loglevel)
    pkl_dir, _ = os.path.split(pkl_filepaths[0])

    # Plot resulting profiles
    if 'plot' in args:
        if args['plot'] == ['all']:
            pltscheme = None
        else:
            pltscheme = {x: [x] for x in args['plot']}
        plotBatch(pkl_filepaths, pltscheme=pltscheme)
        plt.show()


if __name__ == '__main__':
    main()
