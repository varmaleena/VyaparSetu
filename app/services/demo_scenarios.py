"""Pre-staged enterprise hackathon demo scenarios for VyaparSetu."""

from __future__ import annotations

import hashlib
from typing import Any

from app.services.live_settlement_stream import LiveSettlementEngine
from app.services.tamper_evident_ledger import TamperEvidentLedger
from app.services.voice_soundbox_service import generate_voice_script


def build_scenario_data(scenario_key: str) -> dict[str, Any]:
    ledger = TamperEvidentLedger.get_instance()
    settlement_engine = LiveSettlementEngine.get_instance()

    session_id = f"SES_DEMO_{scenario_key.upper()}"
    ledger.reset_session(session_id)

    if scenario_key == "clean_bill_approve_full":
        # Scenario 1: The Star Pitch Demo
        # ₹40,000 invoice, 3% early cash discount = ₹1,200 savings
        # Strong merchant (P20 = ₹18,500/day, existing EDI = ₹500/day)
        # Safe EDI cap = 18,500 * 0.25 - 500 = ₹4,125/day. EDI required = ₹1,953/day. Covers easily!
        inv_amt = 40000
        disc_pct = 3.0
        disc_val = 1200
        pay_amt = 38800
        tenor_days = 20
        interest = 268  # 24% p.a. on declining balance
        net_benefit = 932
        daily_edi = 1953
        supplier_name = "Sri Balaji Distributors"
        gstin = "36AAAAA0000A1Z3"
        account_last4 = "4201"

        decision_id = f"DEC_{session_id}"
        voice_scripts = {
            "te": generate_voice_script(
                decision_id,
                supplier_name,
                inv_amt,
                pay_amt,
                disc_pct,
                disc_val,
                tenor_days,
                daily_edi,
                interest,
                net_benefit,
                "te",
            ),
            "hi": generate_voice_script(
                decision_id,
                supplier_name,
                inv_amt,
                pay_amt,
                disc_pct,
                disc_val,
                tenor_days,
                daily_edi,
                interest,
                net_benefit,
                "hi",
            ),
            "en": generate_voice_script(
                decision_id,
                supplier_name,
                inv_amt,
                pay_amt,
                disc_pct,
                disc_val,
                tenor_days,
                daily_edi,
                interest,
                net_benefit,
                "en",
            ),
        }

        # Initialize audit events
        ledger.append(
            session_id,
            "InvoiceIntakeAgent",
            "INTAKE_ACCEPTED",
            {
                "image": "bill_40k_balaji.jpg",
                "quality_score": 0.96,
                "timestamp": "2026-11-12T10:00:00Z",
            },
        )
        ledger.append(
            session_id,
            "InvoiceUnderstandingAgent",
            "GEMINI_VISION_EXTRACTED",
            {
                "supplier": supplier_name,
                "gstin": gstin,
                "amount": inv_amt,
                "discount_pct": disc_pct,
                "overall_confidence": 0.95,
            },
        )
        ledger.append(
            session_id,
            "ParallelRiskChecks",
            "RISK_VERIFIED_PASS",
            {
                "gstin_checksum": "VALID",
                "bank_account_match": "MATCHED",
                "fingerprint_duplicate": "NONE",
                "price_z_score": 0.12,
            },
        )
        ledger.append(
            session_id,
            "CashflowAffordabilityAgent",
            "P20_FORECAST_EVALUATED",
            {
                "history_days": 90,
                "p50_daily": 25000,
                "p20_daily": 18500,
                "existing_edi": 500,
                "safe_edi_cap": 4125,
            },
        )
        ledger.append(
            session_id,
            "PolicyDecisionAgent",
            "DECISION_RECORDED",
            {
                "decision": "APPROVE_FULL",
                "approved_amount": pay_amt,
                "daily_edi": daily_edi,
                "tenor": tenor_days,
                "net_benefit": net_benefit,
            },
        )

        settlement_engine.initialize_stream(
            session_id, pay_amt, daily_edi, tenor_days, base_daily_inflow=25000
        )

        return {
            "scenario_key": scenario_key,
            "title": "Clean Bill - Full Approval (Star Pitch)",
            "description": "₹40,000 supplier bill with 3% cash discount. P20 QR collections support full financing. ₹932 net profit saved for merchant.",
            "merchant_profile": {
                "name": "Sri Ravi Kirana Store",
                "city": "Hyderabad",
                "daily_avg_qr": "₹25,000",
                "existing_edi": "₹500 / day",
                "risk_tier": "LOW",
            },
            "invoice": {
                "number": "INV-2026-8812",
                "supplier_name": supplier_name,
                "supplier_gstin": gstin,
                "payout_account": f"HDFC Bank (•••• {account_last4})",
                "total_amount": inv_amt,
                "cash_discount_percent": disc_pct,
                "cash_discount_val": disc_val,
                "due_date": "2026-11-27",
                "discount_valid_until": "Today (Immediate)",
                "line_items": [
                    {"name": "Fortune Sunflower Oil 1L x 40", "amount": 16000},
                    {"name": "India Gate Basmati Rice 25kg x 4", "amount": 14000},
                    {"name": "Tata Salt 1kg x 50 & Spices", "amount": 10000},
                ],
                "confidence": {
                    "overall": 0.95,
                    "amount": 0.98,
                    "gstin": 0.94,
                    "discount": 0.93,
                },
            },
            "pipeline_stages": [
                {
                    "name": "Image Intake & Decryption",
                    "status": "COMPLETED",
                    "latency": "0.38s",
                    "badge": "200 OK",
                },
                {
                    "name": "Gemini 2.5 Vision Extraction",
                    "status": "COMPLETED",
                    "latency": "1.42s",
                    "badge": "95% Confidence",
                },
                {
                    "name": "Parallel Risk Checks (GSTIN, Dup, Price)",
                    "status": "COMPLETED",
                    "latency": "0.19s",
                    "badge": "All Passed",
                },
                {
                    "name": "P20 Quantile Cashflow Forecast",
                    "status": "COMPLETED",
                    "latency": "0.31s",
                    "badge": "P20: ₹18.5k/day",
                },
                {
                    "name": "Discount Arbitrage Engine",
                    "status": "COMPLETED",
                    "latency": "0.08s",
                    "badge": "Net: +₹932",
                },
                {
                    "name": "Deterministic Policy Rules",
                    "status": "COMPLETED",
                    "latency": "0.12s",
                    "badge": "APPROVE_FULL",
                },
            ],
            "decision": {
                "status": "APPROVE_FULL",
                "verdict_title": "Fully Approved for Purpose-Bound Supplier Payment",
                "approved_amount": pay_amt,
                "original_invoice": inv_amt,
                "discount_saving": disc_val,
                "financing_cost": interest,
                "net_benefit": net_benefit,
                "tenor_days": tenor_days,
                "daily_edi": daily_edi,
                "apr_percent": 24.0,
                "safe_edi_cap": 4125,
                "supplier_verified": True,
                "reasons": [
                    "SUPPLIER_VERIFIED_ACTIVE",
                    "GSTIN_CHECKSUM_VALID",
                    "ARBITRAGE_NET_PROFIT_POSITIVE",
                    "P20_CASHFLOW_COVERS_DAILY_EDI",
                ],
                "why_not": "Full amount covered. Maximum safe exposure for this merchant is up to ₹82,500.",
                "merchant_explanation": "Mee QR collections stable ga unnai. Full ₹38,800 supplier ki pay chesi ₹932 net benefit pondandi.",
            },
            "forecast_chart": {
                "p50_daily": 25000,
                "p20_daily": 18500,
                "safe_edi_cap": 4125,
                "daily_edi_proposed": daily_edi,
                "existing_edi": 500,
                "tenor_days": tenor_days,
            },
            "voice_scripts": {
                k: {
                    "script": v.script,
                    "language": v.language,
                    "decision_hash": v.decision_hash,
                }
                for k, v in voice_scripts.items()
            },
            "repayment": settlement_engine.get_current_status(session_id),
            "ledger": ledger.get_events(session_id),
        }

    elif scenario_key == "weaker_merchant_partial":
        # Scenario 2: Conservative Sizing / Partial Funding
        # Kirana with lower QR collections (P20 = ₹6,000/day, existing EDI = ₹500/day)
        # Safe EDI cap = 6,000 * 0.25 - 500 = ₹1,000/day.
        # Max safe repayable over 20 days = 20 * 1,000 = ₹20,000. Approved: ₹19,800.
        inv_amt = 40000
        disc_pct = 3.0
        approved_amt = 19800
        remaining_cash = 20200
        disc_val = 1200
        tenor_days = 20
        interest = 137
        net_benefit = 457
        daily_edi = 997
        supplier_name = "Sri Balaji Distributors"
        gstin = "36AAAAA0000A1Z3"

        decision_id = f"DEC_{session_id}"
        voice_scripts = {
            "te": generate_voice_script(
                decision_id,
                supplier_name,
                inv_amt,
                approved_amt,
                disc_pct,
                disc_val,
                tenor_days,
                daily_edi,
                interest,
                net_benefit,
                "te",
            ),
            "hi": generate_voice_script(
                decision_id,
                supplier_name,
                inv_amt,
                approved_amt,
                disc_pct,
                disc_val,
                tenor_days,
                daily_edi,
                interest,
                net_benefit,
                "hi",
            ),
            "en": generate_voice_script(
                decision_id,
                supplier_name,
                inv_amt,
                approved_amt,
                disc_pct,
                disc_val,
                tenor_days,
                daily_edi,
                interest,
                net_benefit,
                "en",
            ),
        }

        ledger.append(
            session_id,
            "InvoiceUnderstandingAgent",
            "GEMINI_VISION_EXTRACTED",
            {"amount": inv_amt, "supplier": supplier_name},
        )
        ledger.append(
            session_id,
            "CashflowAffordabilityAgent",
            "P20_CONSERVATIVE_CAP_HIT",
            {
                "p20_daily": 6000,
                "existing_edi": 500,
                "safe_edi_cap": 1000,
                "max_safe_principal": 19800,
            },
        )
        ledger.append(
            session_id,
            "PolicyDecisionAgent",
            "DECISION_RECORDED",
            {
                "decision": "APPROVE_PARTIAL",
                "approved_amount": approved_amt,
                "daily_edi": daily_edi,
            },
        )

        settlement_engine.initialize_stream(
            session_id, approved_amt, daily_edi, tenor_days, base_daily_inflow=8000
        )

        return {
            "scenario_key": scenario_key,
            "title": "Conservative Sizing - Partial Funding",
            "description": "Merchant collections cannot safely support ₹40,000. System conservatively sizes safe financing at ₹19,800; remaining ₹20,200 from cash.",
            "merchant_profile": {
                "name": "Lakshmi General Store",
                "city": "Secunderabad",
                "daily_avg_qr": "₹8,000",
                "existing_edi": "₹500 / day",
                "risk_tier": "MEDIUM",
            },
            "invoice": {
                "number": "INV-2026-8812",
                "supplier_name": supplier_name,
                "supplier_gstin": gstin,
                "payout_account": "HDFC Bank (•••• 4201)",
                "total_amount": inv_amt,
                "cash_discount_percent": disc_pct,
                "cash_discount_val": disc_val,
                "due_date": "2026-11-27",
                "discount_valid_until": "Today (Immediate)",
                "line_items": [
                    {"name": "Mixed Grocery & FMCG Supplies", "amount": 40000}
                ],
                "confidence": {
                    "overall": 0.94,
                    "amount": 0.98,
                    "gstin": 0.94,
                    "discount": 0.91,
                },
            },
            "pipeline_stages": [
                {
                    "name": "Image Intake & Decryption",
                    "status": "COMPLETED",
                    "latency": "0.35s",
                    "badge": "200 OK",
                },
                {
                    "name": "Gemini 2.5 Vision Extraction",
                    "status": "COMPLETED",
                    "latency": "1.38s",
                    "badge": "94% Confidence",
                },
                {
                    "name": "Parallel Risk Checks (GSTIN, Dup, Price)",
                    "status": "COMPLETED",
                    "latency": "0.18s",
                    "badge": "Passed",
                },
                {
                    "name": "P20 Quantile Cashflow Forecast",
                    "status": "COMPLETED",
                    "latency": "0.33s",
                    "badge": "P20: ₹6.0k/day",
                },
                {
                    "name": "Deterministic Policy Rules",
                    "status": "COMPLETED",
                    "latency": "0.14s",
                    "badge": "APPROVE_PARTIAL",
                },
            ],
            "decision": {
                "status": "APPROVE_PARTIAL",
                "verdict_title": "Partially Approved - Conservative Cashflow Safety Guard",
                "approved_amount": approved_amt,
                "remaining_cash_needed": remaining_cash,
                "original_invoice": inv_amt,
                "discount_saving": disc_val,
                "financing_cost": interest,
                "net_benefit": net_benefit,
                "tenor_days": tenor_days,
                "daily_edi": daily_edi,
                "apr_percent": 24.0,
                "safe_edi_cap": 1000,
                "supplier_verified": True,
                "reasons": [
                    "P20_FORECAST_BELOW_FULL_INVOICE_REQUIREMENT",
                    "SAFE_EDI_CAP_APPLIED (₹1,000/day limit)",
                    "ARBITRAGE_NET_PROFIT_POSITIVE",
                ],
                "why_not": "Full ₹40,000 approval requires at least ₹16,700/day P20 inflow (currently ₹6,000/day). ₹19,800 is the safe maximum that eliminates merchant default risk.",
                "merchant_explanation": "Mee QR collections conservative estimate prakaram, full ₹40,000 safe ga repay cheyyalem. ₹19,800 finance cheyyadam safe. Migilina ₹20,200 cash or supplier credit lo pay cheyyandi.",
            },
            "forecast_chart": {
                "p50_daily": 8000,
                "p20_daily": 6000,
                "safe_edi_cap": 1000,
                "daily_edi_proposed": daily_edi,
                "existing_edi": 500,
                "tenor_days": tenor_days,
            },
            "voice_scripts": {
                k: {
                    "script": v.script,
                    "language": v.language,
                    "decision_hash": v.decision_hash,
                }
                for k, v in voice_scripts.items()
            },
            "repayment": settlement_engine.get_current_status(session_id),
            "ledger": ledger.get_events(session_id),
        }

    elif scenario_key == "duplicate_invoice_fraud":
        # Scenario 3: Duplicate Invoice Fraud Blocked
        inv_amt = 40000
        supplier_name = "Sri Balaji Distributors"
        gstin = "36AAAAA0000A1Z3"
        fingerprint = hashlib.sha256(
            f"{gstin}:INV-2026-8812:{inv_amt}:2026-11-12".encode()
        ).hexdigest()

        ledger.append(
            session_id,
            "InvoiceUnderstandingAgent",
            "GEMINI_VISION_EXTRACTED",
            {"amount": inv_amt, "supplier": supplier_name},
        )
        ledger.append(
            session_id,
            "ParallelRiskChecks.DuplicateAgent",
            "DUPLICATE_DETECTED_BLOCKED",
            {
                "fingerprint": fingerprint,
                "match_source": "PostgreSQL invoice_fingerprint_idx",
                "prior_session": "SES_DEMO_CLEAN_BILL_APPROVE_FULL",
            },
        )
        ledger.append(
            session_id,
            "PolicyDecisionAgent",
            "POLICY_TERMINATE_FRAUD",
            {
                "decision": "DECLINE_FRAUD_DUPLICATE",
                "reason": "Exact fingerprint match detected. Double financing prohibited.",
            },
        )

        return {
            "scenario_key": scenario_key,
            "title": "Fraud Prevention - Duplicate Invoice Blocked",
            "description": "Same supplier bill submitted twice. SHA-256 invoice fingerprint matches previously financed record; immediately blocked to protect lender funds.",
            "merchant_profile": {
                "name": "Sri Ravi Kirana Store",
                "city": "Hyderabad",
                "daily_avg_qr": "₹25,000",
                "risk_tier": "SUSPICIOUS",
            },
            "invoice": {
                "number": "INV-2026-8812",
                "supplier_name": supplier_name,
                "supplier_gstin": gstin,
                "total_amount": inv_amt,
                "due_date": "2026-11-27",
            },
            "pipeline_stages": [
                {
                    "name": "Image Intake & Decryption",
                    "status": "COMPLETED",
                    "latency": "0.32s",
                    "badge": "200 OK",
                },
                {
                    "name": "Gemini 2.5 Vision Extraction",
                    "status": "COMPLETED",
                    "latency": "1.31s",
                    "badge": "Extracted",
                },
                {
                    "name": "Duplicate Invoice Detection",
                    "status": "FAILED",
                    "latency": "0.09s",
                    "badge": "DUPLICATE FOUND",
                },
                {
                    "name": "Pipeline Execution",
                    "status": "BLOCKED",
                    "latency": "0.01s",
                    "badge": "TERMINATED",
                },
            ],
            "decision": {
                "status": "DECLINE_FRAUD",
                "verdict_title": "Declined: Double Financing / Duplicate Invoice Detected",
                "approved_amount": 0,
                "reasons": [
                    "DUPLICATE_INVOICE_FINGERPRINT_MATCH",
                    "PRIOR_FINANCING_EXISTS (Session: SES_DEMO_CLEAN_BILL...)",
                    "ZERO_TOLERANCE_DOUBLE_PLEDGE",
                ],
                "why_not": "This exact invoice was already financed on 2026-11-12. Under RBI and Paytm risk guidelines, the same invoice cannot be pledged twice.",
                "merchant_explanation": "Ee bill idhe supplier ki mundhe finance cheyyabadindhi. Double-financing policy valla ee request decline cheyyabadindhi.",
            },
            "ledger": ledger.get_events(session_id),
        }

    elif scenario_key == "invalid_gstin_mismatch":
        # Scenario 4: Invalid GSTIN Checksum or Payee Name Mismatch
        inv_amt = 35000
        supplier_name = "Fly By Night Traders"
        bad_gstin = "36AAAAA0001A1Z9"  # Fails modulo-36 checksum!

        ledger.append(
            session_id,
            "InvoiceUnderstandingAgent",
            "GEMINI_VISION_EXTRACTED",
            {"amount": inv_amt, "supplier": supplier_name, "gstin": bad_gstin},
        )
        ledger.append(
            session_id,
            "ParallelRiskChecks.SupplierVerificationAgent",
            "GSTIN_CHECKSUM_FAILED",
            {
                "gstin": bad_gstin,
                "algorithm": "BASE36_MODULO",
                "verdict": "INVALID_CHECKSUM",
            },
        )
        ledger.append(
            session_id,
            "PolicyDecisionAgent",
            "POLICY_TERMINATE_RISK",
            {
                "decision": "DECLINE_RISK_SUPPLIER_UNVERIFIED",
                "reason": "Invalid GSTIN checksum and unregistered payee. Disbursal blocked.",
            },
        )

        return {
            "scenario_key": scenario_key,
            "title": "Risk Prevention - Invalid GSTIN Checksum",
            "description": "Bill from unverified entity with mathematically invalid GSTIN checksum. Disbursal blocked to prevent phantom supplier fraud.",
            "merchant_profile": {
                "name": "Sri Ravi Kirana Store",
                "city": "Hyderabad",
                "daily_avg_qr": "₹25,000",
                "risk_tier": "LOW",
            },
            "invoice": {
                "number": "INV-PHANTOM-99",
                "supplier_name": supplier_name,
                "supplier_gstin": bad_gstin,
                "total_amount": inv_amt,
            },
            "pipeline_stages": [
                {
                    "name": "Image Intake & Decryption",
                    "status": "COMPLETED",
                    "latency": "0.33s",
                    "badge": "200 OK",
                },
                {
                    "name": "Gemini 2.5 Vision Extraction",
                    "status": "COMPLETED",
                    "latency": "1.34s",
                    "badge": "Extracted",
                },
                {
                    "name": "Supplier GSTIN Checksum Algorithm",
                    "status": "FAILED",
                    "latency": "0.04s",
                    "badge": "CHECKSUM ERROR",
                },
                {
                    "name": "Policy Decision Gate",
                    "status": "BLOCKED",
                    "latency": "0.01s",
                    "badge": "BLOCKED",
                },
            ],
            "decision": {
                "status": "DECLINE_RISK",
                "verdict_title": "Declined: Supplier Verification Failed (Invalid GSTIN)",
                "approved_amount": 0,
                "reasons": [
                    "GSTIN_CHECKSUM_ALGORITHM_FAILED",
                    "UNREGISTERED_SUPPLIER_ENTITY",
                    "PURPOSE_BOUND_DISBURSAL_REFUSED",
                ],
                "why_not": "GSTIN '36AAAAA0001A1Z9' fails the Indian GSTN Modulo-36 checksum algorithm. Direct payout to unverified accounts is strictly prohibited.",
                "merchant_explanation": "Sannihithamaina supplier GSTIN invalid ga vundhi. Safe payment cheyyadam kudharadhu.",
            },
            "ledger": ledger.get_events(session_id),
        }

    else:
        # Default fallback to clean bill
        return build_scenario_data("clean_bill_approve_full")

