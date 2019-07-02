# -*- coding: utf-8 -*-
# @Author: Theo Lemaire
# @Email: theo.lemaire@epfl.ch
# @Date:   2019-06-04 18:24:29
# @Last Modified by:   Theo Lemaire
# @Last Modified time: 2019-07-02 18:55:02

import os
import logging
import pprint
import numpy as np
import matplotlib.pyplot as plt
from argparse import ArgumentParser

from .utils import Intensity2Pressure, selectDirDialog, OpenFilesDialog, isIterable
from .neurons import getPointNeuron, CorticalRS
from .plt import GroupedTimeSeries, CompTimeSeries

DEFAULT_OUTPUT_FOLDER = os.path.abspath(os.path.split(__file__)[0] + '../../../../dump')


class Parser(ArgumentParser):
    ''' Generic parser interface. '''

    dist_str = '[scale min max n]'

    def __init__(self):
        super().__init__()
        self.pp = pprint.PrettyPrinter(indent=4)
        self.defaults = {}
        self.allowed = {}
        self.factors = {}
        self.to_parse = {}
        self.addPlot()
        self.addVerbose()

    def pprint(self, args):
        self.pp.pprint(args)

    def getDistribution(self, xmin, xmax, nx, scale='lin'):
        if scale == 'log':
            xmin, xmax = np.log10(xmin), np.log10(xmax)
        return {'lin': np.linspace, 'log': np.logspace}[scale](xmin, xmax, nx)

    def getDistFromList(self, xlist):
        if not isinstance(xlist, list):
            raise TypeError('Input must be a list')
        if len(xlist) != 4:
            raise ValueError('List must contain exactly 4 arguments ([type, min, max, n])')
        scale = xlist[0]
        if scale not in ('log', 'lin'):
            raise ValueError('Unknown distribution type (must be "lin" or "log")')
        xmin, xmax = [float(x) for x in xlist[1:-1]]
        if xmin >= xmax:
            raise ValueError('Specified minimum higher or equal than specified maximum')
        nx = int(xlist[-1])
        if nx < 2:
            raise ValueError('Specified number must be at least 2')
        return self.getDistribution(xmin, xmax, nx, scale=scale)

    def addVerbose(self):
        self.add_argument(
            '-v', '--verbose', default=False, action='store_true', help='Increase verbosity')
        self.to_parse['loglevel'] = self.parseLogLevel

    def addPlot(self):
        self.add_argument(
            '-p', '--plot', type=str, nargs='+', help='Variables to plot')
        self.to_parse['pltscheme'] = self.parsePltScheme

    def addMPI(self):
        self.add_argument(
            '--mpi', default=False, action='store_true', help='Use multiprocessing')

    def addTest(self):
        self.add_argument(
            '--test', default=False, action='store_true', help='Run test configuration')

    def addSave(self):
        self.add_argument(
            '-s', '--save', default=False, action='store_true', help='Save output figure(s)')

    def addFigureExtension(self):
        self.add_argument(
            '--figext', type=str, default='png', help='Figure type (extension)')

    def addCompare(self, desc='Comparative graph'):
        self.add_argument(
            '--compare', default=False, action='store_true', help=desc)

    def addSamplingRate(self):
        self.add_argument(
            '--sr', type=int, default=1, help='Sampling rate for plot')

    def addSpikes(self):
        self.add_argument(
            '--spikes', type=str, default='none',
            help='How to indicate spikes on charge profile ("none", "marks" or "details")')

    def addNColumns(self):
        self.add_argument(
            '--ncol', type=int, default=1, help='Number of columns in figure')

    def addNLevels(self):
        self.add_argument(
            '--nlevels', type=int, default=10, help='Number of levels')

    def addHideOutput(self):
        self.add_argument(
            '--hide', default=False, action='store_true', help='Hide output')

    def addTimeRange(self, default=None):
        self.add_argument(
            '--trange', type=float, nargs=2, default=default,
            help='Time lower and upper bounds (ms)')
        self.to_parse['trange'] = self.parseTimeRange

    def addPotentialBounds(self, default=None):
        self.add_argument(
            '--Vbounds', type=float, nargs=2, default=default,
            help='Membrane potential lower and upper bounds (mV)')

    def addFiringRateBounds(self, default):
        self.add_argument(
            '--FRbounds', type=float, nargs=2, default=default,
            help='Firing rate lower and upper bounds (Hz)')

    def addFiringRateScale(self, default='lin'):
        self.add_argument(
            '--FRscale', type=str, choices=('lin', 'log'), default=default,
            help='Firing rate scale for plot ("lin" or "log")')

    def addCmap(self, default=None):
        self.add_argument(
            '--cmap', type=str, default=default, help='Colormap name')

    def addCscale(self, default='lin'):
        self.add_argument(
            '--cscale', type=str, default=default, choices=('lin', 'log'),
            help='Color scale ("lin" or "log")')

    def addInputDir(self, dep_key=None):
        self.inputdir_dep_key = dep_key
        self.add_argument(
            '-i', '--inputdir', type=str, help='Input directory')
        self.to_parse['inputdir'] = self.parseInputDir

    def addOutputDir(self, dep_key=None):
        self.outputdir_dep_key = dep_key
        self.add_argument(
            '-o', '--outputdir', type=str, help='Output directory')
        self.to_parse['outputdir'] = self.parseOutputDir

    def addInputFiles(self, dep_key=None):
        self.inputfiles_dep_key = dep_key
        self.add_argument(
            '-i', '--inputfiles', type=str, help='Input files')
        self.to_parse['inputfiles'] = self.parseInputFiles

    def addPatches(self):
        self.add_argument(
            '--patches', type=str, default='one',
            help='Stimulus patching mode ("none", "one", all", or a boolean list)')
        self.to_parse['patches'] = self.parsePatches

    def addThresholdCurve(self):
        self.add_argument(
            '--threshold', default=False, action='store_true', help='Show threshold amplitudes')

    def addNeuron(self):
        self.add_argument(
            '-n', '--neuron', type=str, nargs='+', help='Neuron name (string)')
        self.to_parse['neuron'] = self.parseNeuron

    def parseNeuron(self, args):
        return [getPointNeuron(n) for n in args['neuron']]

    def addInteractive(self):
        self.add_argument(
            '--interactive', default=False, action='store_true', help='Make interactive')

    def addLabels(self):
        self.add_argument(
            '--labels', type=str, nargs='+', default=None, help='Labels')

    def addRelativeTimeBounds(self):
        self.add_argument(
            '--rel_tbounds', type=float, nargs='+', default=None,
            help='Relative time lower and upper bounds')

    def addPretty(self):
        self.add_argument(
            '--pretty', default=False, action='store_true', help='Make figure pretty')

    def addSubset(self, choices):
        self.add_argument(
            '--subset', type=str, nargs='+', default=['all'], choices=choices + ['all'],
            help='Run specific subset(s)')
        self.subset_choices = choices
        self.to_parse['subset'] = self.parseSubset

    def parseSubset(self, args):
        if args['subset'] == ['all']:
            return self.subset_choices
        else:
            return args['subset']

    def parseTimeRange(self, args):
        if args['trange'] is None:
            return None
        return np.array(args['trange']) * 1e-3

    def parsePatches(self, args):
        if args['patches'] not in ('none', 'one', 'all'):
            return eval(args['patches'])
        else:
            return args['patches']

    def parseInputFiles(self, args):
        if self.inputfiles_dep_key is not None and not args[self.inputfiles_dep_key]:
            return None
        elif args['inputfiles'] is None:
            return OpenFilesDialog('pkl')[0]

    def parseDir(self, key, args, title, dep_key=None):
        if dep_key is not None and args[dep_key] is False:
            return None
        try:
            if args[key] is not None:
                return os.path.abspath(args[key])
            else:
                return selectDirDialog(title=title)
        except ValueError:
            raise ValueError('No {} selected'.format(key))

    def parseInputDir(self, args):
        return self.parseDir(
            'inputdir', args, 'Select input directory', self.inputdir_dep_key)

    def parseOutputDir(self, args):
        if hasattr(self, 'outputdir') and self.outputdir is not None:
            return self.outputdir
        else:
            if args['outputdir'] is not None and args['outputdir'] == 'dump':
                return DEFAULT_OUTPUT_FOLDER
            else:
                return self.parseDir(
                    'outputdir', args, 'Select output directory', self.outputdir_dep_key)

    def parseLogLevel(self, args):
        return logging.DEBUG if args.pop('verbose') else logging.INFO

    def parsePltScheme(self, args):
        if args['plot'] is None or args['plot'] == ['all']:
            return None
        else:
            return {x: [x] for x in args['plot']}

    def restrict(self, args, keys):
        if sum([args[x] is not None for x in keys]) > 1:
            raise ValueError(
                'You must provide only one of the following arguments: {}'.format(', '.join(keys)))

    def parse2array(self, args, key, factor=1):
        return np.array(args[key]) * factor

    def parse(self):
        args = vars(super().parse_args())
        for k, v in self.defaults.items():
            if k in args and args[k] is None:
                args[k] = v if isIterable(v) else [v]
        for k, parse_method in self.to_parse.items():
            args[k] = parse_method(args)
        return args

    @staticmethod
    def parsePlot(args, output):
        render_args = {}
        if 'spikes' in args:
            render_args['spikes'] = args['spikes']
        if args['compare']:
            if args['plot'] == ['all']:
                logger.error('Specific variables must be specified for comparative plots')
                return
            for pltvar in args['plot']:
                comp_plot = CompTimeSeries(output, pltvar)
                comp_plot.render(**render_args)
        else:
            scheme_plot = GroupedTimeSeries(output, pltscheme=args['pltscheme'])
            scheme_plot.render(**render_args)
        plt.show()


