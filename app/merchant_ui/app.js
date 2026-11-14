// VyaparSetu Enterprise Application Logic
// Public Home Landing Page + Enterprise Workspace with Google ADK Agent Graph & Sarvam AI Voice

let currentScenario = null;
let scenarioData = null;
let currentLanguage = 'te';
let streamInterval = null;
let streamSpeedMs = 2000;
let selectedNodeId = 'intake';
let currentAudioPlayer = null;
let currentSelectedFile = null;

// Currency Formatter
function money(amt) {
  if (amt == null || isNaN(amt)) return '—';
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0
  }).format(amt);
}

function showToast(msg, duration = 3500) {
  const toast = document.getElementById('global-toast');
  if (!toast) return;
  toast.textContent = msg;
  toast.hidden = false;
  setTimeout(() => { toast.hidden = true; }, duration);
}

// =========================================================================
// 1. TOP-LEVEL VIEW SWITCHING (PUBLIC HOME VS ENTERPRISE WORKSPACE)
// =========================================================================
window.navToView = function (view, targetPanel = 'panel-decisioning') {
  const homeView = document.getElementById('view-home');
  const workspaceView = document.getElementById('view-workspace');

  if (view === 'home') {
    if (homeView) homeView.style.display = 'block';
    if (workspaceView) workspaceView.style.display = 'none';
    window.scrollTo({ top: 0, behavior: 'smooth' });
  } else {
    if (homeView) homeView.style.display = 'none';
    if (workspaceView) workspaceView.style.display = 'flex';
    window.switchWorkspacePanel(targetPanel);
  }
};

window.scrollToSection = function (id) {
  const el = document.getElementById(id);
  if (el) el.scrollIntoView({ behavior: 'smooth' });
};

// =========================================================================
// 2. WORKSPACE SIDEBAR NAVIGATION & PANEL SWITCHING
// =========================================================================
const panelTitles = {
  'panel-decisioning': 'Invoice Decisioning & Credit Sizing',
  'panel-soundbox': 'Paytm Soundbox 4.0 Voice Authorization',
  'panel-repayment': 'Repayment Engine & Settlement Stream',
  'panel-superagent': 'Google ADK Agent Orchestration Graph',
  'panel-blockchain': 'Audit Ledger',
  'panel-risk': 'Cash-flow Stress Test',
  'panel-policy': 'Policy & Regulatory Assistant',
  'panel-settings': 'Voice & AI Settings',
};

window.switchWorkspacePanel = function (panelId) {
  document.querySelectorAll('.view-panel').forEach(p => p.classList.remove('active'));
  const target = document.getElementById(panelId);
  if (target) target.classList.add('active');

  const titleEl = document.getElementById('current-stage-title');
  if (titleEl && panelTitles[panelId]) {
    titleEl.textContent = panelTitles[panelId];
  }

  document.querySelectorAll('.side-nav-item').forEach(btn => btn.classList.remove('active'));
  const navIdMap = {
    'panel-decisioning': 'nav-item-decisioning',
    'panel-soundbox': 'nav-item-soundbox',
    'panel-repayment': 'nav-item-repayment',
    'panel-superagent': 'nav-item-superagent',
    'panel-blockchain': 'nav-item-blockchain',
    'panel-risk': 'nav-item-risk',
    'panel-policy': 'nav-item-policy',
    'panel-settings': 'nav-item-settings',
  };
  const activeNavBtn = document.getElementById(navIdMap[panelId]);
  if (activeNavBtn) activeNavBtn.classList.add('active');

  if (panelId === 'panel-superagent') {
    loadAgentGraphTopology();
  }

  window.scrollTo({ top: 0, behavior: 'smooth' });
};

// =========================================================================
// 3. LANGUAGE SELECTION
// =========================================================================
function setAppLanguage(lang) {
  currentLanguage = lang;
  const homeSel = document.getElementById('home-lang-select');
  const stageSel = document.getElementById('stage-lang-select');
  if (homeSel) homeSel.value = lang;
  if (stageSel) stageSel.value = lang;
  updateVoiceScript();
  updateSavingsTranscript();
  showToast(`Language set to ${lang === 'te' ? 'Telugu' : lang === 'hi' ? 'Hindi' : 'English'}`);
}

document.getElementById('home-lang-select')?.addEventListener('change', (e) => setAppLanguage(e.target.value));
document.getElementById('stage-lang-select')?.addEventListener('change', (e) => setAppLanguage(e.target.value));

// =========================================================================
// 4. INVOICE SCENARIO SELECTION & UNDERWRITING PIPELINE
// =========================================================================
window.selectInvoiceScenario = function (key) {
  window.navToView('workspace', 'panel-decisioning');
  window.loadScenario(key);
};

window.loadScenario = async function (key) {
  currentScenario = key;

  document.querySelectorAll('.scenario-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.scenarioKey === key);
  });

  const tag = document.getElementById('active-invoice-tag');
  if (tag) {
    if (key === 'clean_bill_approve_full') tag.textContent = 'Sri Balaji Distributors (₹40,000 · 3% off)';
    else if (key === 'weaker_merchant_partial') tag.textContent = 'Sri Balaji Distributors (₹40,000 · Constrained cash flow)';
    else tag.textContent = 'Unverified supplier bill — Invalid GSTIN';
  }

  showToast(`Running Google ADK Agent Pipeline...`);

  // Animate agent graph nodes
  const nodeSequence = ['intake', 'vision', 'supplier_risk', 'duplicate_fraud', 'cashflow_p20', 'arbitrage', 'policy', 'voice_consent'];
  nodeSequence.forEach((nid, i) => {
    setTimeout(() => {
      const nodeEl = document.getElementById(`node-${nid}`);
      if (nodeEl) {
        nodeEl.classList.add('active');
        const rect = nodeEl.querySelector('rect');
        if (rect) {
          rect.style.stroke = 'var(--primary-btn)';
          rect.style.strokeWidth = '2px';
        }
      }
    }, i * 140);
  });

  try {
    const res = await fetch('/api/invoice/process', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: `SES_LIVE_${key.toUpperCase()}`,
        total_amount: 40000,
        supplier_gstin: key === 'invalid_gstin_mismatch' ? '36AAAAA0000A1ZZ' : '36AAAAA0000A1Z3',
        cash_discount_percent: 3.0,
        tenor_days: 20
      })
    });
    if (!res.ok) throw new Error('Pipeline execution failed');
    scenarioData = await res.json();

    setTimeout(() => {
      renderProcessedInvoice(scenarioData);
      showToast(`ADK Workflow Complete: ${scenarioData.decision.status}`);
    }, 600);
  } catch (err) {
    console.error(err);
    showToast(`Error: ${err.message}`);
  }
};

