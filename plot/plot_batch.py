#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author: Theo Lemaire
# @Date:   2017-03-20 12:19:55
# @Email: theo.lemaire@epfl.ch
# @Last Modified by:   Theo Lemaire
# @Last Modified time: 2018-08-21 16:07:30

""" Batch plot profiles of several specific output variables of NICE simulations. """

import sys
import logging

from PySONIC.utils import logger, OpenFilesDialog, InputError
from PySONIC.plt import plotBatch

# Set logging level
logger.setLevel(logging.INFO)

# Select data files
pkl_filepaths, pkl_dir = OpenFilesDialog('pkl')
if not pkl_filepaths:
    logger.error('No input file')
    sys.exit(1)


yvars = {
    'V_m': ['Vm'],
    'i_{Na}\ kin.': ['m', 'h', 'm3h', 'n'],
    'i_K\ kin.': ['n'],
    'i_M\ kin.': ['p']
    # 'i_{CaL}\ kin.': ['q', 'r', 'q2r']
}

# Plot profiles
try:
    plotBatch(pkl_dir, pkl_filepaths, title=True, vars_dict=yvars)
except InputError as err:
    logger.error(err)
    sys.exit(1)