class TestParser(Parser):
    def __init__(self, valid_subsets):
        super().__init__()
        self.addProfiling()
        self.addSubset(valid_subsets)

    def addProfiling(self):
        self.add_argument(
            '--profile', default=False, action='store_true', help='Run with profiling')


class FigureParser(Parser):

    def __init__(self, valid_subsets):
        super().__init__()
        self.addSubset(valid_subsets)
        self.addSave()
        self.addOutputDir(dep_key='save')


class PlotParser(Parser):
    def __init__(self):
        super().__init__()
        self.addHideOutput()
        self.addInputFiles()
        self.addOutputDir(dep_key='save')
        self.addSave()
        self.addFigureExtension()
        self.addCmap()
        self.addPretty()
        self.addTimeRange()
        self.addCscale()
        self.addLabels()


class TimeSeriesParser(PlotParser):
    def __init__(self):
        super().__init__()
        self.addSpikes()
        self.addSamplingRate()
        self.addCompare()
        self.addPatches()


class SimParser(Parser):
    ''' Generic simulation parser interface. '''

    def __init__(self, outputdir=None):
        super().__init__()
        self.outputdir = outputdir
        self.addMPI()
        self.addOutputDir(dep_key='save')
        self.addSave()
        self.addCompare()

    def parse(self):
        args = super().parse()
        return args


