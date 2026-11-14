"""Compare simulated supplier payment options in integer paise."""

from decimal import Decimal, ROUND_HALF_UP


def rounded(value):
    return int(Decimal(value).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def evaluate_options(total, discount_bps, cash, buffer, daily_cap, days,
                     finance_bps=2400, loan_bps=3000, request_loan=False):
    discount = rounded(Decimal(total) * discount_bps / 10_000)
    payable = total - discount
    available = max(0, cash - buffer)
    gap = max(0, payable - available)

    def cost(principal, rate):
        return rounded(Decimal(principal) * rate * (days + 1) / 7_300_000)

    def option(key, supplier, contribution=0, finance=0, loan=0, reason=None):
        fee = cost(finance, finance_bps) + cost(loan, loan_bps)
        installment, remainder = divmod(finance + loan + fee, days)
        return dict(id=key, supplier_payable=supplier, cash_contribution=contribution,
                    financing=finance, loan=loan, cost=fee, net_benefit=total-supplier-fee,
                    daily_repayment=installment+bool(remainder), tenor=days if finance or loan else 0,
                    schedule=[installment+int(day < remainder) for day in range(days)]
                    if finance or loan else [], feasible=reason is None, reason=reason)

    low, high = 0, gap
    while low < high:
        mid = (low + high + 1) // 2
        if mid + cost(mid, finance_bps) <= daily_cap * days:
            low = mid
        else:
            high = mid - 1

    early_reason = None if discount else "No confirmed early-payment discount."
    options = [
        option("USE_AVAILABLE_CASH", payable, payable,
               reason=early_reason or ("Cash is below the supplier payable." if gap else None)),
        option("FINANCE_FUNDING_GAP", payable, min(available, payable), gap,
               reason=early_reason or (
                   "Requires cash contribution and an affordable funding gap."
                   if not available or not gap or gap > low else
                   "Financing costs meet or exceed the discount." if cost(gap, finance_bps) >= discount else None)),
        option("KEEP_ORIGINAL_TERMS", total),
    ]
    if discount and gap > low and (available < payable or request_loan):
        options.append(option("USE_PAYTM_MERCHANT_LOAN", payable, min(available, payable),
                              low, gap-low, "Indicative only. Subject to lender eligibility and approval."))
    return options
