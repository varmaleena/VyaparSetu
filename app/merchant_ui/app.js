// VyaparSetu Enterprise Application Logic
// Public Home Landing Page + Enterprise Workspace with Google ADK Agent Graph & Sarvam AI Voice

let currentScenario = null;
let scenarioData = null;
let currentLanguage = 'te';
let streamInterval = null;
let streamSpeedMs = 2000;
let agentGraphData = null;
let selectedNodeId = 'intake';
let currentAudioPlayer = null;

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
window.navToView = function(view, targetPanel = 'panel-decisioning') {
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

window.scrollToSection = function(id) {
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
  'panel-blockchain': 'Cryptographic Audit Blockchain Ledger',
  'panel-risk': 'Portfolio Risk & Sensitivity Stress-Test',
  'panel-policy': 'Policy & Regulatory Assistant',
  'panel-settings': 'Voice & AI Settings (Sarvam AI 500 Credits)',
};

window.switchWorkspacePanel = function(panelId) {
  // Hide all panels
  document.querySelectorAll('.view-panel').forEach(p => p.classList.remove('active'));
  const target = document.getElementById(panelId);
  if (target) target.classList.add('active');

  // Update topbar title
  const titleEl = document.getElementById('current-stage-title');
  if (titleEl && panelTitles[panelId]) {
    titleEl.textContent = panelTitles[panelId];
  }

  // Update active sidebar item
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
  showToast(`Language set to ${lang === 'te' ? 'Telugu' : lang === 'hi' ? 'Hindi' : 'English'}`);
}

document.getElementById('home-lang-select')?.addEventListener('change', (e) => setAppLanguage(e.target.value));
document.getElementById('stage-lang-select')?.addEventListener('change', (e) => setAppLanguage(e.target.value));

// =========================================================================
// 4. INVOICE SCENARIO SELECTION & UNDERWRITING PIPELINE
// =========================================================================
window.selectInvoiceScenario = function(key) {
  window.navToView('workspace', 'panel-decisioning');
  window.loadScenario(key);
};

window.loadScenario = async function(key) {
  currentScenario = key;

  document.querySelectorAll('.scenario-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.scenarioKey === key);
  });

  const tag = document.getElementById('active-invoice-tag');
  if (tag) {
    if (key === 'clean_bill_approve_full') tag.textContent = 'Sri Balaji Distributors (₹40,000 · Clean Bill)';
    else if (key === 'weaker_merchant_partial') tag.textContent = 'Sri Balaji Distributors (₹40,000 · Constrained Kirana)';
    else tag.textContent = 'Unverified Bill (Invalid GSTIN)';
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
    }, 800);
  } catch (err) {
    console.error(err);
    showToast(`Error: ${err.message}`);
  }
};