const paymentLabels = {
  USE_AVAILABLE_CASH: 'Use available funds',
  FINANCE_FUNDING_GAP: 'Check Business Loan offers on Paytm',
  KEEP_ORIGINAL_TERMS: 'Keep original payment terms',
  USE_PAYTM_MERCHANT_LOAN: 'Check Business Loan offers on Paytm'
};
const optionForm = document.getElementById('evaluate-payment-options');
const optionCards = document.getElementById('payment-option-cards');
const optionNote = document.getElementById('payment-options-note');
const optionApprove = document.getElementById('approve-payment-option');
const optionReview = document.getElementById('payment-option-review');
const businessLoanLink = document.getElementById('payment-business-loan');
businessLoanLink.addEventListener('click', () => {
  const id = scenarioData?.option_decision_id;
  if (id) fetch(`/api/payment-options/${id}/loan-handoff`, { method: 'POST', keepalive: true }).catch(() => {});
});
let optionApproval = null;

async function paymentOptionRequest(action, payload, decisionId = scenarioData.option_decision_id) {
  const response = await fetch(`/api/payment-options/${decisionId}/${action}`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
  });
  const result = await response.json();
  if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : 'Check the entered amounts.');
  return result;
}

const savingsLocales = { te: 'te-IN', hi: 'hi-IN', en: 'en-IN' };

function savingsTranscript(plan) {
  const { supplier, date, payable, daily } = plan;
  const sections = {
    te: [['రోజువారీ పొదుపు', `ఈ బిల్లు కోసం క్యూఆర్ వసూళ్ల నుంచి రోజుకు గరిష్ఠంగా ${daily} పక్కన పెడతాం.`],
      ['చెల్లింపు తేదీ', `సరిపడా డబ్బు ఉంటే, ${date}న ${supplier}కు ${payable} చెల్లింపును డెమోలో చూపిస్తాం.`],
      ['మీ నిర్ణయం', 'చెల్లింపుకు ముందు డబ్బు తీసుకోవచ్చు లేదా ప్రణాళికను రద్దు చేయవచ్చు. కొనసాగడానికి ఆమోదం బటన్ నొక్కండి.']],
    hi: [['रोज़ की बचत', `इस बिल के लिए क्यूआर बिक्री से रोज़ अधिकतम ${daily} अलग रखेंगे।`],
      ['भुगतान की तारीख', `पर्याप्त रकम होने पर ${date} को ${supplier} को ${payable} का भुगतान डेमो में दिखाएँगे।`],
      ['आपका फैसला', 'भुगतान से पहले आप पैसे निकाल सकते हैं या योजना रद्द कर सकते हैं। शुरू करने के लिए मंज़ूरी का बटन दबाएँ।']],
    en: [['Daily set-aside', `Set aside up to ${daily} a day from QR sales for this bill.`],
      ['Scheduled payment', `If enough is available, we’ll simulate paying ${payable} to ${supplier} on ${date}.`],
      ['Your choice', 'You can withdraw or cancel before payment. Tap Approve savings plan to start.']]
  };
  return sections[currentLanguage] || sections.en;
}

function updateSavingsTranscript() {
  const transcript = document.getElementById('qr-plan-transcript');
  transcript.lang = savingsLocales[currentLanguage] || 'en-IN';
  transcript.replaceChildren();
  if (!savingsReview) return;
  for (const [title, text] of savingsTranscript(savingsReview)) {
    const card = document.createElement('div');
    const label = document.createElement('dt');
    const message = document.createElement('dd');
    label.textContent = title;
    message.textContent = text;
    card.append(label, message);
    transcript.append(card);
  }
}

const qrControls = document.getElementById('qr-savings-controls');
const qrActive = document.getElementById('qr-active-controls');
const qrStatus = document.getElementById('qr-plan-status');
let savingsReview;
let savingsBusy = false;

async function savingsAction(action, extra = {}) {
  const review = savingsReview;
  if (!review || savingsBusy) return;
  savingsBusy = true;
  try {
    const result = await paymentOptionRequest('qr-savings', { action, token: review.token, ...extra }, review.id);
    if (review !== savingsReview) return;
    if (action !== 'quote_withdrawal') {
      const monitor = document.getElementById('qr-payment-monitor');
      monitor.hidden = false;
      document.getElementById('card-step-repayment').hidden = true;
      const scheduled = result.status === 'SCHEDULED';
      qrActive.hidden = !scheduled;
      document.getElementById('qr-cancel-payment').hidden = !scheduled;
      document.getElementById('qr-plan-confirm').hidden = true;
      document.getElementById('qr-payment-summary').textContent =
        `${money(result.payable / 100)} to ${result.supplier} on ${formatPaymentDate(result.payment_date)} · Simulation`;
      document.getElementById('qr-payment-progress').textContent = scheduled
        ? `Set aside: ${money(result.balance / 100)} · Still needed: ${money(result.remaining / 100)} · ` +
          (result.shortfall ? `At risk: ${money(result.shortfall / 100)} short` : 'On track')
        : { PAID: 'Simulated payment complete', SKIPPED: 'Payment skipped', CANCELED: 'Payment canceled' }[result.status];
      const activity = document.getElementById('qr-payment-activity');
      activity.replaceChildren(...result.activity.map(text => {
        const item = document.createElement('li');
        item.textContent = text;
        return item;
      }));
      if (action === 'activate') window.switchWorkspacePanel('panel-repayment');
    }
    return result;
  } catch (error) {
    if (review === savingsReview) {
      qrStatus.textContent = error.message;
      showToast(error.message);
    }
  } finally {
    savingsBusy = false;
  }
}

document.getElementById('qr-plan-confirm').onclick = () => savingsAction('activate', { utterance: 'approve' });
document.getElementById('qr-plan-listen').onclick = async () => {
  const review = savingsReview;
  if (!review) return;
  const language = currentLanguage;
  const script = savingsTranscript(review).map(([, text]) => text).join(' ');
  try {
    const response = await fetch('/api/voice/sarvam-tts', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: script, language })
    });
    const result = await response.json();
    if (review !== savingsReview || language !== currentLanguage) return;
    if (!result.audio_base64) throw new Error('Audio unavailable');
    await new Audio(`data:audio/wav;base64,${result.audio_base64}`).play();
  } catch {
    if (review === savingsReview && language === currentLanguage) {
      const speech = new SpeechSynthesisUtterance(script);
      speech.lang = savingsLocales[language] || 'en-IN';
      speechSynthesis.speak(speech);
    }
  }
};
document.getElementById('qr-cancel-payment').onclick = () => {
  if (window.confirm('Cancel this simulated supplier payment and release the set-aside?')) savingsAction('cancel');
};
document.getElementById('qr-next-day').onclick = () => savingsAction('advance');
document.getElementById('qr-withdraw').onclick = async () => {
  const review = savingsReview;
  const amount = Math.round(Number(document.getElementById('qr-withdraw-amount').value) * 100);
  const quote = await savingsAction('quote_withdrawal', { amount });
  if (!quote || review !== savingsReview) return;
  const warning = quote.shortfall
    ? `You could be ${money(quote.shortfall / 100)} short by the discount deadline and may miss the discount. `
    : '';
  if (window.confirm(warning + 'Withdraw ' + money(amount / 100) + ' from your simulated set-aside?')) {
    await savingsAction('withdraw', { amount });
  }
};

const optionActions = document.getElementById('payment-option-actions');
const keepInvoiceTerms = document.getElementById('keep-invoice-terms');
const exploreEarlyPayment = document.getElementById('explore-early-payment');