class MechSimParser(SimParser):
    ''' Parser to run mechanical simulations from the command line. '''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.defaults.update({
            'radius': 32.0,  # nm
            'embedding': 0.,  # um
            'Cm0': CorticalRS.Cm0 * 1e2,  # uF/m2
            'Qm0': CorticalRS.Qm0() * 1e5,  # nC/m2
            'freq': 500.0,  # kHz
            'amp': 100.0,  # kPa
            'charge': 0.,  # nC/cm2
            'fs': 100.  # %
        })

        self.factors.update({
            'radius': 1e-9,
            'embedding': 1e-6,
            'Cm0': 1e-2,
            'Qm0': 1e-5,
            'freq': 1e3,
            'amp': 1e3,
            'charge': 1e-5,
            'fs': 1e-2
        })

        self.addRadius()
        self.addEmbedding()
        self.addCm0()
        self.addQm0()
        self.addFdrive()
        self.addAdrive()
        self.addCharge()
        self.addFs()

    def addRadius(self):
        self.add_argument(
            '-a', '--radius', nargs='+', type=float, help='Sonophore radius (nm)')

    def addEmbedding(self):
        self.add_argument(
            '--embedding', nargs='+', type=float, help='Embedding depth (um)')

    def addCm0(self):
        self.add_argument(
            '--Cm0', type=float, help='Resting membrane capacitance (uF/cm2)')

    def addQm0(self):
        self.add_argument(
            '--Qm0', type=float, help='Resting membrane charge density (nC/cm2)')

    def addFdrive(self):
        self.add_argument(
            '-f', '--freq', nargs='+', type=float, help='US frequency (kHz)')

    def addAdrive(self):
        self.add_argument(
            '-A', '--amp', nargs='+', type=float, help='Acoustic pressure amplitude (kPa)')
        self.add_argument(
            '--Arange', type=str, nargs='+',
            help='Amplitude range {} (kPa)'.format(self.dist_str))
        self.add_argument(
            '-I', '--intensity', nargs='+', type=float, help='Acoustic intensity (W/cm2)')
        self.add_argument(
            '--Irange', type=str, nargs='+',
            help='Intensity range {} (W/cm2)'.format(self.dist_str))
        self.to_parse['amp'] = self.parseAmp

    def addAscale(self, default='lin'):
        self.add_argument(
            '--Ascale', type=str, choices=('lin', 'log'), default=default,
            help='Amplitude scale for plot ("lin" or "log")')

    def addCharge(self):
        self.add_argument(
            '-Q', '--charge', nargs='+', type=float, help='Membrane charge density (nC/cm2)')

    def addFs(self):
        self.add_argument(
            '--fs', nargs='+', type=float, help='Sonophore coverage fraction (%%)')
        self.add_argument(
            '--spanFs', default=False, action='store_true', help='Span Fs from 1 to 100%%')
        self.to_parse['fs'] = self.parseFs

    def parseAmp(self, args):
        params = ['Irange', 'Arange', 'intensity', 'amp']
        self.restrict(args, params[:-1])
        Irange, Arange, Int, Adrive = [args.pop(k) for k in params]
        if Irange is not None:
            amps = Intensity2Pressure(self.getDistFromList(Irange) * 1e4)  # Pa
        elif Int is not None:
            amps = Intensity2Pressure(np.array(Int) * 1e4)  # Pa
        elif Arange is not None:
            amps = self.getDistFromList(Arange) * self.factors['amp']  # Pa
        else:
            amps = np.array(Adrive) * self.factors['amp']  # Pa
        return amps

    def parseFs(self, args):
        if args.pop('spanFs', False):
            return np.arange(1, 101) * self.factors['fs']  # (-)
        else:
            return np.array(args['fs']) * self.factors['fs']  # (-)

    def parse(self):
        args = super().parse()
        for key in ['radius', 'embedding', 'Cm0', 'Qm0', 'freq', 'charge']:
            args[key] = self.parse2array(args, key, factor=self.factors[key])
        return args

    @staticmethod
    def parseSimInputs(args):
        return [args[k] for k in ['freq', 'amp', 'charge']]


