"""
Created on Tue Aug 20
@author: Isaac Sudweeks
"""
import numpy as np
import pandas as pd
import scipy as sp
import seaborn
from matplotlib import pyplot as plt
import plotly.graph_objects as go
import plotly.express as px


def interp(data, title, knottnum_x, knottnum_y, eps, save=True, VOCL=5, NOXl=100, OzoneL=20, val=0.05, yi=-1, ys=-1,
           xi=-1, xs=-1):
    # Reformatting the data so it is more usable
    font = {'size': 23}
    plt.rc('font', **font)
    plt.rc('axes', titlesize=23)
    x = data.VOC.astype(float)
    y = data.NOx.astype(float)
    z = data.Ozone.astype(float)

    # Setting up matplot lib to create graphs
    fig = plt.figure(figsize=(10, 8))
    ax = plt.axes(projection=None)

    # Create several variables used for plotting
    x_range = np.linspace(min(x), max(x), 1000)
    y_range = np.linspace(min(y), max(y), 1000)
    X, Y = np.meshgrid(x_range, y_range)

    # Create knott location as spaced in even quantiles
    numx = np.linspace(0, 1, knottnum_x + 1, endpoint=False)[1:]
    numy = np.linspace(0, 1, knottnum_y + 1, endpoint=False)[1:]
    tx = []
    ty = []
    for i in numx:
        tx.append(np.quantile(x, i, method='interpolated_inverted_cdf'))

    for j in numy:
        ty.append(np.quantile(y, j, method='interpolated_inverted_cdf'))

    # Create the spline
    spline = sp.interpolate.LSQBivariateSpline(x, y, z, tx, ty, bbox=[min(x), max(x), min(y), max(y)], eps=eps)

    Z = spline(x_range, y_range)
    Z = np.clip(Z, 0, OzoneL)
    levels = [i for i in range(0, OzoneL, 5)]
    levels.append(OzoneL)

    # Get rid of extrapolation
    if yi == -1 and ys == -1 and xi == -1 and xs == -1:
        remove_extrapolation = False
    else:
        remove_extrapolation = True
    if remove_extrapolation:
        for i in range(0, len(Z)):
            for j in range(0, len(Z[i])):
                if (Y[i, j] > ys * X[i, j] + yi):
                    Z[i, j] = -5
                elif (Y[i, j] < xs * X[i, j] - xs * xi):
                    Z[i, j] = -5

    cont = ax.contourf(X, Y, Z, cmap='turbo', vmin=0, vmax=OzoneL, levels=levels)
    cbar = fig.colorbar(cont, ax=ax, shrink=0.5, aspect=5, extend='both')
    cbar.set_label('Ozone (ppb)')  # The label for the color bar
    ax.collections[0].colorbar.ax.set_ylim(0, OzoneL)
    ax.set_xlabel('VOC (ppbC)')
    ax.set_xlim(min(x), VOCL)

    ax.set_ylabel('NO$_x$ (ppb)')
    ax.set_ylim(min(y), NOXl)

    # Create the KDE
    seaborn.kdeplot(data=data, x='VOC', y='NOx', ax=ax, fill=False, levels=1, thresh=val, color='black')

    # Scatter all the data points
    plt.scatter(x, y, marker='.', c='k')

    # Get the mean value
    NoxM = np.mean(y)
    VOCM = np.mean(x)
    print(f'[INFO] The mean value of NOX is {NoxM} and the mean value of VOC is {VOCM}')
    # Plot the mean value
    plt.plot(VOCM, NoxM, 'wX', markersize=20, markeredgewidth=3)


    if save:
        plt.savefig(f'plots/{title}_isopleth.png')
    # Create the 3d surface
    plt.show()
    fig = go.Figure(go.Surface(x=X, y=Y, z=Z))
    fig.update_layout(title=f"{title}",
                      scene=dict(
                          xaxis=dict(range=[0, max(x)], ),
                          yaxis=dict(range=[0, max(y)], ),
                          zaxis=dict(range=[0, max(z)], ),
                          xaxis_title='VOC (ppb)',
                          yaxis_title='Nox (ppb)',
                          zaxis_title='Ozone (ppb)'
                      ))
    fig2 = px.scatter_3d(data, x='VOC', y='NOx', z='Ozone')
    fig2.update_layout(title=f"{title}",
                       scene=dict(
                           xaxis=dict(range=[0, VOCL], ),
                           yaxis=dict(range=[0, NOXl], ),
                           zaxis=dict(range=[0, max(z)], ),
                           xaxis_title='VOC (ppb)',
                           yaxis_title='Nox (ppb)',
                           zaxis_title='Ozone (ppb)'
                       ))
    fig3 = go.Figure(data=fig.data + fig2.data)
    fig3.update_layout(title=f"{title}",
                       scene=dict(
                           xaxis=dict(range=[0, max(x)], ),
                           yaxis=dict(range=[0, max(y)], ),
                           zaxis=dict(range=[0, max(z)], ),
                           xaxis_title='VOC (ppb)',
                           yaxis_title='Nox (ppb)',
                           zaxis_title='Ozone (ppb)'
                       ))
    fig3.show()
    if save:
        fig.write_html(f'plots/{title}_Surface_Only.html')
        fig2.write_html(f'plots/{title}_DataPoints.html')
        fig3.write_html(f'plots/{title}_Surface_W_Scatter.html')

    return NoxM, VOCM


def build_isopleths(data, ky, kx, e, filename):
    title = input('What would you like the title/filename of the plot to be?')
    cont = True
    while cont:
        NOXl = float(input('What would you like the upper bound for NOx to be?'))
        VOCl = float(input('What would you like the upper bound for VOC to be?'))
        OzoneL = int(input('What would you like the upper bound for Ozone to be?'))
        yi = float(input('What would you like the Y intercept to be?'))
        ys = float(input('What would you like the Y slope to be'))
        xi = float(input('What would you like the X intercept to be?'))
        xs = float(input('What would you like the X slope to be?'))
        interp(data, title, kx, ky, e, save=False, NOXl=NOXl, VOCL=VOCl, OzoneL=OzoneL, val=0.05,
               xi=xi, yi=yi, ys=ys, xs=xs)
        if (input('Do all of the parameters look good?') == 'y'):
            cont = False
            print('[INFO] Saving isopleths...')
            NoxM, VOCM = interp(data, title, kx, ky, e, save=True, NOXl=NOXl, VOCL=VOCl, OzoneL=OzoneL, val=0.05,
                   xi=xi, yi=yi, ys=ys, xs=xs)
            d = {'Title': title, 'File Source': filename, 'KnotX': kx, 'Knoty': ky, 'Epsilon':e, 'NOX_Bound': NOXl, 'VOCL_Bound': VOCl, 'Ozone_Bound':OzoneL, 'X intercept':xi, 'Y intercept':yi, 'X slope':xs, 'Y slope':ys, 'NOX average' : NoxM, 'VOCM average' :VOCM}
            df = pd.DataFrame(data=d, index=[1])
            df.to_csv(f'plots/{title}_metadata.csv', index=False)
