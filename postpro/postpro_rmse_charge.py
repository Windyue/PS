#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author: Theo Lemaire
# @Date:   2016-11-01 16:35:43
# @Email: theo.lemaire@epfl.ch
# @Last Modified by:   Theo Lemaire
# @Last Modified time: 2018-08-21 16:07:33

""" Compute RMSE between charge profiles of NICE output. """

import sys
import pickle
import ntpath
import numpy as np

from PySONIC.utils import OpenFilesDialog, rmse

# Define options
pkl_root = "../../Output/test Elec/"
t_offset = 10e-3  # s

# Select data files (PKL)
pkl_filepaths, pkl_dir = OpenFilesDialog('pkl')

# Quit if no file selected
if not pkl_filepaths:
    print('error: no input file')
    sys.exit(1)

# Quit if more than 2 files
if len(pkl_filepaths) > 2:
    print('error: cannot compare more than 2 methods')
    sys.exit(1)

# Load data from file 1
pkl_filename = ntpath.basename(pkl_filepaths[0])
print('Loading data from "' + pkl_filename + '"')
with open(pkl_filepaths[0], 'rb') as fh:
    frame = pickle.load(fh)
    df = frame['data']
    meta = frame['meta']

tstim1 = meta['tstim']
toffset1 = meta['toffset']
f1 = meta['Fdrive']
A1 = meta['Adrive']
t1 = df['t'].values
Q1 = df['Qm'].values * 1e2  # nC/cm2
states1 = df['states'].values

# Load data from file 2
pkl_filename = ntpath.basename(pkl_filepaths[1])
print('Loading data from "' + pkl_filename + '"')
with open(pkl_filepaths[1], 'rb') as fh:
    frame = pickle.load(fh)
    df = frame['data']
    meta = frame['meta']

tstim2 = meta['tstim']
toffset2 = meta['toffset']
f2 = meta['Fdrive']
A2 = meta['Adrive']
t2 = df['t'].values
Q2 = df['Qm'].values * 1e2  # nC/cm2
states2 = df['states'].values

if tstim1 != tstim2 or f1 != f2 or A1 != A2 or toffset1 != toffset2:
    print('error: different stimulation conditions')
else:
    print('comparing charge profiles')

    tcomp = np.arange(0, tstim1 + toffset1, 1e-3)  # every ms
    Qcomp1 = np.interp(tcomp, t1, Q1)
    Qcomp2 = np.interp(tcomp, t2, Q2)
    Q_rmse = rmse(Qcomp1, Qcomp2)
    print('rmse = {:.5f} nC/cm2'.format(Q_rmse * 1e5))

