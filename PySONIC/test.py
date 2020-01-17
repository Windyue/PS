# -*- coding: utf-8 -*-
# @Author: Theo Lemaire
# @Email: theo.lemaire@epfl.ch
# @Date:   2019-06-28 11:55:16
# @Last Modified by:   Theo Lemaire
# @Last Modified time: 2020-01-17 18:22:31

import os
import time
import cProfile
import pstats
import inspect
import matplotlib.pyplot as plt

from .utils import logger
from .parsers import TestParser


class TestBase:

    prefix = 'test_'
    parser_class = TestParser

    def execute(self, func_str, globals, locals, is_profiled):
        ''' Execute function with or without profiling. '''
        if is_profiled:
            pfile = 'tmp.stats'
            cProfile.runctx(func_str, globals, locals, pfile)
            stats = pstats.Stats(pfile)
            os.remove(pfile)
            stats.strip_dirs()
            stats.sort_stats('cumulative')
            stats.print_stats()
        else:
            eval(func_str, globals, locals)

    def buildtestSet(self):
        ''' Build list of candidate testsets. '''
        methods = inspect.getmembers(self, predicate=inspect.ismethod)
        testsets = {}
        n = len(self.prefix)
        for name, obj in methods:
            if name[:n] == self.prefix:
                testsets[name[n:]] = obj
        return testsets

    def parseCommandLineArgs(self, testsets):
        ''' Parse command line arguments. '''
        parser = self.parser_class(list(testsets.keys()))
        parser.addHideOutput()
        args = parser.parse()
        logger.setLevel(args['loglevel'])
        if args['profile'] and args['subset'] == 'all':
            raise ValueError('profiling can only be run on individual tests')
        return args

    def runTests(self, testsets, args):
        ''' Run appropriate tests. '''
        for s in args['subset']:
            testsets[s](args['profile'])

    def main(self):
        testsets = self.buildtestSet()
        try:
            args = self.parseCommandLineArgs(testsets)
        except ValueError as err:
            logger.error(err)
            return
        t0 = time.time()
        self.runTests(testsets, args)
        tcomp = time.time() - t0
        logger.info('tests completed in %.0f s', tcomp)
        if not args['hide']:
            plt.show()
