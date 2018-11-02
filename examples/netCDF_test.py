import netCDF4 as cdf
import datetime as dt
import pyproj

def open_netcdf(filename, mode, format = "NETCDF4"):
    ncf = cdf.Dataset(filename, mode, format)
    return ncf

def get_data(ncf):
    data_var = "precip_probability"
    time_var = "fc_time"
    #startdate = dt.datetime.strptime(ncf[time_var].units, time_units_format)
    data = {}
    for i in range(ncf[data_var].shape[0]):
        datetime_str = int(ncf[time_var][i])
        data[datetime_str] = ncf[data_var][i]
    return data

def _get_prob(ncf, datetime_str, x, y): #по пикселям
    data = get_data(ncf)
    p = data[datetime_str][y][x]
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


filename = "/home/eugene/pysteps-data/out/probab_ensemble_nwc_201810270600.ncf"
ncf = open_netcdf(filename, 'r')
#xc = ncf.variables["xc"]
#print(xc[-1] - xc[0])
a = get_prob(ncf, 10, 51.92, 53.44)
print(a)
