# -*- coding: utf-8 -*-
# @Author: Theo Lemaire
# @Email: theo.lemaire@epfl.ch
# @Date:   2017-08-03 11:53:04
# @Last Modified by:   Theo Lemaire
# @Last Modified time: 2019-11-14 18:16:52

import os
from functools import wraps
from inspect import signature, getdoc
import pickle
import abc
import inspect
import numpy as np

from .batches import Batch
from ..utils import *


class Model(metaclass=abc.ABCMeta):
    ''' Generic model interface. '''

    titration_var = None

    @property
    @abc.abstractmethod
    def tscale(self):
        ''' Relevant temporal scale of the model. '''
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def simkey(self):
        ''' Keyword used to characterize simulations made with the model. '''
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def __repr__(self):
        ''' String representation. '''
        raise NotImplementedError

    def params(self):
        ''' Return a dictionary of all model parameters (class and instance attributes) '''
        def toAvoid(p):
            return (p.startswith('__') and p.endswith('__')) or p.startswith('_abc_')
        class_attrs = inspect.getmembers(self.__class__, lambda a: not(inspect.isroutine(a)))
        inst_attrs = inspect.getmembers(self, lambda a: not(inspect.isroutine(a)))
        class_attrs = [a for a in class_attrs if not toAvoid(a[0])]
        inst_attrs = [a for a in inst_attrs if not toAvoid(a[0]) and a not in class_attrs]
        params_dict = {a[0]: a[1] for a in class_attrs + inst_attrs}
        return params_dict

    @classmethod
    def description(cls):
        return getdoc(cls).split('\n', 1)[0].strip()

    @staticmethod
    @abc.abstractmethod
    def inputs():
        ''' Return an informative dictionary on input variables used to simulate the model. '''
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def filecodes(self, *args):
        ''' Return a dictionary of string-encoded inputs used for file naming. '''
        raise NotImplementedError

    def filecode(self, *args):
        return filecode(self, *args)

    @classmethod
    @abc.abstractmethod
    def getPltVars(self, *args, **kwargs):
        ''' Return a dictionary with information about all plot variables related to the model. '''
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def getPltScheme(self):
        ''' Return a dictionary model plot variables grouped by context. '''
        raise NotImplementedError

    @staticmethod
    def checkOutputDir(queuefunc):
        ''' Check if an output directory is provided in input arguments, and if so, add it
            to each item of the returned queue (along with an "overwrite" boolean).
        '''
        @wraps(queuefunc)
        def wrapper(self, *args, **kwargs):
            outputdir = kwargs.get('outputdir')
            queue = queuefunc(self, *args, **kwargs)
            if outputdir is not None:
                overwrite = kwargs.get('overwrite', True)
                queue = queuefunc(self, *args, **kwargs)
                for i, params in enumerate(queue):
                    position_args, keyword_args = Batch.resolve(params)
                    keyword_args['overwrite'] = overwrite
                    keyword_args['outputdir'] = outputdir
                    queue[i] = (position_args, keyword_args)
            else:
                if len(queue) > 5:
                    logger.warning('Running more than 5 simulations without file saving')
            return queue
        return wrapper

    @classmethod
    @abc.abstractmethod
    def simQueue(cls, *args, outputdir=None, overwrite=True):
        return NotImplementedError

    @staticmethod
    @abc.abstractmethod
    def checkInputs(self, *args):
        ''' Check the validity of simulation input parameters. '''
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def derivatives(self, *args, **kwargs):
        ''' Compute ODE derivatives for a specific set of ODE states and external parameters. '''
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def simulate(self, *args, **kwargs):
        ''' Simulate the model's differential system for specific input parameters
            and return output data in a dataframe. '''
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def meta(self, *args):
        ''' Return an informative dictionary about model and simulation parameters. '''
        raise NotImplementedError

    @staticmethod
    def addMeta(simfunc):
        ''' Add an informative dictionary about model and simulation parameters to simulation output '''

        @wraps(simfunc)
        def wrapper(self, *args, **kwargs):
            data, tcomp = timer(simfunc)(self, *args, **kwargs)
            logger.debug('completed in %ss', si_format(tcomp, 1))

            # Add keyword arguments from simfunc signature if not provided
            bound_args = signature(simfunc).bind(self, *args, **kwargs)
            bound_args.apply_defaults()
            target_args = dict(bound_args.arguments)

            # Try to retrieve meta information
            try:
                meta_params_names = list(signature(self.meta).parameters.keys())
                meta_params = [target_args[k] for k in meta_params_names]
                meta = self.meta(*meta_params)
            except KeyError as err:
                logger.error(f'Could not find {err} parameter in "{simfunc.__name__}" function')
                meta = {}

            # Add computation time to it
            meta['tcomp'] = tcomp

            # Return data with meta dict
            return data, meta

        return wrapper

    @staticmethod
    def logNSpikes(simfunc):
        ''' Log number of detected spikes on charge profile of simulation output. '''
        @wraps(simfunc)
        def wrapper(self, *args, **kwargs):
            out = simfunc(self, *args, **kwargs)
            if out is None:
                return None
            data, meta = out
            nspikes = self.getNSpikes(data)
            logger.debug('{} spike{} detected'.format(nspikes, plural(nspikes)))
            return data, meta

        return wrapper

    @staticmethod
    def checkSimParams(simfunc):
        ''' Check simulation parameters before launching simulation. '''
        @wraps(simfunc)
        def wrapper(self, *args, **kwargs):
            args, kwargs = alignWithMethodDef(simfunc, args, kwargs)
            self.checkInputs(*args, *list(kwargs.values()))
            return simfunc(self, *args, **kwargs)

        return wrapper

    @staticmethod
    def logDesc(simfunc):
        ''' Log description of model and simulation parameters. '''
        @wraps(simfunc)
        def wrapper(self, *args, **kwargs):
            args, kwargs = alignWithMethodDef(simfunc, args, kwargs)
            logger.info(self.desc(self.meta(*args, *list(kwargs.values()))))
            return simfunc(self, *args, **kwargs)

        return wrapper

    @staticmethod
    def checkTitrate(simfunc):
        ''' If "None" amplitude provided in the list of input parameters,
            perform a titration to find the threshold amplitude and add it to the list.
        '''
        @wraps(simfunc)
        def wrapper(self, *args, **kwargs):
            # Get argument index from function signature
            func_args = list(signature(simfunc).parameters.keys())[1:]
            iarg = func_args.index(self.titration_var)

            # If argument is None
            if args[iarg] is None:
                # Generate new args list without argument
                args = list(args)
                new_args = args.copy()
                del new_args[iarg]

                # Perform titration to find threshold argument value
                xthr = self.titrate(*new_args)
                if np.isnan(xthr):
                    logger.error(f'Could not find threshold {self.titration_var}')
                    return None

                # Re-insert it into arguments list
                args[iarg] = xthr

            # Execute simulation function
            return simfunc(self, *args, **kwargs)

        return wrapper

    def simAndSave(self, *args, **kwargs):
        return simAndSave(self, *args, **kwargs)

    def getOutput(self, outputdir, *args):
        ''' Get simulation output data for a specific parameters combination, by looking
            for an output file into a specific directory.

            If a corresponding output file is not found in the specified directory, the model
            is first run and results are saved in the output file.
        '''
        fpath = '{}/{}.pkl'.format(outputdir, self.filecode(*args))
        if not os.path.isfile(fpath):
            self.simAndSave(outputdir, *args, outputdir=outputdir)
        return loadData(fpath)
