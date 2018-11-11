import netCDF4 as cdf
import datetime as dt
import pyproj

def open_netcdf(filename, mode, format = "NETCDF4"):
    ncf = cdf.Dataset(filename, mode, format)
    return ncf

def get_data(ncf):
    data_var = "precip_probability"
    time_var = "fc_time"
    time_format = "%Y-%m-%d %H:%M:%S"
    startdate = dt.datetime.strptime(ncf.startdate_str, time_format)
    data = {}
    for i in range(ncf[data_var].shape[0]):
        min_passed = int(ncf.variables["fc_time"][i])
        datetime = startdate + dt.timedelta(minutes = min_passed)
        data[str(datetime)] = ncf[data_var][i]
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
    print (x,y)
    return int(x), int(y)


def get_prob(ncf, datetime_str, lat, lon): #по широте и долготе
    x,y = get_cords(ncf, lat, lon)
    return _get_prob(ncf, datetime_str, x, y)


filename = "/home/eugene/pysteps-data/out/probab_ensemble_nwc_201810270600.ncf"

ncf = open_netcdf(filename, 'r')
print(ncf.startdate_str)

a = get_prob(ncf, "201810270630", 50.5, 31.2)
print(a)
