# User Interface (UI) Guide: Network Status, Login & Product Lifecycle

This guide explains how to view the connected blockchain network in the UI, how to create an account and log in, and how to register and verify products with sample data.

---

## 1. How the Connected Network is Displayed

The UI connects to the Ethereum **Sepolia testnet** through the API Gateway (`http://localhost:8000`) and the Blockchain Service (`http://localhost:8003`).

### 1. Header Network Pill (Top-Right)
In the top-right header, adjacent to the "Sign in" button, you will see the **Network Pill**:
* **🟢 Sepolia**: Connected to Ethereum Sepolia testnet (Chain ID `11155111`).
* **🔴 Disconnected / Error**: Indicates the gateway or RPC connection is unreachable.

### 2. Dedicated "🌐 Network" Page
Click the **🌐 Network** tab in the navigation bar to see full real-time telemetry:
* **Status:** `🟢 Connected`
* **Chain ID:** `11155111` (Sepolia Testnet)
* **Block Number:** Live block height from Alchemy/Infura RPC (e.g., `11,857,132`)
* **Contract:** `0x816cef16DCabBbc4eE970c4dBDCa4444015bdbca` (`ProductRegistry.sol`)
* **RPC URL:** `https://eth-sepolia.g.alchemy.com/v2/...`
* **Check Wallet Authorization:** An interactive input where you can enter any Ethereum wallet address (e.g., `0x124cc1e013d9959e68e7b221f4ac1369370e7ffb`) to check if it is registered as an authorized manufacturer on the smart contract.

> [!NOTE]
> If the network previously showed "Connecting…" or "Disconnected", this was caused by the Docker healthcheck waiting on `curl` (which has now been resolved to use Python's built-in `urllib`) and the API Gateway route permissions (which now permit public reads of network status).

---

## 2. How to Register & Log In via the UI

### Step 1: Open the Frontend
Navigate to **`http://localhost`** (or `http://localhost:80`) in your web browser.

### Step 2: Open the Authentication Modal
Click the **Sign in** button in the upper right corner of the header.

### Step 3: Create an Account (Register)
1. In the modal, click the **Register** tab.
2. Fill in the fields:
   * **Full Name:** `Acme Precision Watches Ltd`
   * **Email:** `manufacturer@acme.com`
   * **Password:** `Password123!`
   * **Wallet Address:** optional. This form creates a **customer** account. It cannot grant manufacturer or admin. An admin creates manufacturer logins from the Manufacturers tab.
3. Click **Create account**. A green notification "Account created!" will appear.

### Step 4: Sign In
1. In the same modal, switch to the **Sign in** tab.
2. Enter your credentials:
   * **Email:** `manufacturer@acme.com` (or pre-seeded admin `admin@productverify.local`)
   * **Password:** `Password123!` (or `admin123` for the admin)
3. Click **Sign in**.
4. The modal will close, and the top-right header will display your session pill:
   `you@example.com · customer` alongside a **Sign out** button. A manufacturer pill appears only after an admin creates that account.

---

## 3. How to Register a Product (Manufacturer Flow)

Once logged in with a `manufacturer` or `admin` role:

1. Click the **📦 Register Product** tab in the main navigation.
2. Fill in the product details using one of the sample sets below:
   * **Product ID:** `LUX-WAT-001`
   * **Product Name:** `Submariner Oyster Perpetual 41mm`
   * **Serial Number:** `ROX-882910-K`
   * **Model:** `SUB-126610LN`
   * **Batch:** `2026-CH-04`
   * **Description:** `Oystersteel luxury diving timepiece with black Cerachrom bezel.`
3. Click **Register with MetaMask**. The private key stays in the wallet.
4. The page then:
   * Saves the catalog row (`POST /api/products/`). `created_by` is taken from the gateway header.
   * Loads unsigned `registerProduct` calldata (`POST /api/blockchain/products/prepare`).
   * Asks MetaMask to sign and broadcast.
   * After the receipt is mined, links the row (`POST /api/products/{id}/mark-on-chain`). `is_on_chain` stays false until that check succeeds.
5. The confirmation line includes the transaction hash.

---

## 4. How to Manage & Add Manufacturers (Admin Flow)

The **🏭 Manufacturers** tab displays manufacturers registered directly on the Ethereum smart contract (`ProductRegistry.sol::getAllManufacturers()`).

### Adding an On-Chain Manufacturer via UI:
1. Log in as an **Admin** (local demo: `admin@productverify.local` / `admin123`). That password is published in the repo. Change it if anyone else can reach the machine.
2. Navigate to the **🏭 Manufacturers** tab. The add form is shown only for an admin.
3. Fill in email, password, company name, the manufacturer's public wallet (42 characters), and a manufacturer id such as `MFG001`.
4. Click **Register Manufacturer**. MetaMask must be the contract **owner**. The owner key is not typed into the page.
5. After the transaction is mined, the wallet appears in the table as active.

The seeded admin password `admin123` is a local demo default, same as the database user `postgres` / `postgres` and the JWT secret `change-me-in-production`.

---

## 5. How to Verify a Product (Consumer / Public Flow)

Product verification is **100% public** and requires **zero login and zero gas fees**:

1. Click the **🔍 Verify** tab in the main navigation.
2. Enter the exact 4 parameters that comprise the canonical cryptographic fingerprint:
   * **Product ID:** `LUX-WAT-001`
   * **Serial Number:** `ROX-882910-K`
   * **Model:** `SUB-126610LN`
   * **Batch:** `2026-CH-04`
3. Click **Verify authenticity**.
4. **Verdicts:**
   * **Registered record matches:** the four fields match an active registration. A copied label would match too.
     * Displays Manufacturer wallet address
     * Registration timestamp
     * Lifecycle status (`Active: Yes`)
     * Keccak256 hash prefix
   * **❌ Not Authentic / Not Found (Red):**
     * Triggered if the Product ID does not exist on-chain OR if any parameter (serial number, model, batch) does not match what was stored on-chain.

---

## 5. Ready-to-Use Test Data Samples

Use these exact sets to test registering and verifying in the UI:

| Field | Sample 1: Luxury Watch | Sample 2: Pharma Insulin | Sample 3: Electronics |
|---|---|---|---|
| **Product ID** | `LUX-WAT-001` | `PHARM-INS-401` | `ELEC-LAP-772` |
| **Product Name** | `Submariner Oyster 41mm` | `Lantus Solostar 100U/mL` | `MacBook Pro 16" M3 Max` |
| **Serial Number**| `ROX-882910-K` | `SN-LT-2026-99014` | `C02ZX919MD6R` |
| **Model** | `SUB-126610LN` | `SOLO-3ML` | `A2991-M3MAX` |
| **Batch** | `2026-CH-04` | `BATCH-2026-Q1-EUR` | `B2026-OCT-FOX` |
| **Description** | `Luxury diving timepiece` | `Sterile injection pen` | `16-inch M3 Max 64GB 1TB` |

---

## 6. Pre-Configured System Credentials

| Role | Email | Password | Allowed UI Actions |
|---|---|---|---|
| **Pre-seeded Admin** | `admin@productverify.local` or `admin@productverify.com` | `admin123` | Register products, add manufacturers, view system health |
| **New Manufacturer** | Any registered email (Role: `manufacturer`) | Your chosen password | Create catalog items, register products on-chain |
| **Public Consumer** | No login needed | None | Verify authenticity, inspect network status, view catalog |