exploreEarlyPayment.onclick = () => {
  optionForm.hidden = false;
  exploreEarlyPayment.setAttribute('aria-expanded', 'true');
  optionForm.requestSubmit();
};

keepInvoiceTerms.onclick = async () => {
  const invoice = scenarioData;
  keepInvoiceTerms.disabled = true;
  optionApproval = null;
  optionReview.hidden = true;
  qrControls.hidden = true;
  savingsReview = null;
  try {
    const result = await paymentOptionRequest('select', { option_id: 'KEEP_ORIGINAL_TERMS' }, invoice.option_decision_id);
    if (scenarioData !== invoice) return;
    optionApproval = result.approval_token;
    businessLoanLink.hidden = true;
    document.getElementById('payment-review-title').textContent = 'Review original payment terms';
    document.getElementById('payment-review-details').textContent =
      'No payment today. ' + money(invoice.invoice.total_amount) + ' remains due on ' + invoice.invoice.due_date + '.';
    optionApprove.textContent = 'Confirm original terms';
    optionApprove.hidden = false;
    optionReview.hidden = false;
    optionReview.scrollIntoView({ block: 'nearest' });
  } catch (error) {
    if (scenarioData === invoice) optionNote.textContent = error.message;
  } finally {
    keepInvoiceTerms.disabled = false;
  }
};

optionForm.addEventListener('input', () => {
  optionApproval = null;
  optionApprove.hidden = true;
  optionReview.hidden = true;
  qrControls.hidden = true;
  savingsReview = null;
  optionCards.replaceChildren();
});
optionForm.addEventListener('submit', async event => {
  event.preventDefault();
  const decisionId = scenarioData.option_decision_id;
  optionApproval = null;
  optionApprove.hidden = true;
  optionReview.hidden = true;
  qrControls.hidden = true;
  savingsReview = null;
  optionCards.replaceChildren();
  try {
    const values = new FormData(optionForm);
    const result = await paymentOptionRequest('evaluate', {
      payment_date: qrPaymentDate.value || null,
      cash_paise: Math.round(Number(values.get('cash')) * 100),
      buffer_paise: Math.round(Number(shopReserve.value) * 100)
    }, decisionId);
    if (scenarioData.option_decision_id !== decisionId) return;
    optionNote.textContent = '';
    const loanChoice = result.options.find(item => item.id === 'USE_PAYTM_MERCHANT_LOAN')
      || result.options.find(item => item.id === 'FINANCE_FUNDING_GAP' && item.financing > 0);
    for (const option of result.options) {
      if (option.id === 'USE_AVAILABLE_CASH' && !option.feasible) continue;
      if (option.id === 'FINANCE_FUNDING_GAP' && option !== loanChoice) continue;
      const card = document.createElement('article');
      card.className = 'card';
      const title = document.createElement('h4');
      title.textContent = paymentLabels[option.id] + (result.recommended === option.id ? ' · Recommended' : '');
      const details = document.createElement('p');
      const rupees = paise => '₹' + (paise / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 });
      const keepTerms = option.id === 'KEEP_ORIGINAL_TERMS';
      const gap = option.financing + option.loan;
      const due = formatPaymentDate(result.due_date);
      const borrowingOption = option === loanChoice;

      details.textContent = keepTerms
        ? `Pay nothing today. The full ${rupees(option.supplier_payable)} is due on ${due}.`
        : borrowingOption
          ? `After your projected QR collections and any cash you add, you’d need about ${rupees(gap)} more to pay early.`
          : option.feasible
            ? `You could cover the ${rupees(option.supplier_payable)} early payment with ${rupees(option.qr_contribution || 0)} from QR collections and ${rupees(option.cash_contribution)} from cash. You’d save ${rupees(option.net_benefit)}.`
            : 'Your projected QR collections and available cash won’t cover the bill before the discount ends.';
      const button = document.createElement('button');
      button.className = 'btn btn-soft';
      button.type = 'button';
      button.textContent = borrowingOption ? 'Review shortfall'
        : keepTerms ? 'Review due date' : option.feasible ? 'Review payment plan' : 'Unavailable';

      button.onclick = async () => {
        optionApproval = null;
        optionApprove.hidden = true;
        optionReview.hidden = true;
  qrControls.hidden = true;
  savingsReview = null;
        try {
          const selected = await paymentOptionRequest('select', { option_id: option.id }, decisionId);
          if (scenarioData.option_decision_id !== decisionId) return;
          const savingsPlan = selected.state === 'QR_PLAN_REVIEW';
          optionApproval = savingsPlan ? null : selected.approval_token || null;
          if (savingsPlan) {
            if (!selected.schedule?.length) {
              throw new Error('The daily savings breakdown is unavailable. Refresh and re-upload the invoice to try again.');
            }
            savingsReview = {
              id: decisionId, token: selected.approval_token,
              supplier: scenarioData.invoice.supplier_name,
              date: formatPaymentDate(selected.payment_date),
              payable: money(selected.payable / 100),
              daily: money(selected.daily_target / 100)
            };
            qrActive.hidden = true;
            const amount = paise => '₹' + (paise / 100).toLocaleString('en-IN', { maximumFractionDigits: 2 });
            const first = selected.schedule[0];
            const remaining = day => day.available_paise - day.deposit_paise;
            document.getElementById('qr-plan-payment').textContent =
              `Set aside ${amount(selected.target)} by ${formatPaymentDate(selected.payment_date)}. We’ll simulate paying ${scenarioData.invoice.supplier_name} that day if there’s enough.`;
            document.getElementById('qr-review-inflow').textContent = amount(first.inflow_paise);
            document.getElementById('qr-review-deposit').textContent = amount(first.deposit_paise);
            document.getElementById('qr-review-left').textContent = amount(remaining(first));
            document.getElementById('qr-review-day').textContent =
              `First QR funds expected by ${formatPaymentDate(first.available_by)}.`;
            const rows = document.getElementById('qr-review-rows');
            rows.replaceChildren();
            let total = 0;
            for (const day of selected.schedule) {
              total += day.deposit_paise;
              const row = rows.insertRow();
              for (const value of [formatPaymentDate(day.available_by), amount(day.inflow_paise),
                amount(day.deposit_paise), amount(remaining(day)), amount(total)]) {
                row.insertCell().textContent = value;
              }
            }
            updateSavingsTranscript();
            qrStatus.textContent = '';
            document.getElementById('qr-plan-confirm').hidden = false;
            qrControls.hidden = false;
            document.getElementById('card-step-soundbox').hidden = true;
            window.switchWorkspacePanel('panel-soundbox');
            return;
          }
          optionCards.querySelectorAll('article').forEach(item => item.classList.toggle('payment-option-selected', item === card));
          optionReview.hidden = false;
          const financingPlan = option.id === 'FINANCE_FUNDING_GAP' || option.id === 'USE_PAYTM_MERCHANT_LOAN';
          businessLoanLink.hidden = !financingPlan;
          optionApprove.hidden = financingPlan || !optionApproval;
          document.getElementById('payment-review-title').textContent = financingPlan ? 'Before you borrow' : paymentLabels[option.id];
          document.getElementById('payment-review-details').textContent = financingPlan
            ? `The supplier offers ${rupees((scenarioData.invoice.total_amount * 100) - option.supplier_payable)} off for paying early. Check what a loan would cost in Paytm before deciding. If the total cost uses up that discount, you can pay ${rupees(scenarioData.invoice.total_amount * 100)} on ${due} instead.`
            : details.textContent;
          optionApprove.textContent = keepTerms ? 'Keep original terms' : 'Confirm simulated payment';
          optionReview.scrollIntoView({ block: 'nearest' });
          optionNote.textContent = optionApproval
            ? 'Selected: ' + paymentLabels[option.id] + '. Review the amounts before approving.'
            : financingPlan
              ? 'Paytm’s lending partners will show any offers you qualify for.'
              : 'This plan uses projected QR inflows. Review actual settlements before paying your supplier.';
        } catch (error) {
          optionNote.textContent = error.message;
        }
      };
      card.append(title, details, button);
      optionCards.append(card);
    }
  } catch (error) {
    optionNote.textContent = error.message;
  }
});
optionApprove.onclick = async () => {
  if (!optionApproval) return;
  optionApprove.disabled = true;
  try {
    const receipt = await paymentOptionRequest('approve', { approval_token: optionApproval });
    optionNote.textContent = receipt.status === 'ORIGINAL_TERMS_RETAINED'
      ? 'Original terms retained. Invoice due on ' + formatPaymentDate(receipt.due_date) + '.'
      : 'Simulated supplier payment recorded. Reference ' + receipt.reference;
    optionForm.hidden = true;
    optionActions.hidden = true;
    optionCards.replaceChildren();
    optionApprove.hidden = true;
    optionReview.hidden = true;
  qrControls.hidden = true;
  savingsReview = null;
    optionApproval = null;
  } catch (error) {
    optionNote.textContent = error.message;
  } finally {
    optionApprove.disabled = false;
  }
};

