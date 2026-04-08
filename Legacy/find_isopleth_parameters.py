"""
Created on July 15 2024
@author: Isaac Sudweeks
"""
from multiprocessing import Pool

import pandas as pd
import scipy as sp
from sklearn.base import BaseEstimator
import numpy as np
from sklearn.model_selection import RepeatedKFold, cross_val_score
import build_isopleths


class spline(BaseEstimator):
    def __init__(self, knottCountx=2, knottCounty=2, epsilon=0.01):
        self.knottCountx = knottCountx
        self.knottCounty = knottCounty
        self.epsilon = epsilon

    def fit(self, X, y):
        """

        @param X:
        @param y:
        @return:
        """
        # Reformatting input data
        p1, p2 = np.hsplit(X, 2)
        p1 = p1.values
        p2 = p2.values
        p1 = p1.flatten()
        p2 = p2.flatten()

        # Set knotts
        numx = np.linspace(0, 1, self.knottCountx + 1, endpoint=False)[1:]
        numy = np.linspace(0, 1, self.knottCounty + 1, endpoint=False)[1:]
        tx = []
        ty = []
        for x in numx:
            tx.append(np.quantile(p1, x))
        for j in numy:
            ty.append(np.quantile(p2, j))

        # Create the model
        self.model = sp.interpolate.LSQBivariateSpline(p1, p2, y, tx, ty, bbox=[min(p1), max(p1), min(p2), max(p2)],
                                                       eps=self.epsilon)

        return self.model

    def predict(self, X):
        p1, p2 = np.hsplit(X, 2)
        p1 = p1.values
        p2 = p2.values
        return self.model.ev(p1, p2)


def kFCV(data, knottCountx, knottCounty, epsilon=0.01):
    X = data[['VOC', 'NOx']]
    y = data.Ozone

    # Do a 10-fold cross-validation on each of
    cv = RepeatedKFold(n_splits=10, random_state=1, n_repeats=3)

    # Create the model
    model = spline(knottCountx, knottCounty, epsilon)

    # Get a list of scores using the negative root mean squared error metric
    scores = cross_val_score(model, X, y, scoring='neg_root_mean_squared_error', cv=cv, n_jobs=-1)

    # Return the mean of those scores along with the number of knots used
    out = [np.mean(scores), knottCountx, knottCounty]
    return out


def parrellel(a):
    test = []
    for i in range(1, 3):  # Change this to however many you want as the max knott count I have found 11 works well
        for j in range(1, 3):
            test.append(kFCV(d, i, j, epsilon=a))
    x = []
    y = []
    z = []
    for i in range(len(test)):  # FIXME: This seems not efficient
        x.append(test[i][1])
        y.append(test[i][2])
        z.append(test[i][0])
    return [x[z.index(max(z))], y[z.index(max(z))], max(z), a]


def init_pool(filename):
    """
    This function is used to initialize the pool so that they all share the data
    @param filename:
    """
    global d
    d = pd.read_csv(filename)


def get_params(filename, num):
    data = pd.read_csv(filename)
    start = 0.99 * 10
    stop = 0.1 * 10
    cont = True
    while cont:
        start = start / 10
        stop = stop / 10
        with Pool(initializer=init_pool, initargs=(filename,)) as pool:
            tmp = pool.map(parrellel, np.linspace(start, stop, num))
        x = []
        y = []
        z = []
        a = []
        for i in range(len(tmp)):
            x.append(tmp[i][0])
            y.append(tmp[i][1])
            z.append(tmp[i][2])
            a.append(tmp[i][3])

        # The best combination found in the grid search
        e = a[z.index(max(z))]
        kx = x[z.index(max(z))]
        ky = y[z.index(max(z))]
        error = max(z)
        build_isopleths.interp(data,
                               f'epsilon is {e} kx: {kx} ky: {ky} and an error of {error}',
                               kx, ky, e,
                               save=False, NOXl=max(data['NOx']), VOCL=max(data['VOC']), OzoneL=100, val=0.05)
        if (input('Would you like to continue with a smaller epsilon? (y/n) ') != 'y'):
            cont = False
            if input('Would you like to save the most recent plot to a file? (y/n) ') == 'y':
                build_isopleths.build_isopleths(data,ky,kx,e)