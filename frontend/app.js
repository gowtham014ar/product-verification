/**
 * Product Verification — frontend JS
 * Talks to the API Gateway at /api/...
 * Change API_BASE if running gateway on a different port.
 */

const API_BASE = 'http://localhost:8000';

// ── State ──────────────────────────────────────────────────────────────────
const state = {
  token: localStorage.getItem('pv_token') || null,
  userRole: localStorage.getItem('pv_role') || null,
  userId: localStorage.getItem('pv_user_id') || null,
  userEmail: localStorage.getItem('pv_email') || null,
};

// ── API helper ─────────────────────────────────────────────────────────────
async function api(method, path, body = null, requiresAuth = false) {
  const headers = { 'Content-Type': 'application/json' };
  if (requiresAuth && state.token) headers['Authorization'] = `Bearer ${state.token}`;

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = data.detail;
    const message = typeof detail === 'string'
      ? detail
      : (detail ? JSON.stringify(detail) : `HTTP ${res.status}`);
    throw new Error(message);
  }
  return data;
}

// ── Toast ──────────────────────────────────────────────────────────────────
function toast(message, type = 'info', duration = 3500) {
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.textContent = message;
  document.getElementById('toastContainer').appendChild(el);
  setTimeout(() => el.remove(), duration);
}

// ── Spinner helper ─────────────────────────────────────────────────────────
function setLoading(btn, loading, label = null) {
  if (loading) {
    btn.dataset.originalText = btn.innerHTML;
    btn.innerHTML = `<span class="spinner"></span>${label || 'Working…'}`;
    btn.disabled = true;
  } else {
    btn.innerHTML = btn.dataset.originalText || btn.innerHTML;
    btn.disabled = false;
  }
}

// ── Form message helper ────────────────────────────────────────────────────
function setMsg(id, message, type = 'error') {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = message;
  el.className = `form-msg ${type}`;
}

// ── Auth state ─────────────────────────────────────────────────────────────
function applyAuthState() {
  const loggedIn = !!state.token;
  document.getElementById('showLoginBtn').style.display = loggedIn ? 'none' : '';
  document.getElementById('userPill').style.display = loggedIn ? 'flex' : 'none';
  if (loggedIn) {
    document.getElementById('userLabel').textContent = `${state.userEmail} · ${state.userRole}`;
  }
  const addCard = document.getElementById('addMfgCard');
  if (addCard) addCard.style.display = state.userRole === 'admin' ? '' : 'none';
}

function saveAuth(token, role, userId, email) {
  state.token = token; state.userRole = role;
  state.userId = userId; state.userEmail = email;
  localStorage.setItem('pv_token', token);
  localStorage.setItem('pv_role', role);
  localStorage.setItem('pv_user_id', userId);
  localStorage.setItem('pv_email', email);
  applyAuthState();
}

function clearAuth() {
  state.token = null; state.userRole = null;
  state.userId = null; state.userEmail = null;
  ['pv_token','pv_role','pv_user_id','pv_email'].forEach(k => localStorage.removeItem(k));
  applyAuthState();
}

// ── Modal ──────────────────────────────────────────────────────────────────
function openAuthModal() { document.getElementById('authModal').style.display = 'flex'; }
function closeAuthModal() { document.getElementById('authModal').style.display = 'none'; }

document.getElementById('showLoginBtn').addEventListener('click', openAuthModal);
document.getElementById('closeAuthModal').addEventListener('click', closeAuthModal);
document.getElementById('authModal').addEventListener('click', e => {
  if (e.target === e.currentTarget) closeAuthModal();
});
document.getElementById('logoutBtn').addEventListener('click', () => { clearAuth(); toast('Signed out', 'info'); });

// Modal tabs
document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    const target = tab.dataset.tab;
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById('loginPane').style.display    = target === 'login'    ? 'flex' : 'none';
    document.getElementById('registerPane').style.display = target === 'register' ? 'flex' : 'none';
    document.getElementById('loginPane').classList.toggle('active', target === 'login');
  });
});

