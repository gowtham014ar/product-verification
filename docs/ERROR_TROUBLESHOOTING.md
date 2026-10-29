# Error Troubleshooting & Resolution Guide

> **Document Type:** Operational Troubleshooting & Fault Resolution  
> **Target Audience:** Blockchain Architects, Backend Engineers, DevOps, Support & QA  
> **Primary Systems:** Ethereum Sepolia Smart Contract (`ProductRegistry.sol`), FastAPI Blockchain Service, API Gateway, Frontend SPA  
> **Authoritative Companion:** [`OKF.md`](../OKF.md)

---

## 1. Quick Diagnostic Matrix

| Error Message / Symptom | Layer | Root Cause | Immediate Fix |
|---|---|---|---|
| `"Attempt to overwrite 'name' in LogRecord"` | Python `logging` | `name` is a reserved attribute on Python's `logging.LogRecord`. Passing `"name": name` in `extra={...}` raised a KeyError immediately **after** the transaction confirmed on Ethereum. | Fixed: Renamed to `"mfg_name": name` in `blockchain_service.py`. |
| `Caller is not owner` / `Signing wallet '0x...' is NOT the contract owner` | Smart Contract (`onlyOwner`) | The private key used in `.env` does not belong to the wallet that deployed `CONTRACT_ADDRESS`. | Use deployer private key, or deploy your own contract via Remix and update `CONTRACT_ADDRESS`. |
| `Gas usage: 200,000 / 200,000 (100%)` / `Transaction reverted on-chain` | EVM Execution | Transaction exceeded hardcoded 200k gas limit due to cold storage writes and dynamic arrays. | Fixed via dynamic `estimate_gas()` with 500,000 gas ceiling in `blockchain_service.py`. |
| `{"error":"Trying to access beyond buffer length"}` | Etherscan Web Decoder | Etherscan tried to decode a revert message from a 0-byte return buffer caused by an Out of Gas (OOG) halt. | Re-send transaction with updated 500,000 gas limit; transaction will confirm with `Success`. |
| `Email already registered` / `Product already exists` halts flow | Frontend SPA | Step 1 (PostgreSQL) caught HTTP 409 duplicate and exited before reaching Step 2 (Blockchain). | Fixed in `app.js` to log info notice and proceed directly to Step 2 blockchain ingestion. |
| `The private key must be exactly 32 bytes long, instead of 20 bytes` | `web3.py` signing | A 42-char public wallet address (`0x...`) was pasted into a field expecting a 66-char private key. | Export the 64-hex-char (32-byte) private key from MetaMask (`Account Details → Show Private Key`). |
| `No owner private key provided` | Blockchain Service | `OWNER_PRIVATE_KEY` was left empty in `.env` and omitted from the request body. | Fill in `OWNER_PRIVATE_KEY=0x...` in `.env` or input it in the Admin UI form. |

---

## 2. Deep Dive: Incident Analysis & Resolutions

---

### Incident 1: "Attempt to overwrite 'name' in LogRecord" (Post-Mining Crash)

#### Symptoms & Misconception
* **The Misconception:** "Is blockchain trying to write two times?"
* **The Reality:** No! The blockchain wrote **once and succeeded**. The transaction was successfully mined on Sepolia (Block `11886017`, `status: 1`, `gas_used: 696663`, tx hash: `0x87dd0ecb063e432f22c23ba195482b5a808c5e102ac5b8625b94e15770621fcc`).
* **The Crash:** Right after `_send_tx()` returned the confirmed transaction hash, Python executed:
  ```python
  log.info("manufacturer added on-chain", extra={"event": "...", "name": name, ...})
  ```
  In Python's standard `logging` library, `name` is a reserved internal attribute on `LogRecord` representing the logger instance name. Passing `"name"` inside `extra` triggers a fatal `KeyError: "Attempt to overwrite 'name' in LogRecord"`.
