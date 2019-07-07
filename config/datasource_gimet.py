# data source specifications
root_path  = "/home/eugene/pysteps-data"
path_fmt   = "radar/gimet/%Y%m%d"
fn_pattern = "bufr_dbz1_%Y%m%d_%H%M"
fn_ext     = "tiff"
importer   = "gimet_tiff"
timestep   = 10.

# importer arguments
importer_kwargs = {}