// ── Login form ─────────────────────────────────────────────────────────────
document.getElementById('loginPane').addEventListener('submit', async e => {
  e.preventDefault();
  const btn = e.target.querySelector('button[type=submit]');
  setMsg('loginMsg', '');
  setLoading(btn, true, 'Signing in…');
  try {
    const emailVal = document.getElementById('loginEmail').value.trim();
    const data = await api('POST', '/api/auth/login', {
      email: emailVal,
      password: document.getElementById('loginPassword').value,
    });
    saveAuth(data.access_token, data.role, data.user_id, emailVal);
    closeAuthModal();
    toast(`Welcome back! Signed in as ${data.role}.`, 'success');
  } catch (err) {
    setMsg('loginMsg', err.message, 'error');
  } finally {
    setLoading(btn, false);
  }
});

// ── Register form ──────────────────────────────────────────────────────────
document.getElementById('registerPane').addEventListener('submit', async e => {
  e.preventDefault();
  const btn = e.target.querySelector('button[type=submit]');
  setMsg('registerMsg', '');
  setLoading(btn, true, 'Creating account…');
  try {
    await api('POST', '/api/auth/register', {
      email: document.getElementById('regEmail').value.trim(),
      password: document.getElementById('regPassword').value,
      full_name: document.getElementById('regName').value.trim(),
      wallet_address: document.getElementById('regWallet').value.trim() || null,
    });
    setMsg('registerMsg', 'Account created — sign in now.', 'success');
    toast('Account created!', 'success');
  } catch (err) {
    setMsg('registerMsg', err.message, 'error');
  } finally {
    setLoading(btn, false);
  }
});

// ── Page navigation ────────────────────────────────────────────────────────
const pages = {
  verify:        document.getElementById('pageVerify'),
  register:      document.getElementById('pageRegister'),
  manufacturers: document.getElementById('pageManufacturers'),
  network:       document.getElementById('pageNetwork'),
};

function showPage(name) {
  Object.entries(pages).forEach(([k, el]) => el.style.display = k === name ? 'block' : 'none');
  document.querySelectorAll('.page-tab').forEach(t => t.classList.toggle('active', t.dataset.page === name));
  if (name === 'manufacturers') loadManufacturers();
  if (name === 'network')       loadNetworkInfo();
}

document.querySelectorAll('.page-tab').forEach(tab => {
  tab.addEventListener('click', () => showPage(tab.dataset.page));
});

// ── Verify product ─────────────────────────────────────────────────────────
document.getElementById('verifyForm').addEventListener('submit', async e => {
  e.preventDefault();
  const btn = document.getElementById('verifyBtn');
  const result = document.getElementById('verifyResult');
  result.style.display = 'none';
  setLoading(btn, true, 'Checking blockchain…');

  try {
    const data = await api('POST', '/api/blockchain/products/verify', {
      product_id:    document.getElementById('vProductId').value.trim(),
      serial_number: document.getElementById('vSerial').value.trim(),
      model:         document.getElementById('vModel').value.trim(),
      batch:         document.getElementById('vBatch').value.trim(),
    });

    const authentic = data.is_authentic;
    result.className = `verify-result ${authentic ? 'authentic' : 'fake'}`;
    result.style.display = 'flex';

    document.getElementById('resultIcon').textContent = authentic ? '✅' : '❌';
    document.getElementById('resultVerdict').textContent = authentic
      ? 'Registered record matches'
      : 'No matching active record';

    const details = [];
    if (data.manufacturer && data.manufacturer !== '0x0000000000000000000000000000000000000000') {
      details.push(`Manufacturer: ${data.manufacturer}`);
    }
    if (data.registered_at) {
      details.push(`Registered: ${new Date(data.registered_at * 1000).toLocaleString()}`);
    }
    details.push(`Active: ${data.active ? 'Yes' : 'No (recalled/deactivated)'}`);
    if (data.product_hash) {
      details.push(`Hash: ${data.product_hash.slice(0, 16)}…`);
    }
    if (authentic) {
      details.push('A copied label with the same details would match too.');
    }

    document.getElementById('resultDetails').innerHTML = details.map(d => `<span>${d}</span>`).join('');
  } catch (err) {
    toast(`Verification error: ${err.message}`, 'error');
  } finally {
    setLoading(btn, false);
  }
});