function formatPaymentDate(value) {
  if (!value) return 'Date unavailable';
  return new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium', timeZone: 'UTC' })
    .format(new Date(value + 'T00:00:00Z'));
}

const shopReserve = document.getElementById('qr-shop-reserve');

const qrPaymentDate = document.getElementById('qr-payment-date');

function renderReserveComparison(qr) {
  if (!qr?.forecast_days || !qrPaymentDate.value || !qrPaymentDate.checkValidity()) return;
  const invoice = scenarioData.invoice;
  const date = qrPaymentDate.value;
  const discounted = Boolean(invoice.discount_expiry && date <= invoice.discount_expiry);
  const payable = discounted ? qr.payable_paise : invoice.total_amount * 100;
  const rows = qr.forecast_days.filter(day => day.available_by <= date);
  const last = rows.at(-1);
  const reserve = Math.round(Math.max(0, Number(shopReserve.value) || 0) * 100);
  const total = Math.max(0, (last?.cumulative_paise || 0) - reserve);
  const slow = Math.max(0, (last?.slower_cumulative_paise || 0) - reserve);
  const gap = Math.max(0, payable - total);
  document.getElementById('qr-total-by-date').textContent = money(total / 100);
  document.getElementById('qr-daily-amount').textContent = rows.length
    ? money(rows.reduce((sum, day) => sum + day.inflow_paise, 0) / rows.length / 100) : '—';
  document.getElementById('qr-reserve-comparison').textContent = gap ? money(gap / 100) : 'Covered by forecast';
  document.getElementById('qr-date-terms').textContent = `${money(payable / 100)} to pay on ${formatPaymentDate(date)}${discounted ? ' with discount' : ''}. Simulated QR funds after repayments and shop reserve.`;
  document.getElementById('qr-slower-sales').textContent = slow < payable
    ? 'If sales slow: ' + money((payable - slow) / 100) + ' still needed.' : 'Slower sales could still cover this payment.';
  const body = document.getElementById('qr-forecast-rows');
  body.replaceChildren();
  for (const day of rows) {
    const row = body.insertRow();
    for (const value of [formatPaymentDate(day.available_by), money(day.inflow_paise / 100),
      money(qr.existing_repayment_paise / 100), money(day.available_paise / 100), money(day.cumulative_paise / 100)]) {
      row.insertCell().textContent = value;
    }
  }
  exploreEarlyPayment.hidden = !discounted;
}

qrPaymentDate.addEventListener('input', () => {
  renderReserveComparison(scenarioData?.qr_plan);
  optionForm.hidden = true;
  optionCards.replaceChildren();
  optionReview.hidden = true;
  optionApproval = null;
});

shopReserve.addEventListener('input', () => {
  renderReserveComparison(scenarioData?.qr_plan);
  optionApproval = null;
  optionReview.hidden = true;
  qrControls.hidden = true;
  savingsReview = null;
  optionApprove.hidden = true;
  optionCards.replaceChildren();
});

