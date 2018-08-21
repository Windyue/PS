#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author: Theo Lemaire
# @Date:   2017-02-13 12:41:26
# @Email: theo.lemaire@epfl.ch
# @Last Modified by:   Theo Lemaire
# @Last Modified time: 2018-08-21 16:07:31

""" Compare profiles of several specific output variables of NICE simulations. """

import sys
import logging

from PySONIC.utils import logger, OpenFilesDialog, InputError
from PySONIC.plt import plotComp

# Set logging level
logger.setLevel(logging.INFO)

# Select data files
pkl_filepaths, _ = OpenFilesDialog('pkl')
if not pkl_filepaths:
    logger.error('No input file')
    sys.exit(1)
nfiles = len(pkl_filepaths)

# Comparative plot
try:
    plotComp('Qm', pkl_filepaths)
except InputError as err:
    logger.error(err)
    sys.exit(1)
