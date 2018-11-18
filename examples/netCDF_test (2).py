import netCDF4 as cdf
import datetime as dt
from glob import glob
from collections import OrderedDict
import pyproj

ncf_time_format = "%Y-%m-%d %H:%M:%S"

def open_netcdf(filename, mode, format = "NETCDF4"):
    ncf = cdf.Dataset(filename, mode, format)
    return ncf

def get_data(ncf, timeformat = ncf_time_format):
    data_var = "precip_probability"
    time_var = "time"
    #time_format = "%Y-%m-%d %H:%M:%S"
    startdate = dt.datetime.strptime(ncf.startdate_str, ncf_time_format)
    data = OrderedDict()
    for i in range(ncf[data_var].shape[0]):
        min_passed = int(ncf.variables["fc_time"][i])
        datetime = startdate + dt.timedelta(minutes = min_passed)
        data[dt.datetime.strftime(datetime, timeformat)] = ncf[data_var][i]
    return data

def _get_prob(ncf, datetime_str, x, y): #по пикселям

    data = get_data(ncf)
    datetime = dt.datetime.strptime(datetime_str,"%Y%m%d%H%M")
    p = data[str(datetime)][y][x]
    return p

def get_cords(ncf, lat, lon):
    pr = pyproj.Proj(ncf.projection)
    X, Y = pr(lon, lat)
    step = ncf.variables["xc"][1]- ncf.variables["xc"][0]
    x = (X - ncf.variables["xc"][0]) / step
    y = (Y - ncf.variables["yc"][0]) / step
    return int(x), int(y)


def get_prob(ncf, datetime_str, lat, lon): #по широте и долготе
    x,y = get_cords(ncf, lat, lon)
    return _get_prob(ncf, datetime_str, x, y)

def get_prob_arr(ncf, starttime_str, endtime_str, lat, lon):
    start = dt.datetime.strptime(starttime_str,"%Y%m%d%H%M")
    end = dt.datetime.strptime(endtime_str,"%Y%m%d%H%M")

    data = get_data(ncf)

    timelist = list(map(lambda x: dt.datetime.strptime(x, ncf_time_format), [i for i in data]))
    timelist = list(map(str, filter(lambda x: start <= x and x <= end, timelist)))

    x, y = get_cords(ncf, lat, lon)

    P = [data[time][y][x] for time in timelist]
    return P

def get_prob_dict(out_dir, lat, lon):
    filename = sorted(glob(out_dir + "/probab_ensemble_nwc_*.ncf"))[-1]
    timeformat = "%Y-%m-%dT%H:%M:%SZ"
    ncf = open_netcdf(filename, 'r')
    data = get_data(ncf, timeformat=timeformat)
    timelist = list(map(lambda x: dt.datetime.strptime(x, timeformat), [i for i in data]))

    datetime_now = dt.datetime.utcnow()
    timelist = list(filter(lambda x: datetime_now <= x and x <= datetime_now + dt.timedelta(minutes=120), timelist))

    x,y = get_cords(ncf, lat, lon)
    P = OrderedDict()
    for time in timelist:
        time_str = dt.datetime.strftime(time, timeformat)
        P[time_str] = data[time_str][y][x]
    return P

#filename = "/home/mikhailsavelov/pysteps-data/out/probab_ensemble_nwc_201810271000.ncf"

#ncf = open_netcdf(filename, 'r')
#print(ncf.startdate_str)

#a = get_prob(ncf, "201810271030", 51.92, 53.44)
P = get_prob_dict("/home/ubuntu/pysteps-data/out", 50.9203, 31.1968)
print(P)
