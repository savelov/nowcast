import numpy as np
import pysteps as stp


def nowcast_probability(n_time_step, shape, R_fct):
    prob = np.zeros((n_time_step, shape[0], shape[1]))
    for i in range(n_time_step):
        prob[i, :, :] = stp.postprocessing.ensemblestats.excprob(R_fct[:, i, :, :], 0.1, ignore_nan=True)
    return prob
