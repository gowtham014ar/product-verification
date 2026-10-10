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
   * **Role:** Select **`Manufacturer`** from the dropdown.  
     *(Important: Only users with the `manufacturer` or `admin` role are permitted to register products into the database catalog.)*
   * **Wallet Address:** *(Optional, e.g., your MetaMask public address)* `0x124cc1e013d9959e68e7b221f4ac1369370e7ffb`
3. Click **Create account**. A green notification "Account created!" will appear.

### Step 4: Sign In
1. In the same modal, switch to the **Sign in** tab.
2. Enter your credentials:
   * **Email:** `manufacturer@acme.com` (or pre-seeded admin `admin@productverify.local`)
   * **Password:** `Password123!` (or `admin123` for the admin)
3. Click **Sign in**.
4. The modal will close, and the top-right header will display your session pill:
   `manufacturer@acme.com · manufacturer` alongside a **Sign out** button.

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
   * **Manufacturer Private Key:** Enter your Sepolia wallet's **32-byte private key** (64 hex characters with `0x`, exported from MetaMask → Account Details → Show Private Key, e.g. `0x4f3edf983ac...`). Note: this is **NOT** your 20-byte public wallet address.
3. Click **Register product**.
4. The system executes the 2-step process:
   * **Step 1:** Writes metadata to PostgreSQL (`POST /api/products/`).
   * **Step 2:** Signs and submits an Ethereum transaction to `ProductRegistry.sol` (`POST /api/blockchain/products/register`).
5. A confirmation message with the **Transaction Hash (Tx)** appears:
   `✓ Registered on-chain. TX: 0x4a9f3b12...`

---

## 4. How to Manage & Add Manufacturers (Admin Flow)

The **🏭 Manufacturers** tab displays manufacturers registered directly on the Ethereum smart contract (`ProductRegistry.sol::getAllManufacturers()`).

### Adding an On-Chain Manufacturer via UI:
1. Log in as an **Admin** (e.g., `admin@productverify.local` / `1`).
2. Navigate to the **🏭 Manufacturers** tab.
3. In the **Add Manufacturer (Admin Only)** card, fill in:
   * **Wallet Address (Public):** The manufacturer's public Ethereum address (20 bytes / 42 chars), e.g. `0x27b1FdB04752BBC536007a920D24ACB045561c26`.
   * **Manufacturer ID:** A unique alphanumeric code, e.g. `MFG001`.
   * **Company Name:** Company or brand name, e.g. `Micro Laboratories`.
   * **Owner Private Key:** The **32-byte secret private key** (64 hex characters with `0x`) of the Ethereum account that deployed the contract (`owner`).
4. Click **Add manufacturer**.
5. Once the Ethereum transaction confirms, the manufacturer will appear in the table above with status `Active` and timestamp.

> [!CAUTION]
> **Troubleshooting: "The private key must be exactly 32 bytes long, instead of 20 bytes"**  
> If you see this red error message, you entered an Ethereum **public wallet address** (42 characters: `0x` + 40 hex digits) into a private key field.
> * **Ethereum Public Address (20 bytes):** `0x27b1FdB04752BBC536007a920D24ACB045561c26` (Use for "Wallet Address" only).
> * **Ethereum Secret Private Key (32 bytes):** `0x4f3edf983ac636a65a842ce7c78d9aa706d3b113bce9c46f30d7d21715b23b1d` (64 hex digits, exported from MetaMask).

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
   * **✅ Authentic Product (Green):**
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