class PWSimParser(SimParser):
    ''' Generic parser interface to run PW patterned simulations from the command line. '''

    def __init__(self):
        super().__init__()

        self.defaults.update({
            'neuron': 'RS',
            'tstim': 100.0,  # ms
            'toffset': 50.,  # ms
            'PRF': 100.0,  # Hz
            'DC': 100.0  # %
        })

        self.factors.update({
            'tstim': 1e-3,
            'toffset': 1e-3,
            'PRF': 1.,
            'DC': 1e-2
        })

        self.allowed.update({
            'DC': range(101)
        })

        self.addNeuron()
        self.addTstim()
        self.addToffset()
        self.addPRF()
        self.addDC()
        self.addTitrate()
        self.addSpikes()

    def addTstim(self):
        self.add_argument(
            '-t', '--tstim', nargs='+', type=float, help='Stimulus duration (ms)')

    def addToffset(self):
        self.add_argument(
            '--toffset', nargs='+', type=float, help='Offset duration (ms)')

    def addPRF(self):
        self.add_argument(
            '--PRF', nargs='+', type=float, help='PRF (Hz)')

    def addDC(self):
        self.add_argument(
            '--DC', nargs='+', type=float, help='Duty cycle (%%)')
        self.add_argument(
            '--spanDC', default=False, action='store_true', help='Span DC from 1 to 100%%')
        self.to_parse['DC'] = self.parseDC

    def addTitrate(self):
        self.add_argument(
            '--titrate', default=False, action='store_true', help='Perform titration')

    def parseAmp(self, args):
        return NotImplementedError

    def parseDC(self, args):
        if args.pop('spanDC'):
            return np.arange(1, 101) * self.factors['DC']  # (-)
        else:
            return np.array(args['DC']) * self.factors['DC']  # (-)

    def parse(self, args=None):
        if args is None:
            args = super().parse()
        for key in ['tstim', 'toffset', 'PRF']:
            args[key] = self.parse2array(args, key, factor=self.factors[key])
        return args

    @staticmethod
    def parseSimInputs(args):
        return [args[k] for k in ['amp', 'tstim', 'toffset', 'PRF', 'DC']]


