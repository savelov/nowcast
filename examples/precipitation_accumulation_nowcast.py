#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys
import pyximport
import copy

import pysteps.utils

pyximport.install()

from tendo import singleton

me = singleton.SingleInstance() # will sys.exit(-1) if other instance is running


"""Stochastic ensemble precipitation nowcasting

The script shows how to run a stochastic ensemble of precipitation nowcasts with
pysteps.

More info: https://pysteps.github.io/
"""
import datetime
import numpy as np
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))

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
archive_dir=ds.root_path
#+"/"+max(os.listdir(ds.root_path))
last_fname=max(os.listdir(archive_dir))
print(last_fname)
startdate_str=last_fname[-18:-10]+last_fname[-9:-5]

print(startdate_str)

## methods
oflow_method        = "lucaskanade"     # lucaskanade, darts, None
nwc_method          = "steps"
adv_method          = "semilagrangian"  # semilagrangian, eulerian
noise_method        = "nonparametric"   # parametric, nonparametric, ssft
bandpass_filter     = "gaussian"
decomp_method       = "fft"

## forecast parameters
n_prvs_times        = 6                # use at least 9 with DARTS
n_leadtimes         = 12                # use 6 for one hour extrapolation and 12 for 2 hours extrapolation
r_threshold         = 0.01              # rain/no-rain threshold [mm/h]
unit                = "mm/h"            # mm/h or dBZ
transformation      = "dB"              # None or dB
adjust_domain       = None              # None or square
output_time_step = 1

vel_pert_kwargs = dict()
vel_pert_kwargs["p_par"] = [ 0.38550792, 0.62097167, -0.23937287]
vel_pert_kwargs["p_perp"] = [0.2240485, 0.68900218, 0.24242502]

a = 200.0
b = 1.6

# Read-in the data
print('Read the data...', startdate_str)
startdate  = datetime.datetime.strptime(startdate_str, "%Y%m%d%H%M")
# startdate = datetime.datetime(2019, 10, 7, 18, 40)
## import data specifications
ds = cfg.get_specifications(data_source)

## find radar field filenames
input_files = stp.io.find_by_date(startdate, ds.root_path, ds.path_fmt, ds.fn_pattern,
                                  ds.fn_ext, ds.timestep, n_prvs_times, 0)

## read radar field files
importer = stp.io.get_method(ds.importer, "importer")
R, _, metadata = stp.io.read_timeseries(input_files, importer, **ds.importer_kwargs)

# Preprocess the data
# R = convert_dbz_to_mm(R)

# Prepare input files
print("Prepare the data...")

## if requested, make sure we work with a square domain
reshaper = stp.utils.get_method(adjust_domain)
R, metadata = reshaper(R, metadata, method="pad")

## if necessary, convert to rain rates [mm/h]
converter = stp.utils.get_method("mm/h")
R, metadata = converter(R, metadata, a=a, b=b)

## threshold the data
R[R<r_threshold] = 0.0
metadata["threshold"] = r_threshold

## convert the data
# converter = stp.utils.get_method(unit)
# R, metadata = converter(R, metadata)

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

# extrapolate at ten minute time step
extrapolate = stp.nowcasts.get_method("extrapolation")
R_calc = extrapolate(R[-1], UV, n_leadtimes, allow_nans=True)

R_all = np.append(R, R_calc, axis=0)

R_all_ref = copy.deepcopy(R_all)

# per minute precipitation
R_all = R_all/60
slow_UV = UV - (UV/10)*(10-output_time_step)    # one minute motion vectors

R_computed = np.zeros((R_all.shape[0], R.shape[1], R.shape[2]))

ten_min_sum = np.zeros((R_all.shape[1], R_all.shape[2]))

# compute sum at 10 min timestep
for i in range(R_all.shape[0]):
    if i == 0:
        R_computed[i] = R_all[i]
        ten_min_sum = R_computed[i]
    else:
        for j in range(10):
            one_min_nowcast = extrapolate(ten_min_sum, slow_UV, 1, allow_nans=True)
            ten_min_sum += one_min_nowcast[0]
        R_computed[i] = ten_min_sum
        ten_min_sum = R_all[i]

print(R_computed.shape)

# compute sum at one hour
R_final = np.zeros((R_all.shape[0]-6, R.shape[1], R.shape[2]))
for i in range(R_final.shape[0]):
    if i == 0:
        R_final[i] = np.sum(R_computed[:6], axis=0)
    else:
        index = i+6
        R_final[i] = np.sum(R_computed[index-6: index], axis=0)

## export precip accumulation to file
filename = "%s/%s_%s.ncf" % (cfg.path_outputs, "precip_accum_nwc", startdate_str)
timestep  = ds.timestep
shape = (R_final.shape[1], R_final.shape[2])
metadata['unit'] = 'mm'
n_leadtimes = R_final.shape[0]

# # set -1 for nan
R_final[np.isnan(R_final)] = -1
export_initializer = stp.io.get_method('netcdf', 'exporter')
exporter = export_initializer(filename, startdate, 10, n_leadtimes, shape, 1, metadata,
                              incremental=None)
stp.io.export_forecast_dataset(R_final, exporter)
stp.io.close_forecast_file(exporter)

# export 10 min precipitation nowcasts to file
filename = "%s/%s_%s.ncf" % (cfg.path_outputs, "precip_nwc", startdate_str)
shape = (R_calc.shape[1], R_calc.shape[2])
metadata['unit'] = 'mm/h'
n_leadtimes = R_calc.shape[0]

# # set -1 for nan
#Back-transform to rain rates
R_calc = pysteps.utils.transformation.dB_transform(R_calc, threshold=-20.0, inverse=True)[0]

R_calc[np.isnan(R_calc)] = -1
export_initializer = stp.io.get_method('netcdf', 'exporter')
exporter = export_initializer(filename, startdate, 10, n_leadtimes, shape, 1, metadata,
                              incremental=None)
stp.io.export_forecast_dataset(R_calc, exporter)
stp.io.close_forecast_file(exporter)
