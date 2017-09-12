#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author: Theo Lemaire
# @Date:   2017-02-13 18:16:09
# @Email: theo.lemaire@epfl.ch
# @Last Modified by:   Theo Lemaire
# @Last Modified time: 2017-09-10 18:42:42

""" Script to run ASTIM simulations from command line. """

import sys
import os
import logging
from argparse import ArgumentParser

from PointNICE.utils import logger, getNeuronsDict
from PointNICE.solvers import checkBatchLog, SolverUS, runAStim
from PointNICE.plt import plotBatch


# Default parameters
default = {
    'neuron': 'RS',
    'a': 32.0,  # nm
    'f': 500.0,  # kHz
    'A': 100.0,  # kPa
    't': 150.0,  # ms
    'off': 20.0,  # ms
    'PRF': 100.0,  # Hz
    'DC': 100.0,  # %
    'int_method': 'effective'
}


def main():

    # Define argument parser
    ap = ArgumentParser()

    # ASTIM parameters
    ap.add_argument('-n', '--neuron', type=str, default=default['neuron'],
                    help='Neuron name (string)')
    ap.add_argument('-a', '--diameter', type=float, default=default['a'],
                    help='BLS diameter (nm)')
    ap.add_argument('-f', '--frequency', type=float, default=default['f'],
                    help='Acoustic drive frequency (kHz)')
    ap.add_argument('-A', '--amplitude', type=float, default=default['A'],
                    help='Acoustic pressure amplitude (kPa)')
    ap.add_argument('-t', '--duration', type=float, default=default['t'],
                    help='Stimulus duration (ms)')
    ap.add_argument('--offset', type=float, default=default['off'],
                    help='Offset duration (ms)')
    ap.add_argument('--PRF', type=float, default=default['PRF'],
                    help='PRF (Hz)')
    ap.add_argument('--DC', type=float, default=default['DC'],
                    help='Duty cycle (%%)')
    ap.add_argument('-o', '--outputdir', type=str, default=os.getcwd(),
                    help='Output directory')
    ap.add_argument('-m', '--method', type=str, default=default['int_method'],
                    help='Numerical integration method ("classic", "hybrid" or "effective"')

    # Boolean parameters
    ap.add_argument('-v', '--verbose', default=False, action='store_true',
                    help='Increase verbosity')
    ap.add_argument('-p', '--plot', default=False, action='store_true',
                    help='Plot results')

    # Parse arguments
    args = ap.parse_args()
    neuron_str = args.neuron
    a = args.diameter * 1e-9  # m
    Fdrive = args.frequency * 1e3  # Hz
    Adrive = args.amplitude * 1e3  # Pa
    tstim = args.duration * 1e-3  # s
    toffset = args.offset * 1e-3  # s
    PRF = args.PRF  # Hz
    DC = args.DC * 1e-2
    output_dir = args.outputdir
    int_method = args.method

    if args.verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    PW_str = ', PRF = {:.2f} kHz, DC = {:.1f}'.format(PRF, DC * 1e2)

    try:
        assert neuron_str in getNeuronsDict(), '{} neuron type not implemented'.format(neuron_str)
        log_filepath, _ = checkBatchLog(output_dir, 'A-STIM')
        neuron = getNeuronsDict()[neuron_str]()
        logger.info('Running A-STIM simulation on %s neuron: a = %.1f nm, f = %.2f kHz, '
                    'A = %.2f kPa, t = %.2f ms%s (%s method)', neuron_str, a * 1e9, Fdrive * 1e-3,
                    Adrive * 1e-3, tstim * 1e3, PW_str if DC < 1.0 else "", int_method)
        solver = SolverUS(a, neuron, Fdrive)
        outfile = runAStim(output_dir, log_filepath, solver, neuron, Fdrive, Adrive, tstim,
                           toffset, PRF, DC, int_method)
        logger.info('Finished')
        if args.plot:
            plotBatch(output_dir, [outfile])

    except AssertionError as err:
        logger.error(err)
        sys.exit(1)


if __name__ == '__main__':
    main()