// ── MetaMask ───────────────────────────────────────────────────────────────
async function connectWallet() {
  if (!window.ethereum) {
    throw new Error('MetaMask is required. Install it, then try again. The private key never leaves the wallet.');
  }
  const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
  if (!accounts || !accounts.length) throw new Error('MetaMask did not return an account.');
  return accounts[0];
}

async function switchToChain(chainId) {
  const chainHex = '0x' + Number(chainId).toString(16);
  const current = await window.ethereum.request({ method: 'eth_chainId' });
  if (String(current).toLowerCase() === chainHex.toLowerCase()) return;
  try {
    await window.ethereum.request({
      method: 'wallet_switchEthereumChain',
      params: [{ chainId: chainHex }],
    });
  } catch (err) {
    if (err && err.code === 4902 && Number(chainId) === 31337) {
      await window.ethereum.request({
        method: 'wallet_addEthereumChain',
        params: [{
          chainId: chainHex,
          chainName: 'Anvil',
          rpcUrls: ['http://127.0.0.1:8545'],
          nativeCurrency: { name: 'Ether', symbol: 'ETH', decimals: 18 },
        }],
      });
      return;
    }
    throw new Error((err && err.message) || 'Switch MetaMask to the network configured for this app.');
  }
}

async function sendPreparedTx(prepared, from) {
  await switchToChain(prepared.chain_id);
  return window.ethereum.request({
    method: 'eth_sendTransaction',
    params: [{ from, to: prepared.to, data: prepared.data, value: '0x0' }],
  });
}

async function confirmWhenMined(path, body) {
  let last = 'Transaction not yet mined';
  for (let attempt = 0; attempt < 40; attempt++) {
    try {
      return await api('POST', path, body, true);
    } catch (err) {
      last = err.message || String(err);
      if (!/not yet mined|not found|pending/i.test(last)) throw err;
      await new Promise(resolve => setTimeout(resolve, 3000));
    }
  }
  throw new Error(last);
}

// ── Register product ───────────────────────────────────────────────────────
document.getElementById('registerProductForm').addEventListener('submit', async e => {
  e.preventDefault();
  if (!state.token) { openAuthModal(); return; }

  const btn = document.getElementById('registerProductBtn');
  setMsg('registerProductMsg', '');
  setLoading(btn, true, 'Connecting MetaMask…');

  const payload = {
    product_id:    document.getElementById('rpProductId').value.trim(),
    name:          document.getElementById('rpName').value.trim(),
    serial_number: document.getElementById('rpSerial').value.trim(),
    model:         document.getElementById('rpModel').value.trim(),
    batch:         document.getElementById('rpBatch').value.trim(),
    description:   document.getElementById('rpDescription').value.trim() || null,
  };

  try {
    const wallet = await connectWallet();
    payload.manufacturer_wallet = wallet;

    setLoading(btn, true, 'Saving to database…');
    try {
      await api('POST', '/api/products/', payload, true);
      setMsg('registerProductMsg', 'Saved to the catalog. Approve the transaction in MetaMask…', 'success');
    } catch (dbErr) {
      const dbErrStr = (dbErr && dbErr.message) ? dbErr.message.toLowerCase() : '';
      if (!(dbErrStr.includes('already exists') || dbErrStr.includes('409'))) throw dbErr;
      const existing = await api('GET', `/api/products/${encodeURIComponent(payload.product_id)}`);
      if (existing.is_on_chain) {
        throw new Error('This product is already linked to a confirmed transaction.');
      }
      if (existing.created_by && state.userId && existing.created_by !== state.userId) {
        throw new Error('This product id belongs to another account.');
      }
      setMsg('registerProductMsg', 'Catalog row already exists. Continuing with MetaMask…', 'info');
    }

    setLoading(btn, true, 'Waiting for MetaMask…');
    const prepared = await api('POST', '/api/blockchain/products/prepare', {
      product_id: payload.product_id,
      serial_number: payload.serial_number,
      model: payload.model,
      batch: payload.batch,
      from_address: wallet,
    }, true);

    const txHash = await sendPreparedTx(prepared, wallet);
    setLoading(btn, true, 'Waiting for the receipt…');
    setMsg('registerProductMsg', `Transaction ${txHash.slice(0, 18)}… submitted. Linking it to the catalog…`, 'info');

    await confirmWhenMined(`/api/products/${encodeURIComponent(payload.product_id)}/mark-on-chain`, {
      tx_hash: txHash,
    });

    setMsg('registerProductMsg', `Registered on-chain and linked in the catalog. TX: ${txHash.slice(0, 18)}…`, 'success');
    toast('Product registered on-chain', 'success', 5000);
    e.target.reset();
  } catch (err) {
    setMsg('registerProductMsg', err.message, 'error');
    toast(`Error: ${err.message}`, 'error');
  } finally {
    setLoading(btn, false);
  }
});