function renderProcessedInvoice(data) {
  document.getElementById('invoice-processing-status').hidden = true;
  document.getElementById('card-step-verification').hidden = false;
  document.getElementById('card-step-underwriting').hidden = false;
  document.getElementById('card-step-soundbox').hidden = Boolean(data.option_decision_id);
  document.getElementById('qr-payment-monitor').hidden = true;
  document.getElementById('card-step-repayment').hidden = data.scenario_key === 'custom_uploaded_invoice';
  const usesOptions = data.scenario_key === 'custom_uploaded_invoice' || Boolean(data.option_decision_id);
  document.getElementById('payment-options').hidden = !usesOptions;
  optionForm.hidden = true;
  const earlySummary = document.getElementById('early-payment-summary');
  const qrSummary = document.getElementById('qr-coverage-summary');
  const qr = data.option_decision_id && data.qr_plan;
  document.getElementById('qr-date-card').hidden = !qr;
  document.getElementById('discount-date-card').hidden = !qr;
  document.getElementById('payment-original-due').textContent = formatPaymentDate(data.invoice?.due_date);
  document.getElementById('payment-original-amount').textContent = money(data.invoice?.total_amount || 0) + ' at original terms';
  if (qr) {
    const expiry = data.invoice.discount_expiry;
    const date = new Date((expiry || data.invoice.due_date) + 'T00:00:00Z');
    const format = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Kolkata', year: 'numeric', month: '2-digit', day: '2-digit' });
    const parts = Object.fromEntries(format.formatToParts().map(item => [item.type, item.value]));
    const daysLeft = (date.getTime() - Date.UTC(+parts.year, +parts.month - 1, +parts.day)) / 86400000;
    const gap = Math.max(0, qr.payable_paise - qr.projected_paise);
    document.getElementById('early-payment-date').textContent = formatPaymentDate(expiry);
    earlySummary.textContent = `Pay ${money(qr.payable_paise / 100)} to save ${money(data.invoice.cash_discount_val)} · ${daysLeft === 0 ? 'Ends today' : daysLeft + (daysLeft === 1 ? ' day left' : ' days left')}`;
    document.getElementById('qr-coverage-date').textContent = gap
      ? money(gap / 100) + ' projected shortfall' : formatPaymentDate(qr.coverage_date);
    qrSummary.textContent = 'Simulated QR forecast before your operating reserve.';
  }
  const breakdown = document.getElementById('qr-funding-breakdown');
  breakdown.hidden = !qr?.forecast_days;
  document.getElementById('invoice-date-cards').hidden = !breakdown.hidden;
  if (!breakdown.hidden) {
    qrPaymentDate.min = qr.as_of;
    qrPaymentDate.max = qr.forecast_days.at(-1)?.available_by || qr.as_of;
    qrPaymentDate.value = data.invoice.discount_expiry || data.invoice.due_date;
    if (!qrPaymentDate.checkValidity()) qrPaymentDate.value = qrPaymentDate.max;
    document.getElementById('qr-funding-explanation').textContent =
      'Daily figures use simulated QR sales and exclude your shop reserve.';
  }
  optionForm.reset();
  optionActions.hidden = !data.option_decision_id;
  exploreEarlyPayment.hidden = !(data.invoice?.cash_discount_percent > 0);
  renderReserveComparison(qr);
  exploreEarlyPayment.setAttribute('aria-expanded', 'false');
  optionCards.replaceChildren();
  optionApprove.hidden = true;
  optionReview.hidden = true;
  qrControls.hidden = true;
  savingsReview = null;
  optionApproval = null;
  optionNote.textContent = data.option_decision_id
    ? 'Keep your original due date, or explore early payment if a discount is available.'
    : data.payment_blocker || 'Verify the supplier and invoice due date before comparing options.';
  document.getElementById('btn-proceed-consent').hidden = usesOptions;
  if (!data) return;

  const inv = data.invoice || {};
  const dec = data.decision || {};

  // STEP 2: Extraction & Terms
  const verifTag = document.getElementById('verification-status-tag');
  if (verifTag) {
    verifTag.textContent = dec.status === 'DECLINED' ? 'Verification Failed' : 'Verified Valid';
    verifTag.className = `badge ${dec.status === 'DECLINED' ? 'badge-red' : 'badge-green'}`;
  }

  const supName = document.getElementById('disp-supplier-name');
  if (supName) supName.textContent = inv.supplier_name || '—';

  const gstinStatus = document.getElementById('disp-gstin-status');
  if (gstinStatus) {
    if (dec.status === 'DECLINED' && dec.reasons?.some(r => r.includes('GSTIN'))) {
      gstinStatus.textContent = 'Checksum Failed (Invalid)';
      gstinStatus.className = 'c-red';
    } else {
      gstinStatus.textContent = 'Passed (Modulo-36 Valid)';
      gstinStatus.className = 'c-green';
    }
  }

  const invTot = document.getElementById('disp-inv-total');
  if (invTot) invTot.textContent = money(inv.total_amount);

  const discTerms = document.getElementById('disp-disc-terms');
  if (discTerms) discTerms.textContent = `${inv.cash_discount_percent}% Prompt Discount (${money(inv.cash_discount_val)})`;

  // STEP 3: Underwriting & Arbitrage
  const verdictBadge = document.getElementById('decision-verdict-badge');
  if (verdictBadge) {
    verdictBadge.textContent = dec.status;
    verdictBadge.className = `verdict-pill ${dec.status === 'APPROVE_FULL' ? 'approve' : dec.status === 'APPROVE_PARTIAL' ? 'partial' : 'decline'}`;
  }

  const decTitle = document.getElementById('decision-verdict-title');
  if (decTitle) decTitle.textContent = dec.verdict_title;

  const decExp = document.getElementById('decision-merchant-explanation');
  if (decExp) decExp.textContent = dec.merchant_explanation;

  const setVal = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
  setVal('arb-invoice-amt', money(inv.total_amount));
  setVal('arb-discount-val', `-${money(inv.cash_discount_val || 0)}`);
  const discountTerms = document.getElementById('arb-discount-terms');
  discountTerms.hidden = !(inv.discount_expiry && inv.cash_discount_val > 0);
  discountTerms.textContent = discountTerms.hidden ? '' :
    `Pay ${money(inv.total_amount - inv.cash_discount_val)} by ${formatPaymentDate(inv.discount_expiry)}`;
  setVal('arb-pay-amt', money(dec.approved_amount || inv.total_amount));
  setVal('arb-interest-cost', `+${money(dec.financing_cost || 0)}`);
  setVal('arb-net-benefit', `+${money(dec.net_benefit || 0)}`);
  setVal('arb-daily-edi', dec.daily_edi ? `${money(dec.daily_edi)} / day` : 'N/A');

  const dueDate = /^\d{4}-\d{2}-\d{2}$/.test(inv.due_date)
    ? Date.parse(inv.due_date + 'T00:00:00Z') : NaN;
  const today = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Kolkata', year: 'numeric', month: '2-digit', day: '2-digit'
  }).formatToParts();
  const part = type => Number(today.find(item => item.type === type).value);
  const days = (dueDate - Date.UTC(part('year'), part('month') - 1, part('day'))) / 86400000;
  setVal('arb-invoice-due', Number.isFinite(days)
    ? new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium', timeZone: 'UTC' }).format(dueDate)
    : 'Due date unavailable');
  const dayLabel = Math.abs(days) === 1 ? 'day' : 'days';
  setVal('arb-invoice-countdown', !Number.isFinite(days) ? '' : days === 0
    ? 'Due today' : days > 0 ? `Due in ${days} ${dayLabel}` : `${-days} ${dayLabel} overdue`);
  setVal('decision-step-label', usesOptions ? 'STEP 3 · INVOICE AND PAYMENT OPTIONS' : 'STEP 3 · P20 CASHFLOW UNDERWRITING & ARBITRAGE');
  document.querySelectorAll('[data-legacy-financing]').forEach(cell => { cell.hidden = usesOptions; });
  if (usesOptions) {
    verdictBadge.textContent = data.option_decision_id ? 'Review' : 'Check invoice';
    verdictBadge.className = 'verdict-pill partial';
    decTitle.textContent = 'Review your invoice';
    decExp.textContent = 'Check the amount and due date before choosing how to pay.';
  }

  const lockText = document.getElementById('supplier-lock-text');
  if (lockText) {
    lockText.textContent = `${inv.supplier_name} (GSTIN: ${inv.supplier_gstin}) · ${inv.payout_account || 'Verified Bank'}`;
  }
  const tick = document.getElementById('supplier-verified-tick');
  if (tick) {
    if (dec.status === 'DECLINED') {
      tick.textContent = 'Blocked';
      tick.className = 'badge badge-red';
    } else {
      tick.textContent = 'Verified Match';
      tick.className = 'badge badge-green';
    }
  }

  // Proceed button
  const proceedBtn = document.getElementById('btn-proceed-consent');
  if (proceedBtn) {
    if (dec.status === 'APPROVE_FULL' || dec.status === 'APPROVE_PARTIAL') {
      proceedBtn.disabled = false;
      proceedBtn.style.opacity = '1';
      proceedBtn.style.cursor = 'pointer';
      proceedBtn.className = 'btn btn-primary btn-block btn-lg';
      proceedBtn.textContent = 'Proceed to Soundbox 4.0 Voice Consent →';
    } else {
      proceedBtn.disabled = true;
      proceedBtn.style.opacity = '0.6';
      proceedBtn.style.cursor = 'not-allowed';
      proceedBtn.className = 'btn btn-outline btn-block btn-lg';
      proceedBtn.textContent = 'Facility Declined (Risk Policy Block)';
    }
  }

  // STEP 4: Soundbox Script
  updateVoiceScript();

  // Populate Ledger
  renderLedger(data.ledger || []);

  // Update Operations Graph Node states
  inspectAgentNode(selectedNodeId || 'intake');
}