function renderProcessedInvoice(data) {
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
  setVal('arb-pay-amt', money(dec.approved_amount || inv.total_amount));
  setVal('arb-interest-cost', `+${money(dec.financing_cost || 0)}`);
  setVal('arb-net-benefit', `+${money(dec.net_benefit || 0)}`);
  setVal('arb-daily-edi', dec.daily_edi ? `${money(dec.daily_edi)} / day` : 'N/A');

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
  agentGraphData = data.agent_graph_nodes || [];
  inspectAgentNode('policy');
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
// 5. SARVAM AI VOICE INTEGRATION (500 CREDITS ENGINE)
// =========================================================================
window.saveSarvamKey = function() {
  const inp = document.getElementById('sarvam-api-key-input');
  if (inp && inp.value.trim()) {
    localStorage.setItem('sarvam_api_key', inp.value.trim());
    showToast('Sarvam API Key saved! 500 Credits ready for TTS.');
  } else {
    localStorage.removeItem('sarvam_api_key');
    showToast('Sarvam API Key cleared.');
  }
};

window.playVoiceAudio = async function() {
  const scriptText = document.getElementById('voice-script-text')?.textContent?.replace(/^"|"$/g, '') ||
    'Sri Ravi Kirana Store. Your supplier payment of Rupees 38,800 is ready for confirmation.';
  const speaker = document.getElementById('sarvam-speaker-select')?.value || 'meera';
  const apiKey = localStorage.getItem('sarvam_api_key') || '';

  const waveform = document.getElementById('soundbox-waveform');
  if (waveform) waveform.classList.add('waveform-active');

  showToast('Generating Sarvam AI voice audio...');

  try {
    const res = await fetch('/api/voice/sarvam-tts', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(apiKey ? { 'x-sarvam-key': apiKey } : {})
      },
      body: JSON.stringify({
        text: scriptText,
        language: currentLanguage,
        speaker: speaker,
        api_key: apiKey || null
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
      showToast(`Playing Sarvam AI Bulbul v1 (${currentLanguage.toUpperCase()})`);
    } else {
      // Fallback to browser SpeechSynthesis
      speakBrowserUtterance(scriptText);
      setTimeout(() => {
        if (waveform) waveform.classList.remove('waveform-active');
      }, 5000);
      if (!apiKey) {
        showToast('Playing browser voice. Add your Sarvam API Key in Settings to use your 500 credits!');
      } else {
        showToast('Sarvam TTS returned fallback; playing via browser synthesis.');
      }
    }
  } catch (err) {
    console.error(err);
    speakBrowserUtterance(scriptText);
    setTimeout(() => {
      if (waveform) waveform.classList.remove('waveform-active');
    }, 5000);
  }
};

window.testSarvamVoice = function() {
  const samplePhrase = currentLanguage === 'te'
    ? 'నమస్కారం, వ్యాపార్ సేతు పేటీఎం సౌండ్‌బాక్స్ వాయిస్ సేవలు సిద్ధంగా ఉన్నాయి.'
    : currentLanguage === 'hi'
    ? 'नमस्ते, व्यापार सेतु पेटीएम साउंडबॉक्स वॉयस सेवाएं तैयार हैं।'
    : 'Hello, VyaparSetu Paytm Soundbox voice service is operational.';

  const speaker = document.getElementById('sarvam-speaker-select')?.value || 'meera';
  const apiKey = localStorage.getItem('sarvam_api_key') || '';

  fetch('/api/voice/sarvam-tts', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(apiKey ? { 'x-sarvam-key': apiKey } : {})
    },
    body: JSON.stringify({
      text: samplePhrase,
      language: currentLanguage,
      speaker: speaker,
      api_key: apiKey || null
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
window.confirmConsent = async function(utterance) {
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
      // Disburse payment directly to payee
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

      // Show receipt card & move to step 5 panel
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

      // Activate PaymentExecution node on graph
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
window.inspectAgentNode = function(nodeId) {
  selectedNodeId = nodeId;

  document.querySelectorAll('.agent-node rect').forEach(r => {
    r.style.stroke = 'rgba(235, 201, 190, 0.9)';
    r.style.strokeWidth = '1.5px';
  });
  const selNode = document.getElementById(`node-${nodeId}`);
  if (selNode) {
    const rect = selNode.querySelector('rect');
    if (rect) {
      rect.style.stroke = 'var(--primary-btn)';
      rect.style.strokeWidth = '2.5px';
    }
  }

  const nodeInfo = (agentGraphData || []).find(n => n.id === nodeId) || getFallbackNodeInfo(nodeId);

  document.getElementById('inspector-title').textContent = nodeInfo.name;
  document.getElementById('inspector-status-badge').textContent = nodeInfo.status || 'Active';
  document.getElementById('inspector-status-badge').className = `badge ${nodeInfo.status === 'COMPLETED' ? 'badge-green' : nodeInfo.status === 'FAILED' ? 'badge-red' : 'badge-accent'}`;
  document.getElementById('inspector-role').textContent = nodeInfo.role;
  document.getElementById('inspector-model').textContent = nodeInfo.model || 'gemini-2.5-flash';
  document.getElementById('inspector-latency').textContent = nodeInfo.latency || '0.24s';
  document.getElementById('inspector-payload').textContent = JSON.stringify({
    agent_id: nodeInfo.id,
    framework: 'Google ADK',
    input_state: nodeInfo.input || {},
    output_state: nodeInfo.output || {},
  }, null, 2);
};

function getFallbackNodeInfo(id) {
  const map = {
    intake: { id: 'intake', name: 'InvoiceIntakeAgent', role: 'Validates file headers, cryptographic checksum, and GCS object lifecycle.', model: 'local-verifier', latency: '0.34s', input: { file: 'invoice.pdf' }, output: { verified: true } },
    vision: { id: 'vision', name: 'GeminiVisionAgent', role: 'Multimodal extraction of commercial invoice entities and discount clauses.', model: 'gemini-2.5-flash', latency: '1.38s', input: { image: 'raw_bytes' }, output: { supplier: 'Sri Balaji Distributors', gstin: '36AAAAA0000A1Z3', amount: 40000, discount: '3%' } },
    supplier_risk: { id: 'supplier_risk', name: 'SupplierVerificationAgent', role: 'Verifies GSTIN Modulo-36 statutory checksum and bank account name similarity.', model: 'checksum-engine', latency: '0.18s', input: { gstin: '36AAAAA0000A1Z3' }, output: { checksum: 'VALID', bank_match: 'MATCHED' } },
    duplicate_fraud: { id: 'duplicate_fraud', name: 'DuplicateFraudAgent', role: 'Computes SHA-256 invoice fingerprint to stop double-financing attacks.', model: 'sha256-hasher', latency: '0.09s', input: { fingerprint: 'sha256(supplier+amount)' }, output: { duplicate: false } },
    cashflow_p20: { id: 'cashflow_p20', name: 'CashflowAffordabilityAgent', role: 'Calculates conservative 20th percentile cashflow floor over 90-day transactions.', model: 'p20-quantile-estimator', latency: '0.29s', input: { history_days: 90 }, output: { p20_floor: 18500, safe_cap: 4125 } },
    arbitrage: { id: 'arbitrage', name: 'DiscountArbitrageAgent', role: 'Compares early cash discount savings against short-term financing costs.', model: 'math-evaluator', latency: '0.06s', input: { discount: 1200, interest: 268 }, output: { net_profit: 932 } },
    policy: { id: 'policy', name: 'PolicyDecisionAgent', role: 'Deterministic credit policy matrix determining approval boundaries.', model: 'policy-matrix', latency: '0.11s', input: { safe_cap: 4125, proposed_edi: 1953 }, output: { verdict: 'APPROVE_FULL' } },
    voice_consent: { id: 'voice_consent', name: 'VoiceConsentAgent', role: 'Generates localized Soundbox 4.0 script and locks decision hash.', model: 'gemini-2.5-flash-audio', latency: '0.22s', input: { hash: 'sha256(...)' }, output: { soundbox_script_ready: true } },
    payment_exec: { id: 'payment_exec', name: 'PaymentExecutionAgent', role: 'Executes idempotent payout rail directly to verified supplier account.', model: 'idempotent-rail', latency: '0.45s', input: { payee: 'Sri Balaji Distributors' }, output: { status: 'DISBURSED' } },
    settlement_loop: { id: 'settlement_loop', name: 'SettlementLoopAgent', role: 'Watches live daily UPI QR customer settlements and splits EDI.', model: 'settlement-hook', latency: 'live', input: { daily_edi: 1953 }, output: { coverage_ratio: 2.34 } },
  };
  return map[id] || { id, name: id, role: 'Agent Worker', model: 'Google ADK', latency: '—', input: {}, output: {} };
}

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
        sales_shock_percent: shockPercent,
        proposed_daily_edi: scenarioData?.decision?.daily_edi || 1953
      })
    });
    const data = await res.json();
    const stressed = data.stressed_sizing || {};

    const p20El = document.getElementById('stress-p20-val');
    if (p20El) p20El.textContent = `${money(stressed.stressed_p20_daily_mean)} / day`;

    const capEl = document.getElementById('stress-cap-val');
    if (capEl) capEl.textContent = `${money(stressed.safe_daily_deduction_cap)} / day`;

    const ratioEl = document.getElementById('stress-ratio-val');
    if (ratioEl) ratioEl.textContent = `${stressed.coverage_ratio}x`;

    const polEl = document.getElementById('stress-policy-val');
    if (polEl) {
      polEl.textContent = data.policy_status || 'MAINTAIN';
      polEl.className = data.policy_status === 'MAINTAIN' ? 'c-green' : 'c-amber';
    }
  } catch (err) {
    console.error(err);
  }
});