document.getElementById('recallForm').addEventListener('submit', async e => {
  e.preventDefault();
  if (!state.token) { openAuthModal(); return; }
  const btn = document.getElementById('recallBtn');
  const productId = document.getElementById('recallProductId').value.trim();
  setMsg('recallMsg', '');
  setLoading(btn, true, 'Connecting MetaMask…');
  try {
    const wallet = await connectWallet();
    const prepared = await api('POST', '/api/blockchain/products/deactivate-calldata', {
      product_id: productId,
    }, true);
    setLoading(btn, true, 'Waiting for MetaMask…');
    const txHash = await sendPreparedTx(prepared, wallet);
    setLoading(btn, true, 'Waiting for the receipt…');
    await confirmWhenMined(`/api/products/${encodeURIComponent(productId)}/confirm-deactivation`, {
      tx_hash: txHash,
    });
    setMsg('recallMsg', `Recalled on-chain and in the catalog. TX: ${txHash.slice(0, 18)}…`, 'success');
    toast('Product recalled', 'success', 5000);
    e.target.reset();
  } catch (err) {
    setMsg('recallMsg', err.message, 'error');
    toast(`Error: ${err.message}`, 'error');
  } finally {
    setLoading(btn, false);
  }
});

// ── Load manufacturers ─────────────────────────────────────────────────────
async function loadManufacturers() {
  const container = document.getElementById('mfgTable');
  container.innerHTML = '<div class="empty-state">Loading…</div>';
  try {
    const data = await api('GET', '/api/blockchain/manufacturers');
    if (!data.length) {
      container.innerHTML = '<div class="empty-state">No manufacturers registered on-chain yet.</div>';
      return;
    }
    container.innerHTML = `
      <table>
        <thead><tr>
          <th>Name</th><th>Wallet</th><th>Added</th><th>Status</th>
        </tr></thead>
        <tbody>
          ${data.map(m => `
            <tr>
              <td>${m.name}</td>
              <td class="mono ellipsis">${m.wallet}</td>
              <td>${m.added_at ? new Date(m.added_at * 1000).toLocaleDateString() : '—'}</td>
              <td><span class="${m.active ? 'pill-active' : 'pill-inactive'}">${m.active ? 'Active' : 'Revoked'}</span></td>
            </tr>
          `).join('')}
        </tbody>
      </table>`;
  } catch (err) {
    container.innerHTML = `<div class="empty-state" style="color:var(--red)">${err.message}</div>`;
  }
}

document.getElementById('refreshMfgBtn').addEventListener('click', loadManufacturers);

