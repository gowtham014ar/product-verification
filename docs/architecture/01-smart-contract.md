# Step 1 — Smart Contract: ProductRegistry

## Why start with the smart contract?

The smart contract is the **single source of truth** for your entire project.  
Everything else — Python APIs, PostgreSQL, QR codes — is built around what the contract stores and returns.  
Getting the contract right first means every downstream service has a stable interface to connect to.

---

## Why Solidity?

- Industry standard for EVM (Ethereum Virtual Machine) smart contracts
- Runs on Ethereum + every L2 (Base, Arbitrum, Polygon, Optimism)
- `web3.py` (Python) speaks to Solidity contracts natively
- Your institute reviewers will recognize it immediately

---

## Why Remix IDE (for now)?

| Tool | Purpose |
|---|---|
| **Remix IDE** | Browser-based, zero install, instant feedback — perfect for learning & iterating |
| **Foundry** | Local CLI testing framework — used later for automated tests & deployment scripts |

Remix is the fastest way to understand how your contract behaves before wiring up Python.

---

## Contract Design Decisions

### What's stored on-chain (minimal & intentional)

```
struct Product {
    bytes32 productHash    <- fingerprint of real product data
    address manufacturer   <- who registered it (wallet address)
    uint256 registeredAt   <- timestamp (cannot be altered)
    bool    active         <- false if recalled/deactivated
}
```

**Why only 4 fields?**  
Every byte stored on-chain costs gas.  
Product name, serial, model, batch, images — all of that lives in PostgreSQL.  
Only the **cryptographic proof** lives on-chain.

### The Hash (Core concept)

```
Off-chain canonical string:
    "P10001|SN001928|ABC-X1|B2026-09"
                |
                v
    keccak256(abi.encode(productId, serialNumber, model, batch))
                |
                v
    0x7a91f3c2...  <- stored on-chain
```

- Any change to any field -> completely different hash -> verification fails
- This is how blockchain detects tampering without storing the full data

### Role system

```
Owner (deployer)
  -> addManufacturer(address)      <- grants registration rights
        -> Manufacturer
              -> registerProduct()  <- can register products
              -> deactivateProduct() <- can deactivate own products
```

Only authorized manufacturers can register products. This prevents anyone from registering fake products against your contract.

---

## Function Breakdown

### `registerProduct(bytes32 productId, bytes32 productHash)`
- Called by: **Manufacturer wallet only**
- Checks: product not already registered (`registeredAt == 0`)
- Stores: hash + caller address + timestamp + `active: true`
- Emits: `ProductRegistered` event

### `verifyProduct(bytes32 productId, bytes32 productHash)`
- Called by: **Anyone** (`view` function — no gas, no transaction)
- Recomputes: your app sends the hash it calculated from the product data
- Returns: `isAuthentic` (true only if registered + active + hash matches)
- This is what the customer verification endpoint calls

### `deactivateProduct(bytes32 productId)`
- Called by: **The manufacturer who registered it, or owner**
- Use case: product recall, counterfeit detected, end of life
- Sets `active = false` — verification will return `isAuthentic: false`
- Cannot be undone (immutable audit trail)

### `getProduct(bytes32 productId)` (bonus view)
- Raw read — returns all stored fields without any hash check
- Useful for admin dashboards and debugging

---

## Step-by-Step: Remix IDE Testing Guide

### 1. Open Remix
Go to -> **https://remix.ethereum.org**

### 2. Create the contract file
- In the **File Explorer** (left panel) -> click `+` -> New File
- Name it: `ProductRegistry.sol`
- Paste the entire contract from `contracts/src/ProductRegistry.sol`

### 3. Compile
- Click the **Solidity Compiler** tab (left panel, `<>` icon)
- Select compiler version: `0.8.20` (or `0.8.x - auto-select`)
- Click **Compile ProductRegistry.sol**
- No errors = ready to deploy