class EStimParser(PWSimParser):
    ''' Parser to run E-STIM simulations from the command line. '''

    def __init__(self):
        super().__init__()
        self.defaults.update({'amp': 10.0})  # mA/m2
        self.factors.update({'amp': 1.})
        self.addAstim()

    def addAstim(self):
        self.add_argument(
            '-A', '--amp', nargs='+', type=float,
            help='Amplitude of injected current density (mA/m2)')
        self.add_argument(
            '--Arange', type=str, nargs='+',
            help='Amplitude range {} (mA/m2)'.format(self.dist_str))
        self.to_parse['amp'] = self.parseAmp

    def addVext(self):
        self.add_argument(
            '--Vext', nargs='+', type=float, help='Extracellular potential (mV)')

    def parseAmp(self, args):
        if args.pop('titrate'):
            return None
        Arange, Astim = [args.pop(k) for k in ['Arange', 'amp']]
        if Arange is not None:
            amps = self.getDistFromList(Arange) * self.factors['amp']  # mA/m2
        else:
            amps = np.array(Astim) * self.factors['amp']  # mA/m2
        return amps


class AStimParser(PWSimParser, MechSimParser):
    ''' Parser to run A-STIM simulations from the command line. '''

    def __init__(self):
        MechSimParser.__init__(self)
        PWSimParser.__init__(self)
        self.defaults.update({'method': 'sonic'})
        self.allowed.update({'method': ['full', 'hybrid', 'sonic']})
        self.addMethod()

    def addMethod(self):
        self.add_argument(
            '-m', '--method', nargs='+', type=str,
            help='Numerical integration method ({})'.format(', '.join(self.allowed['method'])))
        self.to_parse['method'] = self.parseMethod

    def parseMethod(self, args):
        for item in args['method']:
            if item not in self.allowed['method']:
                raise ValueError('Unknown method type: "{}"'.format(item))
        return args['method']

    def parseAmp(self, args):
        if args.pop('titrate'):
            return None
        return MechSimParser.parseAmp(self, args)

    def parse(self):
        args = PWSimParser.parse(self, args=MechSimParser.parse(self))
        for k in ['Cm0', 'Qm0', 'embedding', 'charge']:
            del args[k]
        return args

    @staticmethod
    def parseSimInputs(args):
        return [args['freq']] + PWSimParser.parseSimInputs(args) + [args[k] for k in ['fs', 'method']]