// ── Add manufacturer (unified: PostgreSQL → Blockchain) ────────────────────
(function () {
  // Cached payload for blockchain retry after a partial failure
  let _retryPayload = null;

  function mfgSetStep(step1State, step2State, step3State) {
    const map = { idle: '', done: 'mfg-step-done', active: 'mfg-step-active', error: 'mfg-step-error' };
    const el1 = document.getElementById('mfgStepEl1');
    const el2 = document.getElementById('mfgStepEl2');
    const el3 = document.getElementById('mfgStepEl3');
    if (el1) el1.className = 'step ' + (map[step1State] || '');
    if (el2) el2.className = 'step ' + (map[step2State] || '');
    if (el3) el3.className = 'step ' + (map[step3State] || '');
  }

  function mfgInputs(disabled) {
    document.querySelectorAll('#addMfgForm input').forEach(i => i.disabled = disabled);
  }

  async function doBlockchainStep(payload) {
    const ownerAccount = await connectWallet();
    let prepared;
    try {
      prepared = await api('POST', '/api/blockchain/manufacturers/prepare', payload, true);
    } catch (err) {
      if (/already an active manufacturer/i.test(err.message || '')) {
        return { tx_hash: 'already_whitelisted' };
      }
      throw err;
    }
    if (prepared.owner && ownerAccount.toLowerCase() !== String(prepared.owner).toLowerCase()) {
      throw new Error(
        `MetaMask is ${ownerAccount}. Connect the contract owner ${prepared.owner} before whitelisting.`
      );
    }
    const txHash = await sendPreparedTx(prepared, ownerAccount);
    return confirmWhenMined('/api/blockchain/manufacturers/confirm', {
      tx_hash: txHash,
      wallet_address: payload.wallet_address,
    });
  }

  // ── Main submit ─────────────────────────────────────────────────────────
  document.getElementById('addMfgForm').addEventListener('submit', async e => {
    e.preventDefault();
    if (!state.token) { openAuthModal(); return; }

    const btn = document.getElementById('addMfgSubmitBtn');
    const retryPanel = document.getElementById('mfgRetryPanel');
    setMsg('addMfgMsg', '');
    retryPanel.style.display = 'none';
    _retryPayload = null;

    const wallet   = document.getElementById('mfgWallet').value.trim();
    const fullName = document.getElementById('mfgName').value.trim();
    const mfgId    = document.getElementById('mfgId').value.trim();

    mfgSetStep('active', 'idle', 'idle');
    setLoading(btn, true, 'Step 1/2 — Creating login account…');
    mfgInputs(true);

    try {
      await api('POST', '/api/auth/manufacturers', {
        email:          document.getElementById('mfgEmail').value.trim(),
        password:       document.getElementById('mfgPassword').value,
        full_name:      fullName,
        wallet_address: wallet,
      }, true);
      setMsg('addMfgMsg', 'Account created. Approve addManufacturer in MetaMask…', 'success');
    } catch (err) {
      const errMsg = (err && err.message) ? err.message.toLowerCase() : '';
      if (errMsg.includes('already registered') || errMsg.includes('already exists') || errMsg.includes('409')) {
        setMsg('addMfgMsg', 'That login already exists. Continuing with the chain whitelist…', 'info');
      } else {
        mfgSetStep('error', 'idle', 'idle');
        setMsg('addMfgMsg', `Account creation failed: ${err.message}`, 'error');
        setLoading(btn, false);
        mfgInputs(false);
        return;
      }
    }

    mfgSetStep('done', 'active', 'idle');
    setLoading(btn, true, 'Step 2/2 — Waiting for MetaMask…');

    const blockchainPayload = { wallet_address: wallet, manufacturer_id: mfgId, name: fullName };

    try {
      const tx = await doBlockchainStep(blockchainPayload);
      mfgSetStep('done', 'done', 'done');
      const txLabel = tx.tx_hash === 'already_whitelisted'
        ? 'wallet was already whitelisted'
        : `TX: ${tx.tx_hash.slice(0, 18)}…`;
      setMsg('addMfgMsg', `Manufacturer account created and whitelisted. ${txLabel}`, 'success');
      toast('Manufacturer registered', 'success', 5000);
      e.target.reset();
      mfgSetStep('idle', 'idle', 'idle');
      loadManufacturers();
    } catch (err) {
      mfgSetStep('done', 'error', 'idle');
      _retryPayload = blockchainPayload;
      document.getElementById('mfgRetryWalletLabel').textContent = wallet.slice(0, 14) + '…';
      document.getElementById('mfgRetryIdLabel').textContent     = mfgId;
      retryPanel.style.display = 'block';
      setMsg('addMfgMsg', `Account step finished. Chain step failed: ${err.message}`, 'error');
      toast('Blockchain step failed — use Retry below.', 'error');
    } finally {
      setLoading(btn, false);
      mfgInputs(false);
    }
  });

  document.getElementById('mfgRetryBtn').addEventListener('click', async () => {
    if (!_retryPayload) return;
    const retryBtn   = document.getElementById('mfgRetryBtn');
    const submitBtn  = document.getElementById('addMfgSubmitBtn');
    const retryPanel = document.getElementById('mfgRetryPanel');

    retryBtn.disabled  = true;
    submitBtn.disabled = true;
    retryBtn.innerHTML = '<span class="spinner"></span> Retrying blockchain…';
    setMsg('addMfgMsg', `Retrying whitelist for ${_retryPayload.wallet_address.slice(0, 14)}…`, 'success');
    mfgSetStep('done', 'active', 'idle');

    try {
      const tx = await doBlockchainStep(_retryPayload);
      mfgSetStep('done', 'done', 'done');
      retryPanel.style.display = 'none';
      const txLabel = tx.tx_hash === 'already_whitelisted'
        ? 'wallet was already whitelisted'
        : `TX: ${tx.tx_hash.slice(0, 18)}…`;
      setMsg('addMfgMsg', `Whitelist confirmed. ${txLabel}`, 'success');
      toast('Manufacturer whitelisted', 'success', 5000);
      document.getElementById('addMfgForm').reset();
      mfgSetStep('idle', 'idle', 'idle');
      _retryPayload = null;
      loadManufacturers();
    } catch (err) {
      mfgSetStep('done', 'error', 'idle');
      retryBtn.innerHTML = '↻ Retry Blockchain Whitelist Only';
      setMsg('addMfgMsg', `Retry failed: ${err.message}`, 'error');
      toast('Retry failed — check the message.', 'error');
    } finally {
      retryBtn.disabled  = false;
      submitBtn.disabled = false;
    }
  });
})();