### 4. Deploy to Remix VM (local blockchain)
- Click the **Deploy & Run** tab (Ethereum logo icon)
- Environment: `Remix VM (Cancun)` <- this is a built-in local blockchain, no MetaMask needed
- Contract: `ProductRegistry`
- Click **Deploy**
- You'll see the deployed contract appear at the bottom of the panel

> Remix VM gives you 10 test accounts each with 100 ETH — use these as owner, manufacturer, customer

---

### 5. Test: Add a Manufacturer

Copy the **second account address** from the Account dropdown (this will be your manufacturer).

In the deployed contract panel:
```
addManufacturer
  _addr: 0xAb8483F64d9C6d1EcF9b849Ae677dD3315835cb2   <- paste second account
```
Click **transact** -> transaction succeeds

---

### 6. Test: Register a Product

**Switch the Account dropdown to the manufacturer address** (second account).

Prepare your inputs. In Remix, `bytes32` must be passed as hex.

Use this pattern to generate test values manually:

```
productId   ->  bytes32 of "P10001"
productHash ->  bytes32 representing keccak256("P10001|SN001928|ABC-X1|B2026-09")
```

For quick testing in Remix, use these pre-computed hex values:

```
productId   (bytes32):
0x5031303030310000000000000000000000000000000000000000000000000000

productHash (bytes32) — simulated hash:
0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef
```

In the deployed contract:
```
registerProduct
  productId:   0x5031303030310000000000000000000000000000000000000000000000000000
  productHash: 0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef
```
Click **transact** -> `ProductRegistered` event emitted (visible in the console)

---

### 7. Test: Verify Product (AUTHENTIC)

Pass the **same** productId and productHash:
```
verifyProduct
  productId:   0x503130303031000...
  productHash: 0x1234567890abcde...
```
Click **call** -> Returns:
```
isAuthentic:  true
manufacturer: 0xAb8483...
registeredAt: 1727430000  (UNIX timestamp)
active:       true
```

### 8. Test: Verify Product (FAKE / TAMPERED)

Pass the **same** productId but a **different** hash:
```
verifyProduct
  productId:   0x503130303031000...
  productHash: 0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef
```
Click **call** -> Returns:
```
isAuthentic: false
```
This simulates a counterfeit product or tampered data.

---

### 9. Test: Deactivate a Product

Switch back to the **manufacturer account**:
```
deactivateProduct
  productId: 0x503130303031000...
```
Click **transact** -> `ProductDeactivated` event emitted

Now call `verifyProduct` with the same productId + correct hash -> `isAuthentic: false` (because `active = false`)

---

### 10. Test: Access Control (should fail)

Switch to a **third account** (not owner, not manufacturer):
```
registerProduct
  productId:   0xaaaa...
  productHash: 0xbbbb...
```
Click **transact** -> Reverts with `"Caller is not an authorized manufacturer"`

This confirms your role-based access control is working.

---

## How bytes32 Works (Quick Reference)

| You have | In Remix |
|---|---|
| String `"P10001"` | `0x5031303030310000000000000000000000000000000000000000000000000000` |
| Number `12345` | `0x0000000000000000000000000000000000000000000000000000000000003039` |
| keccak256 hash | `0xabc123...` (always 32 bytes / 64 hex chars) |

> **Note:** Later, your Python (`web3.py`) will convert product IDs and compute hashes automatically. In Remix, you work with raw hex for manual testing.

---

## Gas Cost Reference (approximate, Remix VM)

| Operation | Est. Gas | Why |
|---|---|---|
| Deploy contract | ~600,000 | One-time cost |
| `addManufacturer` | ~45,000 | Writes to mapping |
| `registerProduct` | ~65,000 | Writes struct to mapping |
| `verifyProduct` | 0 | `view` function — free |
| `deactivateProduct` | ~28,000 | Updates one bool field |

> On an L2 like Arbitrum or Base, gas costs are ~10-100x cheaper than Ethereum mainnet.