* **Consequence:** The router caught this Python exception and returned HTTP 500, making the client believe the operation had failed, even though the on-chain write had actually confirmed.

#### Resolution
Renamed `"name": name` to `"mfg_name": name` in [blockchain_service.py:L289](../services/blockchain-service/app/services/blockchain_service.py#L289).

---

### Incident 2: "Caller is not owner" Revert

#### Error Signatures
* **Backend Log:**
  ```json
  {"level": "ERROR", "message": "add_manufacturer key error", "error": "Signing wallet '0xbB23...' is NOT the contract owner! The on-chain contract owner is '0x124c...'."}
  ```
* **Contract Revert:**
  ```text
  Contract execution reverted: Caller is not owner (0x43616c6c6572206973206e6f74206f776e6572)
  ```

#### Technical Root Cause
The smart contract modifier in [ProductRegistry.sol](../contracts/src/ProductRegistry.sol#L46-L50) strictly enforces:
```solidity
modifier onlyOwner() {
    require(msg.sender == owner, "Caller is not owner");
    _;
}
```
The state variable `address public owner;` is set once during deployment in the constructor:
```solidity
constructor() {
    owner = msg.sender;
}
```
If the private key in [.env](../.env) (`OWNER_PRIVATE_KEY`) derives an address that differs from the deployer of `CONTRACT_ADDRESS`, the EVM rejects the transaction. Setting environment variables like `CONTRACT_OWNER` cannot alter EVM storage on Ethereum.

#### Resolution Steps
1. **Option A (Recommended): Deploy Your Own Contract from MetaMask**
   - Open [Remix IDE](https://remix.ethereum.org/).
   - Paste [ProductRegistry.sol](../contracts/src/ProductRegistry.sol).
   - Under **Deploy & Run Transactions**, set Environment to **Injected Provider - MetaMask** on Sepolia.
   - Click **Deploy** and confirm in MetaMask.
   - Copy the deployed address and update [.env](../.env):
     ```env
     CONTRACT_ADDRESS=0x<YourNewContractAddress>
     OWNER_PRIVATE_KEY=0x<YourMetaMaskPrivateKey>
     ```
2. **Option B: Use the Original Deployer Private Key**
   - If you own the wallet shown in the error log as `contract owner`, export its private key from MetaMask (`Account Details → Show Private Key`) and set it in [.env](../.env) as `OWNER_PRIVATE_KEY`.

---

### Incident 3: Out of Gas Revert & Etherscan "Trying to access beyond buffer length"

#### Error Signatures
* **Sepolia Etherscan:**  
  `Status: ❌ Failed addManufacturer`  
  `Gas usage & limit by txn: 200,000 | 200,000 —— 100%`
* **Etherscan Trace Decoder:**  
  `{"error":"Trying to access beyond buffer length"}`
* **Backend Log:**  
  `Transaction reverted: 0x3f7d63... (Reason: Transaction reverted on-chain)`

#### Technical Root Cause
1. **EVM Gas Exhaustion:**  
   [blockchain_service.py](../services/blockchain-service/app/services/blockchain_service.py) previously hardcoded `"gas": 200_000`.  
   Executing `addManufacturer` creates a mapping entry with 5 fields, writes a dynamic `string` name, pushes to `manufacturerAddresses` storage array, and emits an event. Writing these cold storage slots requires **~230,000 to ~260,000 gas**. At block execution, the EVM consumed all 200,000 gas and halted with `OutOfGas`.
2. **Buffer Length Error on Etherscan:**  
   When the EVM runs out of gas, it halts abruptly and returns a `0-byte` buffer (no custom revert error string). When Etherscan's web client attempted to decode the return data buffer, the JavaScript parser threw `Trying to access beyond buffer length`.

#### Resolution Steps
Updated [_send_tx()](../services/blockchain-service/app/services/blockchain_service.py#L105-L125) with dynamic gas estimation and a safe 500k ceiling:
```python
try:
    estimated_gas = fn.estimate_gas({"from": account.address})
    gas_limit = max(int(estimated_gas * 1.5), 500_000)
except Exception:
    gas_limit = 500_000
```
On Ethereum, unused gas is automatically refunded. Setting a 500,000 ceiling guarantees transactions have sufficient gas to confirm.

---

### Incident 4: PostgreSQL Duplicate 409 Aborting Blockchain Ingestion

#### Error Signatures
* **UI Notice:** `❌ Step 1 failed (account creation): Email already registered`
* **Symptom:** Retrying a failed blockchain registration stopped at Step 1 without ever sending the transaction to Ethereum.

#### Technical Root Cause
Manufacturer onboarding is a two-step hybrid workflow:
1. **Step 1:** Off-chain login account created in PostgreSQL (`POST /api/auth/register`).
2. **Step 2:** On-chain wallet whitelisted in Smart Contract (`POST /api/blockchain/manufacturers`).

If Step 2 failed on an initial attempt (e.g., due to gas or network timeout), the user already existed in PostgreSQL. On retry, Step 1 returned `HTTP 409 Conflict ("Email already registered")`. The UI error handler previously executed `return;`, terminating the flow before Step 2.

#### Resolution Steps
Updated [frontend/app.js](../frontend/app.js#L363-L373) and product registration in [app.js:L240-L250](../frontend/app.js#L240-L250):
* If Step 1 returns `409` or `already registered`/`already exists`, the UI logs an informational note (`ℹ Account already exists in database. Continuing to ingest on blockchain…`) and proceeds directly to Step 2.

---

### Incident 5: 20-Byte Public Address vs. 32-Byte Private Key

#### Error Signatures
```text
ValueError: The private key must be exactly 32 bytes long, instead of 20 bytes
```

#### Technical Distinction
* **Ethereum Public Wallet Address (20 bytes / 42 chars):**  
  Format: `0x` + 40 hex characters (e.g., `0x742d35Cc6634C0532925a3b844Bc454e4438f44e`).  
  Usage: Public identity (`wallet_address`). Safe to share.
* **Ethereum Private Key (32 bytes / 66 chars):**  
  Format: `0x` + 64 hex characters (e.g., `0x36a30b50...`).  
  Usage: Cryptographic transaction signing (`owner_private_key`, `manufacturer_private_key`). Must be kept secret.

#### Resolution Steps
* Always export the private key from MetaMask via:  
  **MetaMask → Click 3 dots next to Account → Account Details → Show Private Key**.

---

### Incident 6: Purpose of `CONTRACT_OWNER` Environment Variable

#### Technical Clarification
* On-chain smart contract ownership is stored in EVM storage at contract creation and cannot be changed via off-chain `.env` variables.
* The `CONTRACT_OWNER` variable in [.env](../.env) serves as:
  1. **Configured Reference / Fallback:** If an RPC glitch prevents reading `owner()` on-chain, `network_info()` falls back to `CONTRACT_OWNER`.
  2. **Pre-Validation Anchor:** Used by [blockchain_service.py](../services/blockchain-service/app/services/blockchain_service.py#L250-L260) to provide immediate feedback if a signing key belongs to an unauthorized wallet.

---

## 3. Preventive Maintenance Checklist

Before running write transactions on Ethereum Sepolia:
1. [ ] Check that `CONTRACT_ADDRESS` in [.env](../.env) matches your deployed contract.
2. [ ] Check that `OWNER_PRIVATE_KEY` in [.env](../.env) matches the wallet that deployed `CONTRACT_ADDRESS`.
3. [ ] Verify that the signing wallet has at least `0.05 Sepolia ETH` for gas fees.
4. [ ] Verify RPC connectivity via `GET /api/blockchain/network`.
5. [ ] Rebuild container images after editing `.py` files: `docker compose up --build -d`.
