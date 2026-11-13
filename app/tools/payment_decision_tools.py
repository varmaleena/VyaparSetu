"""Compare full-bill funding routes and apply deterministic demo policy."""

from datetime import date

from app.models.decision import (
    Funding,
    PaymentDecision,
    PaymentEconomics,
    PaymentOption,
)
from app.models.invoice import ExtractedInvoice


def calculate_payment_economics(
    invoice: ExtractedInvoice,
    funding: Funding,
    daily_cap: int,
    as_of: date,
) -> PaymentEconomics:
    economics = PaymentEconomics(
        code="TERMS_UNCONFIRMED",
        due_date=invoice.due_date,
        invoice_total=invoice.total_paise,
        tenor_days=funding.offer.tenor_days if funding.offer else 0,
        offer=funding.offer,
        daily_cap=daily_cap,
        options=[PaymentOption(method="WAIT")],
    )
    terms = invoice.discount
    total = invoice.total_paise
    if invoice.discount_status == "none":
        economics.code = "NO_DISCOUNT"
        return economics
    if (
        invoice.discount_status != "offered"
        or total is None
        or terms is None
        or (
            terms.deadline is None
            or terms.requires_full_payment is None
            or (terms.amount_paise is None and terms.rate_bps is None)
        )
    ):
        return economics
    discount = terms.amount_paise or (total * (terms.rate_bps or 0) + 5000) // 10_000
    if not 0 < discount < total:
        return economics
    economics.discount = discount
    economics.discount_deadline = terms.deadline
    economics.early_amount = total - discount
    if terms.deadline < as_of:
        economics.code = "DISCOUNT_EXPIRED"
        return economics

    economics.code = "OPTIONS_COMPARED"
    amount = economics.early_amount
    cash = min(funding.cash, amount)
    gap = amount - cash
    if not gap:
        economics.options.append(
            PaymentOption(method="CASH", cash=cash, net_savings=discount)
        )
        return economics
    # Compare financing alone with drawing the available settlement tranche first.
    settlement_draw = min(funding.instant_net, gap)
    for net in dict.fromkeys((0, settlement_draw)):
        principal = max(0, gap - net)
        fee = funding.instant_fee if net else 0
        offer = funding.offer
        if principal and offer is None:
            continue
        repayment_cost = (
            (principal * offer.daily_rate_bps * offer.tenor_days + 5000) // 10_000
            + offer.fee_paise
            if principal and offer
            else 0
        )
        cost = fee + repayment_cost
        economics.options.append(
            PaymentOption(
                method="FINANCING" if principal else "INSTANT_SETTLEMENT",
                cash=cash,
                instant_net=net,
                principal=principal,
                cost=cost,
                repayment_total=principal + repayment_cost,
                daily_installment=(principal + repayment_cost + offer.tenor_days - 1)
                // offer.tenor_days
                if principal and offer
                else 0,
                net_savings=discount - cost,
            )
        )
    return economics


def apply_payment_policy(economics: PaymentEconomics) -> PaymentDecision:
    eligible = [
        option
        for option in economics.options
        if option.method != "WAIT"
        and option.net_savings > 0
        and option.daily_installment <= economics.daily_cap
    ]
    if eligible:
        best = max(eligible, key=lambda option: (option.net_savings, -option.principal))
        return PaymentDecision(
            status="FINANCING_FITS" if best.principal else "PAY_FROM_AVAILABLE_FUNDS",
            code="POSITIVE_NET_SAVINGS",
            selected=best,
            economics=economics,
        )
    code = economics.code
    if code == "OPTIONS_COMPARED" and len(economics.options) == 1:
        code = "NO_FUNDING_OPTION"
    if code == "OPTIONS_COMPARED":
        code = (
            "REPAYMENT_CAP_EXCEEDED"
            if any(option.net_savings > 0 for option in economics.options)
            else "NO_NET_SAVINGS"
        )
    return PaymentDecision(
        status="NEEDS_REVIEW" if code == "TERMS_UNCONFIRMED" else "WAIT",
        code=code,
        economics=economics,
    )
