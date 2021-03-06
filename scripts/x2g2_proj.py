#!/usr/bin/env python3

import pickle

from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt
import numpy
from scipy import constants

from pysolidg2p import asymmetry, cross_section, sim_reader, structure_f

_alpha = constants.alpha
_m_p = constants.value('proton mass energy equivalent in MeV') * 1e-3
_inv_fm_to_gev = constants.hbar * constants.c / constants.e * 1e6
_inv_gev_to_fm = _inv_fm_to_gev
_inv_gev_to_mkb = _inv_gev_to_fm**2 * 1e4

e = 11
binning = {'bins': 20, 'range': (0.0, 1.0)}
yield_limit = 10000


def create_bins():
    bins = binning['bins']
    bin_low, bin_high = binning['range']
    bin_centers = numpy.linspace(bin_low + (bin_high - bin_low) / bins / 2, bin_high - (bin_high - bin_low) / bins / 2, bins)
    bin_edges = numpy.linspace(bin_low, bin_high, bins + 1)

    return bin_centers, bin_edges


x_raw, q2_raw, yield_raw = sim_reader.load('yield.txt')

q2_list = [2, 3, 4, 5, 6]
q2_edges = [1.5, 2.5, 3.5, 4.5, 5.5, 6.5]

result = {}

for i, _ in enumerate(q2_list):
    x, x_edges = create_bins()
    yield_ = numpy.zeros_like(x)

    for j, _ in enumerate(x):
        q2_x = q2_raw[(x_raw >= x_edges[j]) & (x_raw < x_edges[j + 1])]
        yield_x = yield_raw[(x_raw >= x_edges[j]) & (x_raw < x_edges[j + 1])]

        yield_[j] = numpy.sum(yield_x[(q2_x >= q2_edges[i]) & (q2_x < q2_edges[i + 1])])

    q2 = q2_list[i]
    ep_min = q2 / (4 * 11)
    x_min = q2 / (2 * _m_p * (e - ep_min))
    select = (x > x_min) & (yield_ > yield_limit)
    x = x[select]
    yield_ = yield_[select]

    asym = asymmetry.atp(e, x, q2)
    easym = 1 / numpy.sqrt(yield_)

    xs0 = cross_section.xsp(e, x, q2)
    exs0 = xs0 * (1 / numpy.sqrt(yield_))

    dxsT = 2 * xs0 * asym
    edxsT = dxsT * numpy.sqrt((easym / asym)**2 + (exs0 / xs0)**2)

    dxsL = cross_section.dxslp(e, x, q2)  # from model
    edxsL = 0

    nu = q2 / (2 * _m_p * x)
    ep = e - nu
    theta = 2 * numpy.arcsin(numpy.sqrt(q2 / (4 * e * ep)))
    sigma0 = 4 * _alpha**2 * ep / (nu * _m_p * q2 * e) * _inv_gev_to_mkb

    A1 = (e + ep * numpy.cos(theta))
    B1 = -2 * _m_p * x
    C1 = dxsL / sigma0
    A2 = ep * numpy.sin(theta)
    B2 = 2 * e * ep * numpy.sin(theta) / nu
    C2 = dxsT / sigma0
    D = A1 * B2 - A2 * B1
    #g1 = (C1 * B2 - C2 * B1) / D
    g2 = (-C1 * A2 + C2 * A1) / D

    eC1 = edxsL / sigma0
    eC2 = edxsT / sigma0
    eg1 = numpy.sqrt((eC1 * B2 / D)**2 + (eC2 * B1 / D)**2)
    eg2 = numpy.sqrt((eC1 * A2 / D)**2 + (eC2 * A1 / D)**2)

    sub_result = {}
    sub_result['x'] = x
    sub_result['q2'] = q2
    sub_result['g2'] = g2
    sub_result['eg2'] = eg2
    result[str(q2_list[i])] = sub_result

with open('g2.pkl', 'wb') as f:
    pickle.dump(result, f)

x_model = numpy.linspace(0, 1, 201)

with PdfPages('x2g2_proj.pdf') as pdf:
    plt.figure()
    ax = plt.gca()
    ax.axhline(y=0, linestyle='--', linewidth=0.75, color='k')
    plt.xlabel(r'$x$')
    plt.ylabel(r'$x^2g_2$')
    plt.xlim(0, 1)
    plt.ylim(-0.04, 0.01)
    l6, = plt.plot(x_model, x_model**2 * structure_f.g2p(x_model, 6), 'y-', linewidth=0.75)  # q2 = 6
    p6 = plt.errorbar(result['6']['x'], result['6']['x']**2 * result['6']['g2'], result['6']['x']**2 * result['6']['eg2'], fmt='y.')
    l5, = plt.plot(x_model, x_model**2 * structure_f.g2p(x_model, 5), 'b-', linewidth=0.75)  # q2 = 5
    p5 = plt.errorbar(result['5']['x'], result['5']['x']**2 * result['5']['g2'], result['5']['x']**2 * result['5']['eg2'], fmt='b.')
    l4, = plt.plot(x_model, x_model**2 * structure_f.g2p(x_model, 4), 'g-', linewidth=0.75)  # q2 = 4
    p4 = plt.errorbar(result['4']['x'], result['4']['x']**2 * result['4']['g2'], result['4']['x']**2 * result['4']['eg2'], fmt='g.')
    l3, = plt.plot(x_model, x_model**2 * structure_f.g2p(x_model, 3), 'r-', linewidth=0.75)  # q2 = 3
    p3 = plt.errorbar(result['3']['x'], result['3']['x']**2 * result['3']['g2'], result['3']['x']**2 * result['3']['eg2'], fmt='r.')
    l2, = plt.plot(x_model, x_model**2 * structure_f.g2p(x_model, 2), 'k-', linewidth=0.75)  # q2 = 2
    p2 = plt.errorbar(result['2']['x'], result['2']['x']**2 * result['2']['g2'], result['2']['x']**2 * result['2']['eg2'], fmt='k.')
    plt.legend([(p2, l2), (p3, l3), (p4, l4), (p5, l5), (p6, l6)],
               [r'$1.5<Q^2<2.5$', r'$2.5<Q^2<3.5$', r'$3.5<Q^2<4.5$', r'$4.5<Q^2<5.5$', r'$5.5<Q^2<6.5$'])
    pdf.savefig(bbox_inches='tight')
    plt.close()
