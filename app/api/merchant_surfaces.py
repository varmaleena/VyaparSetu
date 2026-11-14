"""Run-scoped A2UI surfaces and workflow relationships."""

from typing import Any

import networkx as nx  # type: ignore[import-untyped]

CATALOG = "https://a2ui.org/specification/v1_0/catalogs/basic/catalog.json"


def money(value: int | None) -> str:
    if value is None:
        return "Unavailable"
    whole, remainder = divmod(abs(value), 100)
    return f"{'-' if value < 0 else ''}₹{whole:,}.{remainder:02d}"


def surface(name: str, rows: list[tuple[str, str]]) -> dict:
    components: list[dict[str, Any]] = [
        {
            "id": "root",
            "component": "Column",
            "children": [f"row-{i}" for i in range(len(rows))],
        }
    ]
    for i, (label, value) in enumerate(rows):
        components.extend(
            [
                {
                    "id": f"row-{i}",
                    "component": "Row",
                    "children": [f"label-{i}", f"value-{i}"],
                },
                {"id": f"label-{i}", "component": "Text", "text": label},
                {"id": f"value-{i}", "component": "Text", "text": value},
            ]
        )
    return {
        "version": "v1.0",
        "createSurface": {
            "surfaceId": name,
            "catalogId": CATALOG,
            "components": components,
        },
    }


def present(state: dict) -> dict:
    decision = state.get("payment_decision") or {}
    economics = decision.get("economics") or {}
    option = decision.get("selected") or {}
    monitoring = state.get("repayment_monitoring") or {}
    proposal = (state.get("payment_proposal") or {}).get("terms")
    receipt = state.get("simulated_payment_receipt")
    decision_rows = [
        (
            "Recommendation",
            {
                "FINANCING_FITS": "Pay early with financing",
                "PAY_FROM_AVAILABLE_FUNDS": "Pay early from available funds",
                "WAIT": "Wait",
                "NEEDS_REVIEW": "Needs review",
            }.get(decision.get("status", ""), "Awaiting comparison"),
        )
    ]
    reasons = {
        "NO_DISCOUNT": "The invoice has no confirmed early-payment discount.",
        "DISCOUNT_EXPIRED": "The supplier's discount deadline has passed.",
        "NO_POSITIVE_SAVINGS": "The available options do not leave positive net savings.",
        "TERMS_UNCONFIRMED": "The early-payment terms need confirmation.",
    }
    reason = reasons.get(economics.get("code", "")) or reasons.get(
        decision.get("code", "")
    )
    if reason:
        decision_rows.append(("Reason", reason))
    if economics:
        decision_rows.append(("Invoice total", money(economics.get("invoice_total"))))
        if economics.get("discount_deadline"):
            decision_rows.extend(
                [
                    ("Discount deadline", economics["discount_deadline"]),
                    ("Gross discount", money(economics.get("discount"))),
                ]
            )
        if economics.get("due_date"):
            decision_rows.append(("Normal due date", economics["due_date"]))
    if option:
        decision_rows.extend(
            [
                ("Early payment amount", money(economics.get("early_amount"))),
                ("Funding cost", money(option["cost"])),
                ("Estimated net savings", money(option["net_savings"])),
            ]
        )
    repayment_rows = [
        (
            "Projection",
            {
                "ON_TRACK": "On track",
                "PROJECTED_SHORTFALL": "Projected shortfall",
                "UNKNOWN": "Coverage unknown",
                "NO_INSTALLMENTS": "No financing installments",
            }.get(monitoring.get("status", ""), "Awaiting repayment check"),
        )
    ]
    for key, label in [
        ("next_paise", "Next installment"),
        ("upcoming_paise", "Upcoming scheduled total"),
        ("projected_shortfall_paise", "Projected shortfall"),
    ]:
        if key in monitoring:
            repayment_rows.append((label, money(monitoring[key])))
    if monitoring.get("next_date"):
        repayment_rows.append(("Next due date", monitoring["next_date"]))
    if receipt and receipt["installments_paise"]:
        repayment_rows.append(("Actual collections", "Unknown in simulation"))

    invoice = state.get("invoice_structured")
    supplier = state.get("supplier_verification_result")
    graph = nx.DiGraph()
    for key, node_label in (
        ("invoice", invoice and invoice.get("invoice_number")),
        ("supplier", supplier and supplier.get("supplier_name")),
        ("proposal", proposal and proposal["id"]),
        ("receipt", receipt and receipt["proposal_id"]),
        (
            "schedule",
            receipt and receipt["installments_paise"] and "Scheduled installments",
        ),
    ):
        if node_label:
            graph.add_node(key, label=node_label)
    for source, target, relation in (
        ("invoice", "supplier", "Issued by"),
        ("invoice", "proposal", "Evaluated as"),
        ("proposal", "receipt", "Confirmed as"),
        ("receipt", "schedule", "Schedules"),
    ):
        if source in graph and target in graph:
            graph.add_edge(source, target, label=relation)

    return {
        "invoice": invoice,
        "supplier": supplier,
        "intake_id": (state.get("invoice_intake_result") or {}).get("intake_id"),
        "checks": [
            state.get(key)
            for key in ("duplicate_check_result", "pricing_anomaly_result")
        ],
        "decision_status": decision.get("status"),
        "proposal": proposal,
        "receipt": receipt,
        "repayment_checked": bool(monitoring),
        "offer_available": economics.get("code") == "NO_DISCOUNT" and not proposal,
        "decision": surface("decision", decision_rows),
        "repayment": surface("repayment", repayment_rows),
        "graph": {
            "nodes": [{"id": key, **data} for key, data in graph.nodes(data=True)],
            "edges": [
                {"source": source, "target": target, **data}
                for source, target, data in graph.edges(data=True)
            ],
        },
    }