function updateVoiceScript() {
  if (!scenarioData || !scenarioData.voice_scripts) return;
  const scriptObj = scenarioData.voice_scripts[currentLanguage] || scenarioData.voice_scripts['en'];
  if (scriptObj) {
    const textEl = document.getElementById('voice-script-text');
    if (textEl) textEl.textContent = `"${scriptObj.script}"`;
    const hashEl = document.getElementById('display-decision-hash');
    if (hashEl) hashEl.textContent = scriptObj.decision_hash;
  }
}

// =========================================================================
// 5. SARVAM AI VOICE INTEGRATION
// =========================================================================
window.playVoiceAudio = async function () {
  const scriptText = document.getElementById('voice-script-text')?.textContent?.replace(/^"|"$/g, '') ||
    'Sri Ravi Kirana Store. Your supplier payment of Rupees 38,800 is ready for confirmation.';
  const speaker = document.getElementById('sarvam-speaker-select')?.value || 'priya';

  const waveform = document.getElementById('soundbox-waveform');
  if (waveform) waveform.classList.add('waveform-active');

  showToast('Generating Sarvam AI voice audio...');

  try {
    const res = await fetch('/api/voice/sarvam-tts', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        text: scriptText,
        language: currentLanguage,
        speaker
      })
    });

    const data = await res.json();

    if (data.status === 'success' && data.audio_base64) {
      if (currentAudioPlayer) {
        currentAudioPlayer.pause();
      }
      currentAudioPlayer = new Audio(`data:audio/wav;base64,${data.audio_base64}`);
      currentAudioPlayer.onended = () => {
        if (waveform) waveform.classList.remove('waveform-active');
      };
      await currentAudioPlayer.play();
      showToast(`Playing Sarvam AI Bulbul v3 (${currentLanguage.toUpperCase()})`);
    } else {
      speakBrowserUtterance(scriptText);
      setTimeout(() => {
        if (waveform) waveform.classList.remove('waveform-active');
      }, 5000);
      showToast(data.message || 'Playing browser voice.');
    }
  } catch (err) {
    console.error(err);
    speakBrowserUtterance(scriptText);
    setTimeout(() => {
      if (waveform) waveform.classList.remove('waveform-active');
    }, 5000);
  }
};

window.testSarvamVoice = function () {
  const samplePhrase = currentLanguage === 'te'
    ? 'నమస్కారం, వ్యాపార్ సేతు పేటీఎం సౌండ్‌బాక్స్ వాయిస్ సేవలు సిద్ధంగా ఉన్నాయి.'
    : currentLanguage === 'hi'
      ? 'नमस्ते, व्यापार सेतु पेटीएम साउंडबॉक्स वॉयस सेवाएं तैयार हैं।'
      : 'Hello, VyaparSetu Paytm Soundbox voice service is operational.';

  const speaker = document.getElementById('sarvam-speaker-select')?.value || 'priya';

  fetch('/api/voice/sarvam-tts', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      text: samplePhrase,
      language: currentLanguage,
      speaker
    })
  })
    .then(r => r.json())
    .then(data => {
      if (data.audio_base64) {
        const audio = new Audio(`data:audio/wav;base64,${data.audio_base64}`);
        audio.play();
        showToast('Sarvam voice test successful!');
      } else {
        speakBrowserUtterance(samplePhrase);
        showToast('Tested using browser speech synthesis.');
      }
    })
    .catch(() => {
      speakBrowserUtterance(samplePhrase);
    });
};

function speakBrowserUtterance(text) {
  if (!('speechSynthesis' in window)) return;
  window.speechSynthesis.cancel();
  const utter = new SpeechSynthesisUtterance(text);
  if (currentLanguage === 'hi') utter.lang = 'hi-IN';
  else if (currentLanguage === 'te') utter.lang = 'te-IN';
  else utter.lang = 'en-IN';
  utter.rate = 0.95;
  window.speechSynthesis.speak(utter);
}

// =========================================================================
// 6. VOICE CONSENT APPROVAL & DISBURSAL
// =========================================================================
window.confirmConsent = async function (utterance) {
  if (scenarioData?.scenario_key === 'custom_uploaded_invoice' || scenarioData?.option_decision_id) {
    showToast('Select and approve an option in the invoice workspace.');
    return;
  }
  if (!scenarioData) {
    showToast('Select or upload an invoice first.');
    return;
  }

  const scriptObj = scenarioData?.voice_scripts?.[currentLanguage] || scenarioData?.voice_scripts?.['en'];
  const hash = scriptObj?.decision_hash || 'DEMO_HASH';
  const dec = scenarioData?.decision || {};

  showToast(`Soundbox recording consent: "${utterance}"...`);

  try {
    const res = await fetch('/api/voice/consent', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: scenarioData.session_id,
        decision_id: `DEC_${scenarioData.session_id}`,
        utterance: utterance,
        decision_hash: hash,
        language: currentLanguage
      })
    });
    const consentRes = await res.json();

    if (consentRes.valid) {
      const payRes = await fetch('/api/payments/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: scenarioData.session_id,
          decision_id: `DEC_${scenarioData.session_id}`,
          decision_status: dec.status,
          approved_amount: dec.approved_amount || 38800,
          requested_amount: dec.approved_amount || 38800,
          supplier_name: scenarioData?.invoice?.supplier_name || 'Sri Balaji Distributors',
          supplier_account: 'HDFC Bank •••• 4201',
          daily_edi: dec.daily_edi || 1953,
          tenor_days: dec.tenor_days || 20,
          consent_valid: true,
          consent_hash: hash
        })
      });
      const payment = await payRes.json();

      window.switchWorkspacePanel('panel-repayment');

      const card = document.getElementById('payment-success-card');
      if (card) {
        card.hidden = false;
        document.getElementById('receipt-ref').textContent = payment.payment_reference;
        document.getElementById('receipt-acc').textContent = payment.account;
        document.getElementById('receipt-edi').textContent = `${money(payment.daily_edi)} / day`;
        document.getElementById('receipt-tenor').textContent = `${payment.tenor_days} Days`;
      }

      showToast(`Disbursal confirmed. Ref: ${payment.payment_reference}`, 5000);

      const payNode = document.getElementById('node-payment_exec');
      if (payNode) payNode.classList.add('active');

      if (scenarioData.repayment) {
        renderSettlementState(scenarioData.repayment);
      }
    } else {
      showToast(`Consent declined: ${consentRes.message}`, 4000);
    }
  } catch (err) {
    showToast(`Error: ${err.message}`);
  }
};

