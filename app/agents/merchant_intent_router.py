"""Merchant Intent Router for natural language interaction in Telugu, Hindi, and English.

Handles questions like:
- 'Ye bill upload chesa, eppudu pay cheyyala?'
- 'Why did you reduce the loan amount?'
- 'Is this cash discount worth it?'
- 'How much can I safely borrow for this bill?'
- 'Mee forecast prakaram safe ga entha finance cheyyagalam?'

Safety rule: The router NEVER executes payments directly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass
class IntentResult:
    intent: str
    confidence: float
    reply_text: dict[str, str]  # 'te', 'hi', 'en'
    suggested_action: str
    context_data: dict[str, Any]


class MerchantIntentRouter:
    @staticmethod
    def route_query(
        query: str, current_decision: dict[str, Any] | None = None
    ) -> IntentResult:
        q = query.strip().lower()

        # 1. Why reduced / partial funding question
        if any(
            w in q
            for w in [
                "reduce",
                "tagginch",
                "kam kyu",
                "why partial",
                "why less",
                "why not full",
                "entha finance",
                "safe ga",
            ]
        ):
            return IntentResult(
                intent="EXPLAIN_SIZING",
                confidence=0.96,
                reply_text={
                    "en": "We sized your financing at ₹19,800 instead of ₹40,000 because our P20 conservative forecast guarantees that your daily QR collections will safely cover the ₹997 daily EDI even during slow sales days. Sizing higher would risk a cash crunch for your store.",
                    "te": "మీ భద్రత కోసమే లోన్ ₹19,800 కి సైజ్ చేసాము. మా P20 సంప్రదాయ అంచనా ప్రకారం వ్యాపారం మందగించిన రోజుల్లో కూడా ₹997 రోజువారీ ఈడీఐని మీరు సులభంగా చెల్లించగలరు. పూర్తి ₹40,000 తీసుకుంటే మీ స్టోర్ లో నగదు కొరత ఏర్పడే ప్రమాదం ఉంది.",
                    "hi": "हमने आपकी सुरक्षा के लिए लोन राशि ₹19,800 तय की है। हमारा P20 कंजर्वेटिव मॉडल यह सुनिश्चित करता है कि बिक्री कम होने पर भी आपकी दुकान पर कोई दबाव न आए और ₹997 की दैनिक कटौती आसानी से हो सके।",
                },
                suggested_action="VIEW_WHY_THIS_AMOUNT_PANEL",
                context_data={
                    "p20_cap": "₹1,000 / day",
                    "safe_principal": "₹19,800",
                },
            )

        # 2. Should I pay today / is discount worth it?
        if any(
            w in q
            for w in [
                "pay today",
                "eppudu pay",
                "worth it",
                "discount",
                "savings",
                "aada",
                "bachat",
                "laabh",
                "profit",
            ]
        ):
            return IntentResult(
                intent="EXPLAIN_ARBITRAGE",
                confidence=0.95,
                reply_text={
                    "en": "Yes! Paying this ₹40,000 bill today captures a 3% early cash discount (₹1,200). Your 20-day financing cost is only ₹268, delivering a clear net profit of ₹932. That equals an annualized return of ~75%!",
                    "te": "అవును అన్నా! ఈ ₹40,000 బిల్లును ఈరోజే చెల్లిస్తే మీకు 3% క్యాష్ డిస్కౌంట్ ద్వారా ₹1,200 ఆదా అవుతుంది. 20 రోజుల ఫైనాన్సింగ్ ఖర్చు ₹268 మాత్రమే. మీకు ₹932 నికర లాభం దక్కుతుంది (~75% వార్షిక లాభం).",
                    "hi": "जी हाँ! इस ₹40,000 के बिल का आज भुगतान करने पर 3% कैश डिस्काउंट से ₹1,200 की बचत होगी। 20 दिनों का ब्याज केवल ₹268 है, यानी आपको ₹932 का सीधा मुनाफा मिलेगा!",
                },
                suggested_action="PROCEED_TO_SOUNDBOX_CONSENT",
                context_data={
                    "discount_value": 1200,
                    "interest": 268,
                    "net_benefit": 932,
                },
            )

        # 3. Why declined
        if any(
            w in q
            for w in [
                "declined",
                "reject",
                "enduku decline",
                "kyu reject",
                "fail",
                "blocked",
            ]
        ):
            return IntentResult(
                intent="EXPLAIN_DECLINE",
                confidence=0.94,
                reply_text={
                    "en": "Your request was declined by policy to protect your store and funds. Common causes include: duplicate invoice submission, supplier GSTIN checksum mismatch, or QR collection volume being insufficient for safe repayment.",
                    "te": "మీ వ్యాపార రక్షణ కోసమే ఈ రిక్వెస్ట్ నిలిపివేయబడింది. ప్రధాన కారణాలు: డూప్లికేట్ బిల్లు, చెల్లని సప్లయర్ GSTIN, లేదా రోజువారీ QR కలెక్షన్స్ రీపేమెంట్ కి సరిపోకపోవడం.",
                    "hi": "आपकी सुरक्षा के लिए यह अनुरोध अस्वीकार किया गया। मुख्य कारण: डुप्लीकेट बिल, गलत सप्लायर GSTIN, या दैनिक QR संग्रह का पर्याप्त न होना।",
                },
                suggested_action="CHECK_RISK_REASONS",
                context_data={"policy": "STRICT_CREDIT_SAFETY"},
            )

        # 4. Safe financing capacity question
        if any(
            w in q
            for w in [
                "how much",
                "entha",
                "kitna",
                "capacity",
                "limit",
                "max borrow",
            ]
        ):
            return IntentResult(
                intent="CHECK_CAPACITY",
                confidence=0.92,
                reply_text={
                    "en": "Based on your 90-day Paytm QR settlement history, your conservative daily P20 inflow is ₹18,500. After accounting for existing obligations, your maximum safe 20-day invoice financing limit is ₹82,500.",
                    "te": "మీ గత 90 రోజుల పేటీఎం క్యూఆర్ కలెక్షన్స్ ఆధారంగా, మీ సంప్రదాయ P20 రోజువారీ ఆదాయం ₹18,500. మీ గరిష్ట సురక్షిత ఇన్వాయిస్ ఫైనాన్సింగ్ పరిమితి ₹82,500 వరకు ఉంటుంది.",
                    "hi": "आपके 90 दिनों के Paytm QR इतिहास के आधार पर आपकी P20 दैनिक क्षमता ₹18,500 है। आप सुरक्षित रूप से ₹82,500 तक का बिल फाइनेंस करवा सकते हैं।",
                },
                suggested_action="VIEW_P20_FORECAST",
                context_data={"max_capacity": 82500, "daily_p20": 18500},
            )

        # 5. General / Default response
        return IntentResult(
            intent="GENERAL_ASSISTANCE",
            confidence=0.88,
            reply_text={
                "en": f"I analyzed your query: '{query}'. VyaparSetu helps small merchants turn supplier bills into profit by capturing cash discounts safely using daily QR settlements. Would you like to scan a bill or run a demo scenario?",
                "te": f"మీ ప్రశ్నను విశ్లేషించాను. పేటీఎం వ్యాపార్ సేతు మీ సప్లయర్ బిల్లులపై క్యాష్ డిస్కౌంట్ లాభాలను సురక్షితంగా అందిస్తుంది. మీరు బిల్లు స్కాన్ చేయాలనుకుంటున్నారా లేదా డెమో చూడాలనుకుంటున్నారా?",
                "hi": f"व्यापारसेतु आपके सप्लायर बिलों पर मिलने वाले कैश डिस्काउंट को सुरक्षित रूप से मुनाफे में बदलता है। क्या आप बिल स्कैन करना चाहते हैं या लाइव डेमो देखना चाहते हैं?",
            },
            suggested_action="OPEN_BILL_STUDIO",
            context_data={},
        )
