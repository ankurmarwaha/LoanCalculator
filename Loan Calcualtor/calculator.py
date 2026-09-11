"""Indicative, constant-rate principal and interest loan calculations."""
import math


def payment(principal, annual_rate, months):
    r = annual_rate / 1200
    return principal / months if r == 0 else principal * r / -math.expm1(-months * math.log1p(r))


def schedule(principal, annual_rate, monthly):
    rows = []
    balance = principal
    for month in range(1, 601):
        if balance < 0.000001:
            break
        interest = balance * annual_rate / 1200
        paid = min(monthly, balance + interest)
        if balance + interest - paid < 0.000001:
            paid = balance + interest
        if paid <= interest:
            raise ValueError('Payment must exceed monthly interest.')
        balance = max(0, balance + interest - paid)
        rows.append(dict(month=month, payment=paid, interest=interest, principal=paid-interest, balance=balance))
    if balance > .01:
        raise ValueError('Loan cannot be repaid within 50 years.')
    return rows


def calculate(data):
    def number(key, low, high):
        try:
            value = float(data[key])
        except (KeyError, TypeError, ValueError):
            raise ValueError(f'Enter a valid {key}.')
        if not math.isfinite(value) or not low <= value <= high:
            raise ValueError(f'{key} must be between {low:,} and {high:,}.')
        return value
    kind = data.get('kind', 'home')
    if kind not in ('home', 'commercial'):
        raise ValueError('Choose home or commercial.')
    value = number('property', 1, 100_000_000)
    deposit = number('deposit', 0, value)
    principal = value - deposit
    if principal <= 0:
        raise ValueError('Deposit must be less than the property value.')
    rate = number('rate', 0, 30)
    years = number('years', 1, 40)
    if not years.is_integer():
        raise ValueError('Term must be a whole number of years.')
    extra = number('extra', 0, 1_000_000)
    income = number('income', 0, 10_000_000)
    expenses = number('expenses', 0, 10_000_000)
    debts = number('debts', 0, 10_000_000)
    lvr_cap = number('lvrCap', 1, 100)
    buffer = 3 if kind == 'home' else number('buffer', 0, 15)
    dscr = 1 if kind == 'home' else number('dscr', 1, 5)
    available = max(0, income-expenses-debts) / dscr
    capacity = available / payment(1, rate+buffer, int(years*12))
    collateral_cap = value*lvr_cap/100
    eligible = min(capacity, collateral_cap)
    monthly = payment(principal, rate, int(years*12))
    base = schedule(principal, rate, monthly)
    accelerated = schedule(principal, rate, monthly+extra)
    interest = sum(row['interest'] for row in base)
    extra_interest = sum(row['interest'] for row in accelerated)
    return dict(principal=principal, monthly=monthly, lvr=principal/value*100,
                capacity=eligible, serviceability=capacity, collateralCap=collateral_cap,
                lendingPercent=eligible/value*100, shortfall=max(0, principal-eligible),
                assessmentRate=rate+buffer, totalInterest=interest, totalPaid=principal+interest,
                interestSaved=max(0, interest-extra_interest), monthsSaved=len(base)-len(accelerated),
                payoffMonths=len(accelerated), base=base, accelerated=accelerated)