// =========================================================================
// 7. SETTLEMENT STREAM TABLE & STEPPING
// =========================================================================
function renderSettlementState(state) {
  if (!state) return;
  const tbody = document.getElementById('settlement-stream-tbody');
  if (!tbody) return;
  tbody.innerHTML = '';
  (state.events || []).forEach(evt => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><strong>#${evt.day_number}</strong></td>
      <td>${evt.date_str}</td>
      <td><strong class="c-green">${money(evt.inflow_amount)}</strong></td>
      <td><strong class="c-accent">${money(evt.edi_deduction)}</strong></td>
      <td>${money(evt.merchant_payout)}</td>
      <td>${money(evt.remaining_edi)}</td>
      <td><strong class="${evt.coverage_ratio >= 1.2 ? 'c-green' : evt.coverage_ratio >= 1.0 ? 'c-amber' : 'c-red'}">${evt.coverage_ratio}x</strong></td>
    `;
    tbody.appendChild(tr);
  });
}

document.getElementById('btn-stream-step')?.addEventListener('click', async () => {
  if (!scenarioData) return;
  try {
    const res = await fetch('/api/settlements/step', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: scenarioData.session_id })
    });
    const data = await res.json();
    renderSettlementState(data.current_status);
  } catch (err) {
    console.error(err);
  }
});

document.getElementById('btn-stream-play')?.addEventListener('click', (e) => {
  if (!scenarioData) return;
  const btn = e.target;
  if (streamInterval) {
    clearInterval(streamInterval);
    streamInterval = null;
    btn.textContent = 'Auto Stream';
  } else {
    btn.textContent = 'Pause';
    streamInterval = setInterval(() => {
      document.getElementById('btn-stream-step').click();
    }, streamSpeedMs);
  }
});

// =========================================================================
// 8. ADK ORCHESTRATION GRAPH INSPECTOR
// =========================================================================
let workflowStream;
const workflowNodes = new Map();
const nodeNames = {
  intake: 'Invoice intake', vision: 'Document extraction', supplier_risk: 'Supplier checksum',
  cashflow_p20: 'QR cash-flow forecast',
  policy: 'Payment options', voice_consent: 'Merchant review', payment_exec: 'Merchant outcome'
};

function watchWorkflow(runId) {
  workflowStream?.close();
  workflowNodes.clear();
  document.querySelectorAll('.agent-node').forEach(node => delete node.dataset.status);
  inspectAgentNode('intake');
  workflowStream = new EventSource(`/api/workflow-runs/${runId}/events`);
  workflowStream.onmessage = ({ data }) => {
    const event = JSON.parse(data);
    workflowNodes.set(event.id, event);
    const node = document.getElementById(`node-${event.id}`);
    if (node) node.dataset.status = event.status;
    if (selectedNodeId === event.id) inspectAgentNode(event.id);
  };
}

window.inspectAgentNode = function (nodeId) {
  selectedNodeId = nodeId;
  document.querySelectorAll('.agent-node').forEach(node => {
    node.classList.toggle('inspected', node.id === `node-${nodeId}`);
  });
  const event = workflowNodes.get(nodeId);
  const nodeInfo = {
    ...event, id: nodeId, name: nodeNames[nodeId] || nodeId,
    status: event?.status || 'NOT RUN',
    role: event?.output?.next_step || '',
    model: event?.output?.provider || '—'
  };

  document.getElementById('inspector-title').textContent = nodeInfo.name;
  document.getElementById('inspector-status-badge').textContent = nodeInfo.status || 'Active';
  document.getElementById('inspector-status-badge').className = `badge ${nodeInfo.status === 'COMPLETED' ? 'badge-green' : nodeInfo.status === 'FAILED' ? 'badge-red' : 'badge-accent'}`;
  document.getElementById('inspector-role').textContent = nodeInfo.role;
  document.getElementById('inspector-model').textContent = nodeInfo.model || 'gemini-2.5-flash';
  document.getElementById('inspector-latency').textContent = nodeInfo.latency || '—';
  document.getElementById('inspector-payload').textContent = JSON.stringify({
    agent_id: nodeInfo.id,
    input_state: nodeInfo.input || {},
    output_state: nodeInfo.output || {},
  }, null, 2);
};



async function loadAgentGraphTopology() {
  try {
    const sid = scenarioData ? scenarioData.session_id : 'SES_LATEST';
    const res = await fetch(`/api/agent-graph?session_id=${sid}`);
    const data = await res.json();
    const stEl = document.getElementById('graph-runtime-status');
    if (stEl) stEl.textContent = `Workflow: ${data.framework}`;
  } catch (err) {
    console.error(err);
  }
}

// =========================================================================
// 9. AUDIT BLOCKCHAIN LEDGER & TAMPER DETECTION
// =========================================================================
function renderLedger(records) {
  const tbody = document.getElementById('ledger-tbody');
  if (!tbody) return;
  tbody.innerHTML = '';
  if (!records || records.length === 0) {
    tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 24px;">No events recorded.</td></tr>';
    return;
  }
  records.forEach(rec => {
    const tr = document.createElement('tr');
    tr.id = `ledger-row-${rec.id}`;
    tr.innerHTML = `
      <td><strong>#${rec.id}</strong></td>
      <td class="mono">${rec.created_at.substring(11, 19)}</td>
      <td><strong>${rec.actor}</strong></td>
      <td><span class="badge badge-accent">${rec.kind}</span></td>
      <td><code>${JSON.stringify(rec.payload).substring(0, 36)}...</code></td>
      <td><code>${rec.prev_hash.substring(0, 8)}...${rec.prev_hash.substring(60)}</code></td>
      <td><code class="c-green">${rec.hash.substring(0, 8)}...${rec.hash.substring(60)}</code></td>
    `;
    tbody.appendChild(tr);
  });
}

window.verifyAuditLedger = async function () {
  const banner = document.getElementById('ledger-verify-result');
  try {
    const sid = scenarioData ? scenarioData.session_id : 'SES_LIVE_CLEAN_BILL_APPROVE_FULL';
    const res = await fetch(`/api/ledger/verify?session_id=${sid}`);
    const data = await res.json();
    if (banner) {
      banner.hidden = false;
      if (data.valid) {
        banner.className = 'verify-banner ok';
        banner.innerHTML = `<strong>CRYPTOGRAPHIC CHAIN VERIFIED:</strong> ${data.message} Zero data tampering detected across all blocks.`;
      } else {
        banner.className = 'verify-banner bad';
        banner.innerHTML = `<strong>TAMPER DETECTION ALERT:</strong> ${data.message} Chain broken at Block #${data.broken_record_id}!`;
        const row = document.getElementById(`ledger-row-${data.broken_record_id}`);
        if (row) row.style.backgroundColor = 'rgba(192, 77, 65, 0.15)';
      }
    }
  } catch (err) {
    showToast(`Verification error: ${err.message}`);
  }
};

window.tamperAuditLedger = async function () {
  try {
    const sid = scenarioData ? scenarioData.session_id : 'SES_LIVE_CLEAN_BILL_APPROVE_FULL';
    const res = await fetch('/api/ledger/tamper', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sid })
    });
    const data = await res.json();
    showToast(`Block #${data.tampered_id} payload modified. Run 'Verify Cryptographic Chain' to observe detection.`, 5000);
    const lRes = await fetch(`/api/ledger?session_id=${sid}`);
    renderLedger(await lRes.json());
  } catch (err) {
    showToast(`Tamper error: ${err.message}`);
  }
};

