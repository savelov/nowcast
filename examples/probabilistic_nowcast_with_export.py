#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys
import pyximport
pyximport.install()

from tendo import singleton
from glob import glob

me = singleton.SingleInstance() # will sys.exit(-1) if other instance is running


"""Stochastic ensemble precipitation nowcasting

The script shows how to run a stochastic ensemble of precipitation nowcasts with
pysteps.

More info: https://pysteps.github.io/
"""
import datetime
import numpy as np
import pickle
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))

from pysteps_custom_utils.probability_nowcasting import nowcast_probability

import pysteps as stp
import config as cfg

# List of case studies that can be used in this tutorial

#+-------+--------------+-------------+----------------------------------------+
#| event |  start_time  | data_source | description                            |
#+=======+==============+=============+========================================+
#|  01   | 201701311030 |     mch     | orographic precipitation               |
#+-------+--------------+-------------+----------------------------------------+
#|  02   | 201505151630 |     mch     | non-stationary field, apparent rotation|
#+-------+--------------+------------------------------------------------------+
#|  03   | 201609281530 |     fmi     | stratiform rain band                   |
#+-------+--------------+-------------+----------------------------------------+
#|  04   | 201705091130 |     fmi     | widespread convective activity         |
#+-------+--------------+-------------+----------------------------------------+
#|  05   | 201806161100 |     bom     | bom example data                       |
#+-------+--------------+-------------+----------------------------------------+

# Set parameters for this tutorial
data_source="gimet"

## import data specifications
ds = cfg.get_specifications(data_source)


## input data (copy/paste values from table above)
archive_dir=ds.root_path+"/"+ds.path_fmt
last_fname=max(os.listdir(archive_dir))
print(last_fname)
startdate_str=last_fname[-18:-10]+last_fname[-9:-5]

print(startdate_str)

## methods
oflow_method        = "darts"     # lucaskanade, darts, None
nwc_method          = "steps"
adv_method          = "semilagrangian"  # semilagrangian, eulerian
noise_method        = "nonparametric"   # parametric, nonparametric, ssft
bandpass_filter     = "gaussian"
decomp_method       = "fft"

## forecast parameters
n_prvs_times        = 9                # use at least 9 with DARTS
n_leadtimes         = 12
n_ens_members       = 5
n_cascade_levels    = 6
ar_order            = 2
r_threshold         = 0.1               # rain/no-rain threshold [mm/h]
adjust_noise        = "auto"
prob_matching       = "mean"
precip_mask         = True
mask_method         = "incremental"     # sprog, obs or incremental
conditional         = False
unit                = "mm/h"            # mm/h or dBZ
transformation      = "dB"              # None or dB
adjust_domain       = None              # None or square
seed                = 42                # for reproducibility

vel_pert_kwargs = dict()
vel_pert_kwargs["p_par"] = [ 0.27159242, 0.80105668,  0.05984754]
vel_pert_kwargs["p_perp"] =  [ 2.42090851,  0.32323032, -3.66120619]


# Read-in the data
print('Read the data...', startdate_str)
startdate  = datetime.datetime.strptime(startdate_str, "%Y%m%d%H%M")

## import data specifications
ds = cfg.get_specifications(data_source)

## find radar field filenames
input_files = stp.io.find_by_date(startdate, ds.root_path, ds.path_fmt, ds.fn_pattern,
                                  ds.fn_ext, ds.timestep, n_prvs_times, 0)

## read radar field files
importer = stp.io.get_method(ds.importer, "importer")
R, _, metadata = stp.io.read_timeseries(input_files, importer, **ds.importer_kwargs)

# Prepare input files
print("Prepare the data...")

## if requested, make sure we work with a square domain
reshaper = stp.utils.get_method(adjust_domain)
R, metadata = reshaper(R, metadata, method="pad")

## if necessary, convert to rain rates [mm/h]
converter = stp.utils.get_method("mm/h")
R, metadata = converter(R, metadata)

## threshold the data
R[R<r_threshold] = 0.0
metadata["threshold"] = r_threshold

## convert the data
converter = stp.utils.get_method(unit)
R, metadata = converter(R, metadata)

## transform the data
transformer = stp.utils.get_method(transformation)
R, metadata = transformer(R, metadata)

nan_mask = np.ma.masked_invalid(R).mask
R[nan_mask] = metadata["zerovalue"] # to compute optical flow

# Compute motion field
oflow_method = stp.motion.get_method(oflow_method)
UV = oflow_method(R)

# Perform the nowcast
extrap_kwargs={}
extrap_kwargs['allow_nonfinite_values'] = True

# apply nan mask back
R[nan_mask] = np.nan

nwc_method = stp.nowcasts.get_method(nwc_method)
R_fct = nwc_method(R, UV,
    n_leadtimes,
    n_ens_members,
    n_cascade_levels=6,
    R_thr=-10.0,
    kmperpixel=metadata["xpixelsize"]/1000,
    timestep=10,
    decomp_method="fft",
    bandpass_filter_method="gaussian",
    noise_method="nonparametric",
    vel_pert_method="bps",
    mask_method="incremental",
    seed=seed,
    conserve_radar_mask=True,
    vel_pert_kwargs=vel_pert_kwargs)

## convert all data to mm/h
converter   = stp.utils.get_method("mm/h")
R_fct, _    = converter(R_fct, metadata)
R, metadata = converter(R, metadata)

## readjust to initial domain shape
R_fct, _    = reshaper(R_fct, metadata, inverse=True)
R, metadata = reshaper(R, metadata, inverse=True)

## export to file

filename = "%s/%s_%s.ncf" % (cfg.path_outputs, "probab_ensemble_nwc", startdate_str)
timestep  = ds.timestep
shape = (R_fct.shape[2], R_fct.shape[3])

prob_array = nowcast_probability(n_leadtimes, shape, R_fct)

# set -1 for nan
prob_array[np.isnan(prob_array)] = -1
export_initializer = stp.io.get_method('netcdf', 'exporter')
exporter = export_initializer(filename, startdate, timestep, n_leadtimes , shape, n_ens_members, metadata,
                              product='precip_probability', incremental=None)
stp.io.export_forecast_dataset(prob_array, exporter)
stp.io.close_forecast_file(exporter)
