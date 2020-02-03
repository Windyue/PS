# -*- coding: utf-8 -*-
# @Author: Theo Lemaire
# @Email: theo.lemaire@epfl.ch
# @Date:   2018-09-26 09:51:43
# @Last Modified by:   Theo Lemaire
# @Last Modified time: 2020-02-03 21:36:53

''' Plot (duty-cycle x amplitude) US activation map of a neuron at a given frequency and PRF. '''

import numpy as np
import matplotlib.pyplot as plt

from PySONIC.utils import logger
from PySONIC.plt import ActivationMap
from PySONIC.parsers import AStimParser


def main():

    # Parse command line arguments
    parser = AStimParser()
    parser.defaults['amp'] = np.logspace(np.log10(10), np.log10(600), 30)  # kPa
    parser.defaults['DC'] = np.arange(1, 101)  # %
    parser.defaults['tstim'] = 1000.  # ms
    parser.defaults['toffset'] = 0.  # ms
    parser.addInputDir()
    parser.addThresholdCurve()
    parser.addInteractive()
    parser.addAscale()
    parser.addTimeRange(default=(0., 240.))
    parser.addFiringRateBounds((1e0, 1e3))
    parser.addFiringRateScale()
    parser.addPotentialBounds(default=(-150, 50))
    parser.outputdir_dep_key = 'save'
    args = parser.parse()
    logger.setLevel(args['loglevel'])

    for pneuron in args['neuron']:
        for a in args['radius']:
            for f in args['freq']:
                for tstim in args['tstim']:
                    for PRF in args['PRF']:
                        actmap = ActivationMap(args['inputdir'], pneuron, a, f, tstim, PRF,
                                               args['amp'], args['DC'])
                        actmap.render(
                            cmap=args['cmap'],
                            Ascale=args['Ascale'],
                            FRscale=args['FRscale'],
                            FRbounds=args['FRbounds'],
                            interactive=args['interactive'],
                            Vbounds=args['Vbounds'],
                            trange=args['trange'],
                            thresholds=args['threshold'],
                        )

    plt.show()


if __name__ == '__main__':
    main()
