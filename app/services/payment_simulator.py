"""Create a simulated receipt and an exact paise repayment schedule."""

from app.models.payment import PaymentProposal, SimulatedPayment


def simulate_payment(proposal: PaymentProposal) -> SimulatedPayment:
    option = proposal.option
    installments = []
    if option.principal:
        remaining = option.repayment_total
        for _ in range(proposal.tenor_days):
            installment = min(option.daily_installment, remaining)
            installments.append(installment)
            remaining -= installment
        if remaining or not installments or installments[-1] <= 0:
            raise ValueError("Invalid repayment schedule")
    return SimulatedPayment(
        proposal_id=proposal.id,
        status="SIMULATED_PAID",
        installments_paise=installments,
    )