// =========================================================================
// 10. REVENUE SHOCK SENSITIVITY TEST (PORTFOLIO RISK SLIDER)
// =========================================================================
document.getElementById('stress-shock-slider')?.addEventListener('input', async (e) => {
  const shockPercent = parseInt(e.target.value, 10);
  const label = document.getElementById('stress-shock-label');
  if (label) {
    label.textContent = shockPercent === 0 ? '0% (Normal Baseline)' : `-${shockPercent}% Daily Footfall Drop`;
  }

  try {
    const sid = scenarioData ? scenarioData.session_id : 'SES_LIVE_CLEAN_BILL_APPROVE_FULL';
    const res = await fetch('/api/stress/recalculate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sid,
        sales_drop_percent: shockPercent,
        base_p20_daily: scenarioData?.forecast_chart?.p20_daily ?? 18500,
        existing_edi: scenarioData?.forecast_chart?.existing_edi ?? 500,
        required_daily_edi: scenarioData?.decision?.daily_edi ?? 1953
      })
    });
    const data = await res.json();
    if (!res.ok) throw new Error("Could not recalculate cash flow.");
    const stressed = data;

    const p20El = document.getElementById('stress-p20-val');
    if (p20El) p20El.textContent = `${money(stressed.stressed_p20_daily)} / day`;

    const capEl = document.getElementById('stress-cap-val');
    if (capEl) capEl.textContent = `${money(stressed.safe_edi_cap)} / day`;

    const ratioEl = document.getElementById('stress-ratio-val');
    if (ratioEl) ratioEl.textContent = `${stressed.coverage_ratio}x`;

    const polEl = document.getElementById('stress-policy-val');
    if (polEl) {
      polEl.textContent = data.policy_action || 'MAINTAIN';
      polEl.className = data.policy_action === 'MAINTAIN' ? 'c-green' : 'c-amber';
    }
  } catch (err) {
    console.error(err);
  }
});

// =========================================================================
// 11. POLICY ASSISTANT CHAT
// =========================================================================
window.sendChatMessage = async function () {
  const input = document.getElementById('chat-input');
  if (!input || !input.value.trim()) return;
  const question = input.value.trim();
  input.value = '';

  const thread = document.getElementById('chat-messages');
  if (thread) {
    const userDiv = document.createElement('div');
    userDiv.style.cssText = 'background: rgba(139, 74, 54, 0.1); padding: 10px 14px; border-radius: 8px; font-size: 0.85rem; align-self: flex-end; max-width: 85%;';
    userDiv.textContent = `You: ${question}`;
    thread.appendChild(userDiv);
    thread.scrollTop = thread.scrollHeight;
  }

  try {
    const res = await fetch('/api/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query: question,
        language: currentLanguage,
        decision_id: scenarioData?.option_decision_id || null,
        payment_date: qrPaymentDate.value || null,
        reserve_paise: Math.round(Math.max(0, Number(shopReserve.value) || 0) * 100)
      })
    });
    const data = await res.json();

    if (thread) {
      const botDiv = document.createElement('div');
      botDiv.style.cssText = 'background: rgba(255, 255, 255, 0.85); padding: 10px 14px; border-radius: 8px; font-size: 0.85rem; max-width: 85%;';
      botDiv.textContent = res.ok ? data.reply : (typeof data.detail === "string" ? data.detail : "Could not answer. Try again.");
      thread.appendChild(botDiv);
      thread.scrollTop = thread.scrollHeight;
    }
  } catch (err) {
    console.error(err);
  }
};

document.getElementById('chat-input')?.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') window.sendChatMessage();
});

// =========================================================================
// 12. FILE UPLOAD & REAL GEMINI EXTRACTION HANDLERS
// =========================================================================
function handleFileSelection(file, context = 'home') {
  if (!file) return;
  currentSelectedFile = file;

  const wrapEl = document.getElementById(`${context}-selected-file-wrap`);
  const nameEl = document.getElementById(`${context}-selected-filename`);
  if (wrapEl && nameEl) {
    nameEl.textContent = file.name;
    wrapEl.style.display = 'block';
  }
  showToast(`Selected "${file.name}". Click "Process Invoice" to scan & underwrite.`);
}

let invoiceUploadVersion = 0;
window.processSelectedFile = async function (context = 'home') {
  if (!currentSelectedFile) {
    showToast('Please select an invoice file first.');
    return;
  }

  const version = ++invoiceUploadVersion;
  const file = currentSelectedFile;
  scenarioData = null;
  window.activeUploadedInvoice = null;
  const status = document.getElementById('invoice-processing-status');
  status.textContent = 'Reading your invoice…';
  status.hidden = false;
  for (const id of ['card-step-verification', 'card-step-underwriting', 'qr-savings-controls',
    'qr-payment-monitor', 'card-step-soundbox', 'card-step-repayment']) {
    document.getElementById(id).hidden = true;
  }
  savingsReview = null;
  optionApproval = null;
  window.navToView('workspace', 'panel-decisioning');

  const reader = new FileReader();
  reader.onerror = () => {
    if (version === invoiceUploadVersion) status.textContent = 'Could not read the file. Choose the invoice again.';
  };
  reader.onload = async function (e) {
    const base64Data = e.target.result.split(',')[1];
    try {
      const runResponse = await fetch('/api/workflow-runs', { method: 'POST' });
      if (!runResponse.ok) throw new Error('Could not start the invoice trace.');
      const { run_id } = await runResponse.json();
      if (version !== invoiceUploadVersion) return;
      watchWorkflow(run_id);
      const res = await fetch('/api/invoice/process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          run_id,
          session_id: `SES_UPLOAD_${Date.now()}`,
          file_name: file.name,
          file_bytes_base64: base64Data,
        })
      });
      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || 'Invoice processing failed. Please upload a clearer copy.');
      }
      const invoice = await res.json();
      if (version !== invoiceUploadVersion) return;
      scenarioData = invoice;
      window.activeUploadedInvoice = scenarioData;

      renderProcessedInvoice(scenarioData);
      showToast(`Extraction complete: ${scenarioData?.invoice?.supplier_name || 'Bill extracted'} (${money(scenarioData?.invoice?.total_amount)})`);
    } catch (err) {
      if (version === invoiceUploadVersion) status.textContent = err.message;
    }
  };
  reader.readAsDataURL(file);
};

document.getElementById('home-file-input')?.addEventListener('change', (e) => {
  if (e.target.files && e.target.files.length > 0) handleFileSelection(e.target.files[0], 'home');
});

document.getElementById('workspace-file-input')?.addEventListener('change', (e) => {
  if (e.target.files && e.target.files.length > 0) {
    handleFileSelection(e.target.files[0], 'home');
    window.processSelectedFile('home');
  }
});

// =========================================================================
// 13. BOOTSTRAP INITIAL STATE
// =========================================================================
window.addEventListener('DOMContentLoaded', () => {
  // Pre-load default standard bill for ready inspection in workspace
  window.loadScenario('clean_bill_approve_full');

  // ALWAYS start on public homepage as requested
  window.navToView('home');
});
