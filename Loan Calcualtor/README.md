# Loanleaf

Australian home and commercial loan planning website. Python 3.12+, no package installation required.

Run `python server.py`, then open http://localhost:8000. Run checks with `python -m unittest -v`.

Includes monthly principal-and-interest payments, indicative borrowing capacity, adjustable LVR, commercial cash-flow coverage, extra-payment savings, balance charts and downloadable amortisation schedules. Inputs are processed in memory and not persisted or sent to banks.

Public bank connectors retrieve CommBank and Westpac product reference data, preserve conditions/tiers and fees, and cache complete responses for 15 minutes. Bank outages are shown explicitly; illustrative rates never masquerade as live quotes. Products are not automatically matched or ranked: users must check all conditions before applying a rate. Business feeds may not contain commercial property quotes. LVR is a user-controlled modelling assumption, not a bank-sourced eligibility limit.

## Calculation assumptions

Monthly rate = annual nominal rate / 12. Repayment = P*r/(1-(1+r)^(-n)); zero interest uses P/n. Extra contributions begin with the first payment and the final payment is capped. Unrounded intermediate balances are used. Lender daily accrual, rounding, variable rates, interest-only periods, fixed-rate expiry, fees, stamp duty, LMI and offsets are not modelled.

Home capacity is the lesser of the selected collateral limit and the present value of monthly after-tax surplus at the entered rate + 3 percentage points. Commercial capacity divides surplus by the selected coverage ratio before discounting at the entered rate plus the selected buffer. Defaults are illustrative, not lender policies. Dependants and obligations must be reflected in entered expenses; credit files, verified expense benchmarks and underwriting are not assessed.

No 95% accuracy claim is made. Establishing that target requires a defined error metric, consented lender quotes/decisions, representative validation data, product-specific fee/accrual modelling and lender underwriting integrations.

## Sources

- APRA assessment buffer: https://www.apra.gov.au/standards/aps-220
- CommBank API: https://www.commbank.com.au/developer/documentation/Products
- Westpac API: https://www.westpac.com.au/about-westpac/innovation/open-banking/product-api/

## Hosting

This is a local working prototype. `HOST` and `PORT` environment variables configure binding. Before public deployment use a production HTTP server/reverse proxy with HTTPS, request limits and monitoring, and validate lender matching/financial assumptions. No public deployment is included. Public API calls require outbound HTTPS. Google Fonts is optional; system fonts are used if unavailable.
