#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author: Theo Lemaire
# @Date:   2017-03-20 12:19:55
# @Email: theo.lemaire@epfl.ch
# @Last Modified by:   Theo Lemaire
# @Last Modified time: 2018-03-13 22:42:38

""" Batch plot profiles of several specific output variables of NICE simulations. """

import sys
import logging

from PointNICE.utils import logger, OpenFilesDialog
from PointNICE.plt import plotBatch

# Set logging level
logger.setLevel(logging.INFO)

# Select data files
pkl_filepaths, pkl_dir = OpenFilesDialog('pkl')
if not pkl_filepaths:
    logger.error('No input file')
    sys.exit(1)

# Plot profiles
try:
    # yvars = {'Q_m': ['Qm'], 'i_{Ca}\ kin.': ['s', 'u', 's2u'], 'I': ['iNa', 'iK', 'iT', 'iL']}
    yvars = {'Q_m': ['Qm']}
    plotBatch(pkl_dir, pkl_filepaths, title=False, vars_dict=yvars)
except AssertionError as err:
    logger.error(err)
    sys.exit(1)