// ── Network info ───────────────────────────────────────────────────────────
async function loadNetworkInfo() {
  try {
    const data = await api('GET', '/api/blockchain/network');
    document.getElementById('netStatus').textContent    = data.connected ? '🟢 Connected' : '🔴 Disconnected';
    document.getElementById('netChainId').textContent   = data.chain_id   ?? '—';
    document.getElementById('netBlock').textContent     = data.block_number?.toLocaleString() ?? '—';
    document.getElementById('netContract').textContent       = data.contract   ?? '—';
    const ownerEl = document.getElementById('netContractOwner');
    if (ownerEl) ownerEl.textContent = data.contract_owner ?? '—';
    document.getElementById('netRpc').textContent            = data.rpc        ?? '—';
    updateNetworkPill(data.connected, data.chain_id);
  } catch (err) {
    document.getElementById('netStatus').textContent = '🔴 Error';
    updateNetworkPill(false);
  }
}

function updateNetworkPill(connected, chainId) {
  const dot   = document.querySelector('.network-dot');
  const label = document.getElementById('networkLabel');
  dot.className = 'network-dot ' + (connected ? 'connected' : 'error');
  const names = { 11155111: 'Sepolia', 1: 'Mainnet', 31337: 'Anvil' };
  label.textContent = connected
    ? (names[chainId] || `Chain ${chainId}`)
    : 'Disconnected';
}

document.getElementById('refreshNetBtn').addEventListener('click', loadNetworkInfo);

// ── Check wallet authorization ─────────────────────────────────────────────
document.getElementById('checkMfgForm').addEventListener('submit', async e => {
  e.preventDefault();
  const btn = e.target.querySelector('button[type=submit]');
  setMsg('checkMfgMsg', '');
  setLoading(btn, true, 'Checking…');
  try {
    const wallet = document.getElementById('checkWallet').value.trim();
    const data = await api('GET', `/api/blockchain/manufacturers/${wallet}/is-authorized`);
    const msg = data.is_manufacturer
      ? `✓ ${wallet.slice(0,10)}… is an authorized manufacturer`
      : `✗ ${wallet.slice(0,10)}… is NOT a registered manufacturer`;
    setMsg('checkMfgMsg', msg, data.is_manufacturer ? 'success' : 'error');
  } catch (err) {
    setMsg('checkMfgMsg', err.message, 'error');
  } finally {
    setLoading(btn, false);
  }
});

// ── Init ───────────────────────────────────────────────────────────────────
applyAuthState();
loadNetworkInfo();    // check network on load
setInterval(loadNetworkInfo, 30_000);   // re-check every 30s
