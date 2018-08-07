#!/usr/bin/env python
#
# Compute and plot marginal tax rates (regular and LT capital gains) for a
# married couple filing a joint return. We assume:
#  - No children
#  - Income comes entirely from wages
#  - Each spouse earns exactly half the wages
#  - State tax is paid at a rate of 9% on the income
#
# The payroll tax (social security and medicare) is not included in
# the computed marginal rates although we do include the "Additional
# Medicare Tax" in these rates.

import copy
from f1040 import F1040
from form import FilingStatus
import matplotlib.pyplot as plt
from matplotlib import cm
import numpy as np
import sys
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.ticker import LinearLocator, FormatStrFormatter
from matplotlib.widgets import Slider

template = {
    'status': FilingStatus.JOINT,
    'exemptions': 2,
    'disable_rounding': True,
}

SOCIAL_SECURITY_MAX = 117000
MEDICARE_RATE = .0145

def compute_with_income(template,
        incomes=[0,0],
        capital_gains=0,
        re_tax=0,
        mortgage_interest=0,
        amt_basis_adj=0):
    inputs = copy.deepcopy(template)
    inputs['real_estate_taxes'] = re_tax
    inputs['wages']          = incomes
    inputs['wages_medicare'] = incomes
    inputs['medicare_withheld'] = [incomes[0] * MEDICARE_RATE,
                                   incomes[1] * MEDICARE_RATE]
    ss = [min(SOCIAL_SECURITY_MAX, income) for income in incomes]
    inputs['wages_ss'] = ss
    inputs['state_withholding'] = (sum(incomes) + capital_gains) * .10
    inputs['capital_gain_long'] = capital_gains
    inputs['amt_basis_adjustment'] = amt_basis_adj
    inputs['F1040sa'] =  {
                         '10' : mortgage_interest, # mortgage interest deduction
                         }
    return F1040(inputs)

DELTA = 10

"""
Split total income across two spouses
Doesn't seem to make any difference.
"""
def calc_spouse_split(total_income, ratio=0.5):
    return [total_income * ratio, total_income * (1 - ratio)]

@np.vectorize
def calc_rates(income,
               re_tax=0,
               ltcg=0,
               amt_basis_adj = 0,
               mortgage_interest = 0,
               rate='MARGINAL',
               spouse_ratio=0.5):
    spouse_income = calc_spouse_split(income, ratio=spouse_ratio)
    base_args = dict(incomes=spouse_income,
                     capital_gains=ltcg,
                     amt_basis_adj=amt_basis_adj,
                     mortgage_interest=mortgage_interest,
                     re_tax=re_tax)
    fbase = compute_with_income(template, **base_args)
    next_args = base_args.copy()
    if rate == 'LTCG_MARGINAL':
        next_args['capital_gains'] += DELTA
        fnext = compute_with_income(template, **next_args)
        return float(fnext['63'] - fbase['63']) / DELTA
    elif rate == 'INT_DEDUCTION_MARGINAL':
        next_args['mortgage_interest'] += DELTA
        fnext = compute_with_income(template, **next_args)
        return float(fnext['63'] - fbase['63']) / DELTA
    elif rate == 'RE_DEDUCTION_MARGINAL':
        next_args['re_tax'] += DELTA
        fnext = compute_with_income(template, **next_args)
        return float(fnext['63'] - fbase['63']) / DELTA
    elif rate == 'MARGINAL':
        next_args['incomes'] = calc_spouse_split(income + DELTA, ratio=spouse_ratio)
        fnext = compute_with_income(template, **next_args)
        fnext = compute_with_income(template, **next_args)
        return float(fnext['63'] - fbase['63']) / DELTA
    elif rate == 'EFFECTIVE':
        return fbase['63'] / (income + ltcg)
    elif rate == 'TOTAL':
        return fbase['63']

MIN_RE_TAX = 0
MAX_RE_TAX = 2500000 * 0.015
MIN_LTCG = 0
MAX_LTCG = 1000000
MIN_WAGES = 10000
MAX_WAGES = 1000000
MAX_MORTGAGE_INTEREST = 100000
WAGES_STEP = 10000
incomes = np.arange(MIN_WAGES, MAX_WAGES, WAGES_STEP)

fig = plt.figure()
ax_marginal = plt.axes([0.1, 0.65, 0.85, 0.3])
plt.xlabel('Wages')
plt.ylabel('Marginal Rate')
plt.legend(loc=4)
p_ltcg, = plt.plot(incomes, incomes, label="LTCG Marginal")
p_wages, = plt.plot(incomes, incomes, label="W2 Marginal")
p_deduct, = plt.plot(incomes, incomes, label="Local tax marginal Deduction")
p_int_deduct, = plt.plot(incomes, incomes, label="Mortgage marginal Deduction")
plt.grid(True)
ax_marginal.set_ylim([-0.6, 0.60])
ax_marginal.legend()

ax_effective = plt.axes([0.1, 0.25, 0.85, 0.3])
plt.xlabel('Wages')
plt.ylabel('Effective rate tax')
plt.legend(loc=4)
p_effective, = plt.plot(incomes, incomes, label='Total')
plt.grid(True)
ax_effective.set_ylim([0.15, 0.35])

ax_re_tax = plt.axes([0.15, 0.05, 0.75, 0.03], facecolor="lightgoldenrodyellow")
re_tax_slider = Slider(ax_re_tax, 'Prop tax', MIN_RE_TAX, MAX_RE_TAX, valinit=MIN_RE_TAX, valfmt="%d")

ax_ltcg = plt.axes([0.15, 0.1, 0.75, 0.03], facecolor="lightgoldenrodyellow")
ltcg_slider = Slider(ax_ltcg, 'LTCG', MIN_LTCG, MAX_LTCG, valinit=0, valfmt="%d")

ax_amt_basis_adj = plt.axes([0.15, 0.15, 0.75, 0.03], facecolor="lightgoldenrodyellow")
amt_basis_adj_slider = Slider(ax_amt_basis_adj, 'AMT Basis Adj', -MAX_LTCG, MAX_LTCG, valinit=0, valfmt="%d")

ax_mortgage_interest = plt.axes([0.15, 0.2, 0.75, 0.03], facecolor="lightgoldenrodyellow")
mortgage_interest_slider = Slider(ax_mortgage_interest, 'Mtg int', 0, MAX_MORTGAGE_INTEREST, valinit=0, valfmt="%d")

def update(unused=None):
    inputs = dict(
        re_tax = re_tax_slider.val,
        mortgage_interest = mortgage_interest_slider.val,
        amt_basis_adj = amt_basis_adj_slider.val,
        ltcg = ltcg_slider.val)
    p_ltcg.set_ydata(calc_rates(incomes, rate='LTCG_MARGINAL', **inputs))
    p_wages.set_ydata(calc_rates(incomes, rate='MARGINAL', **inputs))
    p_effective.set_ydata(calc_rates(incomes, rate='EFFECTIVE', **inputs))
    p_deduct.set_ydata(calc_rates(incomes, rate='RE_DEDUCTION_MARGINAL', **inputs))
    p_int_deduct.set_ydata(calc_rates(incomes, rate='INT_DEDUCTION_MARGINAL', **inputs))
    fig.canvas.draw_idle()

re_tax_slider.on_changed(update)
ltcg_slider.on_changed(update)
amt_basis_adj_slider.on_changed(update)
mortgage_interest_slider.on_changed(update)
update()
plt.show()