// =========================================================================
// 11. POLICY ASSISTANT CHAT
// =========================================================================
window.sendChatMessage = async function() {
  const input = document.getElementById('chat-input');
  if (!input || !input.value.trim()) return;
  const question = input.value.trim();
  input.value = '';

  const thread = document.getElementById('chat-messages');
  if (thread) {
    const userDiv = document.createElement('div');
    userDiv.style.cssText = 'background: rgba(139, 74, 54, 0.1); padding: 10px 14px; border-radius: 8px; font-size: 0.85rem; align-self: flex-end; max-width: 85%;';
    userDiv.innerHTML = `<strong>You:</strong> ${question}`;
    thread.appendChild(userDiv);
    thread.scrollTop = thread.scrollHeight;
  }

  try {
    const sid = scenarioData ? scenarioData.session_id : 'SES_LIVE';
    const res = await fetch('/api/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sid,
        question: question
      })
    });
    const data = await res.json();

    if (thread) {
      const botDiv = document.createElement('div');
      botDiv.style.cssText = 'background: rgba(255, 255, 255, 0.85); padding: 10px 14px; border-radius: 8px; font-size: 0.85rem; max-width: 85%;';
      botDiv.innerHTML = `<strong>Policy Agent:</strong> ${data.answer}`;
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
let currentSelectedFile = null;

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

window.processSelectedFile = async function(context = 'home') {
  if (!currentSelectedFile) {
    showToast('Please select an invoice file first.');
    return;
  }

  showToast(`Scanning "${currentSelectedFile.name}" with Gemini 2.5 Vision...`);
  window.navToView('workspace', 'panel-decisioning');

  // Progress tag
  const stepTag = document.getElementById('merchant-flow-step-tag');
  if (stepTag) stepTag.textContent = 'Step 2: Gemini Vision Extraction...';

  // Read file as base64
  const reader = new FileReader();
  reader.onload = async function(e) {
    const base64Data = e.target.result.split(',')[1];
    try {
      const res = await fetch('/api/invoice/process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: `SES_UPLOAD_${Date.now()}`,
          file_name: currentSelectedFile.name,
          file_bytes_base64: base64Data,
        })
      });
      if (!res.ok) throw new Error('Invoice processing pipeline failed');
      scenarioData = await res.json();

      renderProcessedInvoice(scenarioData);
      showToast(`Gemini extraction complete: ${scenarioData?.invoice?.supplier_name || 'Bill extracted'}`);
    } catch (err) {
      console.error(err);
      showToast(`Error: ${err.message}`);
    }
  };
  reader.readAsDataURL(currentSelectedFile);
};

document.getElementById('home-file-input')?.addEventListener('change', (e) => {
  if (e.target.files && e.target.files.length > 0) handleFileSelection(e.target.files[0], 'home');
});

document.getElementById('workspace-file-input')?.addEventListener('change', (e) => {
  if (e.target.files && e.target.files.length > 0) handleFileSelection(e.target.files[0], 'home');
});

// =========================================================================
// 13. BOOTSTRAP INITIAL STATE
// =========================================================================
window.addEventListener('DOMContentLoaded', () => {
  // Restore saved Sarvam key if exists
  const savedKey = localStorage.getItem('sarvam_api_key');
  const keyInput = document.getElementById('sarvam-api-key-input');
  if (keyInput && savedKey) {
    keyInput.value = savedKey;
  }

  // Pre-load default standard bill for ready inspection
  window.loadScenario('clean_bill_approve_full');
});
