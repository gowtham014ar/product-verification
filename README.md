# Product Verification System

A decentralized, blockchain-based product authenticity and anti-counterfeiting platform. Manufacturers register products on-chain using cryptographic proofs; consumers and retailers verify authenticity instantly without trusting a central authority.

![System Architecture](docs/images/system-architecture.jpg)


---

## Architecture Documentation Deep Dive

Comprehensive step-by-step architectural guides and operational resources:

| Document / Resource | Description |
|---|---|
| 📘 [**Operational Knowledge File (`OKF.md`)**](OKF.md) | Single Source of Truth for system purpose, end-to-end workflows, APIs, cryptographic hashing, and Q&A reference. |
| 📑 [**01 — Smart Contract (`ProductRegistry.sol`)**](docs/architecture/01-smart-contract.md) | Contract design decisions, data layout, role permissions, functions, and gas economics. |
| 🏗️ [**02 — System Architecture & Design**](docs/architecture/02-system-architecture.md) | Full end-to-end design, microservices communication, sequence diagrams, and canonical hashing specs. |
| 🧪 [**03 — Service Guide & Testing Manual**](docs/architecture/03-service-guide-and-testing.md) | How to run individual services, health checks, curl payloads, and testing role-based authentication. |
| ⛓️ [**04 — Blockchain Setup & Configuration Guide**](docs/architecture/04-blockchain-setup-and-configuration.md) | How to obtain test ETH, configure Infura/Alchemy RPC, deploy the contract, and update `.env`. |
| 🖥️ [**UI User Guide (`UI_USER_GUIDE.md`)**](UI_USER_GUIDE.md) | Step-by-step UI manual for verifying Sepolia telemetry, account registration/login, and interactive verification. |
| 📦 [**Product Registration Examples (`PRODUCT_REGISTRATION_EXAMPLES.md`)**](PRODUCT_REGISTRATION_EXAMPLES.md) | Canonical Keccak-256 packing breakdown and sample payloads across 4 industry verticals. |
| 🚀 [**Postman Test Suite (`postman_collection.json`)**](postman_collection.json) | Automated test suite validating service health, active/inactive status, JWT extraction, and gasless verification. |

---

## What It Does

| Who | Action |
|-----|--------|
| **Manufacturer** | Registers physical products → computes deterministic `keccak256` hash → permanently recorded on Sepolia Ethereum testnet. |
| **Consumer / Scanner** | Submits product details / scans QR code → service recomputes hash → queries smart contract → returns authentic, tampered, or recalled status. |
| **System Admin** | Manages manufacturer authorization on-chain and monitors microservice health and telemetry in Grafana. |

The smart contract stores only a **32-byte cryptographic hash** (`bytes32`), reducing gas fees to a minimum. All mutable product metadata (name, serial number, model, batch, SKU) resides in PostgreSQL. Any modification to off-chain data immediately breaks the hash match on-chain, exposing counterfeit attempts.

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend UI** | Vanilla HTML5, CSS3, ES6 JS | Responsive dark-theme dashboard (served via Nginx on Port 80) |
| **Smart Contract** | Solidity 0.8.20 | `ProductRegistry.sol` on Sepolia testnet |
| **Blockchain RPC** | web3.py 7.x | Python ↔ Ethereum EVM bridge |
| **Blockchain Network**| Sepolia Testnet (MetaMask) | Free test ETH; optional Ethereum Mainnet or Anvil |
| **API Gateway** | FastAPI (Python 3.12) | Central reverse proxy, JWT validation, header forwarding |
| **Microservices** | FastAPI (Python 3.12) | Modular Auth, Product Catalog, and Blockchain services |
| **Database** | PostgreSQL 16 | Relational store for users and product metadata |
| **Authentication** | JWT (python-jose) + Bcrypt | Stateless RBAC (`admin`, `manufacturer`, `customer`) |
| **Observability** | Grafana Loki 3.x + Grafana 11.x | Structured JSON log ingestion and pre-built monitoring dashboards |
| **Local Logging Fallback** | RotatingFileHandler | Local log persistence (10MB × 5) if Loki is unreachable |
| **Containerization** | Docker + Docker Compose | Unified one-command deployment |

---

## Microservices & Port Map
![Process](docs\images\architecture_diagram.png)

| Service | Host Port | Internal URL | Purpose |
|---------|-----------|--------------|---------|
| **frontend** | `80` | `http://frontend:80` | Nginx web interface for registration, verification, and network telemetry |
| **api-gateway** | `8000` | `http://api-gateway:8000` | Single entry point, JWT verification, routing to downstream microservices |
| **auth-service** | `8001` | `http://auth-service:8001` | User registration, login, password hashing, and JWT token issuance |
| **product-service** | `8002` | `http://product-service:8002` | Product catalog CRUD, keccak256 hash generation, PostgreSQL records |
| **blockchain-service**| `8003` | `http://blockchain-service:8003` | web3.py integration, contract read/write, transaction signing |
| **postgres** | `5432` | `http://postgres:5432` | Relational database storing user profiles and product details |
| **loki** | `3100` | `http://loki:3100` | Centralized log ingestion engine |
| **grafana** | `3000` | `http://grafana:3000` | Interactive monitoring dashboards (`admin` / `admin123`) |

---

## User Interface Walkthrough & Operational Scenarios

The platform provides a responsive, dark glassmorphism Single Page Application (SPA) served via Nginx on Port `80`. The dashboard implements strict Role-Based Access Control (RBAC) and exposes four main workspaces: **Verify**, **Register Product**, **Manufacturers**, and **Network**.

Below are the five core operational scenarios demonstrated in the platform:

---

### Scenario 1: Authentic Product Verification (Consumer / Public View)

![Scenario 1: Authentic Product Verification](docs/images/ui_scenario_1_authentic_verification.jpg)

#### Overview & Objective
This scenario demonstrates how an end consumer, retail clerk, or customs inspector validates a physical product's authenticity without creating an account or paying blockchain transaction fees.

#### What Can Be Seen on This Page
* **Input Form Controls:**
  * **Product ID:** The unique item or SKU identifier (e.g., `ELEC-PHN-002`).
  * **Serial Number:** The physical unit serial number (e.g., `SAM-PHN-2026-002`).
  * **Model Number:** The hardware model designation (e.g., `SM-S948B`).
  * **Batch Identifier:** The factory production run (e.g., `BATCH-2026-SAM-P02`).
  * **Action Button:** `Verify authenticity` button triggering a gasless on-chain evaluation.
* **Authenticity Verdict Card (Green Success Banner):**
  * **Headline:** `🟢 Authentic Product` confirming the product was minted by an authorized manufacturer.


#### Cryptographic & Architectural Mechanics
1. The consumer client submits the 4 canonical attributes to the API Gateway.
2. The service deterministically packs and computes:
   $$\text{Hash} = \text{keccak256}(\text{productId} \parallel \text{serialNumber} \parallel \text{model} \parallel \text{batch})$$
3. The blockchain service executes a zero-gas `view` call (`ProductRegistry.sol::verifyProduct`) over the RPC bridge.
4. The smart contract performs an $O(1)$ mapping lookup in storage. Because the computed hash exactly matches the on-chain fingerprint and `active == true`, Ethereum mathematically proves the item is authentic.

---

### Scenario 2: Counterfeit & Tampered Product Detection (Fraud Prevention)

![Scenario 2: Tampered / Counterfeit Product Detection](docs/images/ui_scenario_2_tampered_verification.png)

#### Overview & Objective
This scenario demonstrates the platform's anti-counterfeiting defense. It simulates an attacker attempting to pass off a counterfeit unit or re-labeling an unauthorized serial number (`SAM-PHN-2026-001` instead of genuine `002`).

#### What Can Be Seen on This Page
* **Tampered Input Parameters:**
  * Product ID, Model, and Batch match a legitimate product series (`ELEC-PHN-002`, `SM-S948B`, `BATCH-2026-SAM-P02`).
  * The physical **Serial Number** has been altered by a single character (`SAM-PHN-2026-001`).
* **Fraud Alert Card (Red Alert Banner):**
  * **Headline:** `🔴 Not Authentic / Not Found` alerting the user that the item failed authenticity checks.
  * **Discrepancy Details:** Shows that the computed hash (`0x5c518d43c615d6...`) mathematically diverges from the fingerprint recorded in the smart contract registry.
  * **Security Assessment:** Indicates that either the serial number does not exist, the product was never registered on-chain, or physical metadata was altered after manufacturing.

#### Cryptographic & Architectural Mechanics
* **Cryptographic Avalanche Effect:** In Keccak-256, changing even one character in the input string causes more than 50% of the output bits to flip.
* Because the smart contract stores immutable hashes on the EVM, counterfeiters cannot spoof serial numbers or forge packaging without causing a mathematical mismatch.
* The consumer is protected from purchasing fraudulent, counterfeit, or grey-market goods.

---

### Scenario 3: Product Registration & Cryptographic Minting (Manufacturer Workspace)

![Scenario 3: Product Registration](docs/images/ui_scenario_3_product_registration.jpg)

#### Overview & Objective
This workspace allows authorized manufacturers to catalog new merchandise in the off-chain database and anchor an immutable 32-byte cryptographic fingerprint onto Ethereum Sepolia.

#### What Can Be Seen on This Page
* **Role Guard & Navigation:**
  * Active navigation tab: **📦 Register Product** (requires authenticated `manufacturer` role).
  * Informative guide explaining that the Keccak-256 fingerprint is generated and stored permanently on-chain.
* **3-Step Lifecycle Visual Indicator:**
  * `1 Save to database` $\rightarrow$ `2 Register on-chain` $\rightarrow$ `3 Tx confirmed`.
* **Product Catalog Inputs:**
  * **Product ID:** Alphanumeric identifier (e.g., `P10001`).
  * **Product Name:** Commercial description (e.g., `Widget X Pro`).
  * **Serial Number:** Unique per-unit identifier (e.g., `SN001928`).
  * **Model & Batch:** Production specifications (e.g., `ABC-X1`, `B2026-09`).
  * **Description:** Optional extended specifications and warranty terms.
* **Blockchain Transaction Signing Control:**
  * **Manufacturer Private Key Field:** Secure input field for the manufacturer's 32-byte Ethereum private key. The key is used locally by the service to sign the transaction and is never persisted into the database.
  * **Action Button:** `Register product` to initiate the database write and blockchain broadcast.

#### Cryptographic & Architectural Mechanics
1. **Off-Chain Persistence:** Rich product metadata (descriptions, names, timestamps) is saved in PostgreSQL 16.
2. **Deterministic Fingerprint:** The service encodes the 4 canonical fields into a 32-byte byte array (`bytes32`).
3. **Smart Contract Enforcement:** `ProductRegistry.sol::registerProduct` verifies via the `onlyManufacturer` modifier that `msg.sender` is an active whitelisted manufacturer address.
4. An irreversible `ProductRegistered` event is emitted on Sepolia, generating a permanent transaction hash (`0x...`).

---

### Scenario 4: Manufacturer Onboarding & Dual-Layer Governance (Admin Workspace)

![Scenario 4: Manufacturer Governance](docs/images/ui_scenario_4_manufacturer_governance.jpg)

#### Overview & Objective
This administrative dashboard allows system governors to inspect registered manufacturers and onboard new enterprise partners across both PostgreSQL and the Ethereum smart contract.

#### What Can Be Seen on This Page
* **Active Manufacturers Registry Table:**
  * Displays all approved enterprises currently active on the Ethereum smart contract:
    * **Company Name:** e.g., `GSK Pharmaceuticals`, `Samsung Electronics`.
    * **Wallet Address:** 42-character public Ethereum address (`0x...`).
    * **Added Date:** Block timestamp when the manufacturer was approved (`10/10/2026`).
    * **Status Badge:** `🟢 Active` authorization badge.
  * `↻ Refresh` button to poll live smart contract state via `getAllManufacturers()`.
* **Unified Onboarding Form (`ADMIN ONLY`):**
  * **Dual-Tier Registration Pipeline:** Automatically coordinates off-chain account creation with on-chain smart contract whitelisting in a single transaction flow.
  * **Section 1 (PostgreSQL Login Account):** Enterprise email and initial password for dashboard authentication.
  * **Section 2 (Shared Metadata):** Company display name and public Ethereum wallet address (42 characters).
  * **Section 3 (Blockchain Smart Contract):** Unique Manufacturer ID (e.g., `MFG001`) and Admin Owner Private Key for signing the administrative transaction.
  * **Action Button:** `Register Manufacturer` executing the two-tier provisioning pipeline.

#### Cryptographic & Architectural Mechanics
* **Access Control:** The Solidity smart contract enforces the `onlyOwner` modifier on `addManufacturer`. Only the deployer's wallet can grant manufacturer privileges.
* **On-Chain Storage:** The smart contract stores the wallet in `mapping(address => Manufacturer) manufacturerInfo` and pushes the address to `manufacturerAddresses` for enumeration.
* Once whitelisted on-chain, the manufacturer can sign transactions to register products.

---

### Scenario 5: Real-Time Network Telemetry & Authorization Audit (Diagnostic Workspace)

![Scenario 5: Network Telemetry & Authorization Audit](docs/images/ui_scenario_5_network_telemetry.jpg)

#### Overview & Objective
This workspace provides real-time system observability, verifying live Web3 RPC synchronization, Ethereum node height, deployed contract coordinates, and ad-hoc wallet authorization inspection.

#### What Can Be Seen on This Page
* **Top Bar Live Pulse Indicator:**
  * Shows `🟢 Sepolia` with a green indicator, continuously polling node health.
* **Network Status Card:**
  * **Status:** `🟢 Connected` verifying active communication with the Ethereum JSON-RPC provider.
  * **Chain ID:** `11155111` confirming the target is Ethereum Sepolia Testnet.
  * **Block Number:** Live block height (`11,886,109`) showing real-time blockchain synchronization.
  * **Contract Address:** The deployed address of `ProductRegistry.sol` on Sepolia.
  * **Contract Owner:** The administrative wallet that governs the smart contract.
  * **RPC Provider:** The Web3 HTTP RPC endpoint connecting the microservice mesh to Ethereum.
  * `↻ Refresh` button triggering dynamic telemetry queries via `GET /api/blockchain/network`.
* **Check Wallet Authorization Diagnostic Tool:**
  * Interactive tool allowing any retailer, inspector, or auditor to paste an Ethereum public address (`0x...`) and immediately check whether the wallet is an active authorized manufacturer on-chain.

#### Cryptographic & Architectural Mechanics
* Telemetry polling queries `Web3.is_connected()`, `w3.eth.block_number`, and `contract.functions.owner().call()` without requiring user authentication.
* The wallet authorization checker calls `ProductRegistry.sol::isManufacturer(address)` via gasless `eth_call`, giving consumers full transparency into supply chain authorizations.

---

## Project Structure

```
product-verification/
├── contracts/
│   ├── src/ProductRegistry.sol             ← Smart contract source code
│   ├── test/                               ← Foundry smart contract unit tests
│   └── script/Deploy.s.sol                 ← Foundry deployment script
│
├── frontend/
│   ├── index.html                          ← Responsive single-page UI (Port 80)
│   ├── style.css                           ← Dark glassmorphism styling (Inter font)
│   └── app.js                              ← Vanilla JS state and API client
│
├── services/
│   ├── common/                             ← Shared utilities across all services
│   │   ├── crypto/hashing.py               ← keccak256 deterministic hash functions
│   │   ├── models/base.py                  ← SQLAlchemy declarative base
│   │   └── logging/logger.py               ← Tri-modal logging (stdout, file, Loki)
│   │
│   ├── api-gateway/                        ← :8000 reverse proxy + JWT gatekeeper
│   ├── auth-service/                       ← :8001 registration, login, token issue
│   ├── product-service/                    ← :8002 catalog CRUD & database models
│   └── blockchain-service/                 ← :8003 web3.py EVM contract interface
│       └── contracts_abi/
│           └── ProductRegistry.json        ← Contract ABI definition
│
├── database/
│   └── init-scripts/01-init.sql            ← PostgreSQL bootstrap schemas
│
├── examples/
│   ├── products_sample.json                ← Initial 4 sample products across verticals
│   ├── product_samples-2.json              ← 30 production items (Apple, Samsung, GSK, Lay's)
│   └── manufacturer_examples.json          ← 8 verified manufacturer accounts with wallets
│
├── monitoring/
│   ├── loki/config.yaml                    ← Loki single-node retention & storage
│   └── grafana/
│       ├── provisioning/                   ← Automated datasources & dashboards
│       └── dashboards/product-verification.json ← Pre-configured dashboard
│
├── docs/architecture/
│   ├── 01-smart-contract.md                ← Smart contract architectural rationale
│   ├── 02-system-architecture.md           ← Complete system architecture & sequence flows
│   ├── 03-service-guide-and-testing.md     ← Individual service startup & test manual
│   ├── 04-blockchain-setup-and-configuration.md ← Blockchain config, MetaMask, and .env setup
│   └── system-architecture.jpg             ← System architecture visual diagram
│
├── postman_collection.json                 ← Complete Postman v2.1 testing suite
├── PRODUCT_REGISTRATION_EXAMPLES.md        ← Canonical hashing & registration guide
├── UI_USER_GUIDE.md                        ← Interactive UI & network guide
├── Product_Verification_System_Architecture_and_Operations.docx / .doc ← Printable technical specification
├── Product_Verification_System_Presentation.pptx / .ppt ← 6-slide executive presentation
├── docker-compose.yml                      ← Multi-container orchestration (urllib health checks)
├── .env.example                            ← Environment template
└── README.md                               ← Platform documentation
```

---

## Quick Start

### 1. Configure Blockchain & Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Open `.env` and fill in your details (refer to [04 — Blockchain Setup Guide](docs/architecture/04-blockchain-setup-and-configuration.md)):
- `ETH_RPC_URL`: Alchemy or Infura Sepolia RPC URL (e.g., `https://eth-sepolia.g.alchemy.com/v2/...`)
- `CONTRACT_ADDRESS`: Deployed address of `ProductRegistry.sol` (`0x816cef16DCabBbc4eE970c4dBDCa4444015bdbca` on Sepolia Chain ID `11155111`)
- `OWNER_PRIVATE_KEY`: Your MetaMask account private key (deployer)
- `JWT_SECRET_KEY`: Random 64-hex string

### 2. Start the Entire Stack
```bash
docker compose up --build -d
```

### 3. Open in Browser
- **Frontend App**: [http://localhost](http://localhost) (or open `frontend/index.html` directly)
- **API Gateway Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Grafana Monitoring**: [http://localhost:3000](http://localhost:3000) (`admin` / `admin123`)

### Pre-Configured Credentials
| Role | Email | Password | Allowed Actions |
|---|---|---|---|
| **System Admin** | `admin@productverify.local` or `admin@productverify.com` | `admin123` | Onboard manufacturers, system observability |
| **New Manufacturer** | Any registered email (Role: `manufacturer`) | Your chosen password | Create catalog items, register products on-chain |
| **Public Consumer** | No login needed | None | Verify product authenticity, check network telemetry |

> [!NOTE]
> **Wallet Address vs Private Key:**
> * **Wallet Address (Public):** 20 bytes (42 characters: `0x...` 40 hex digits). Used in `wallet_address`.
> * **Private Key (Secret):** 32 bytes (66 characters: `0x...` 64 hex digits, exported from MetaMask). Used in `owner_private_key` and `manufacturer_private_key` to sign EVM transactions. Passing a 20-byte address into a private key field causes the error: *"The private key must be exactly 32 bytes long, instead of 20 bytes."*

---

## Automated Postman Test Suite (Service-Wise Testing Guide)

The system provides an automated end-to-end verification and testing suite in [`postman_collection.json`](file:///d:/learning/sample-projects/product-verification/postman_collection.json). It contains structured test scenarios with embedded JavaScript assertions (`pm.test`, `pm.expect`), response schema validation, and dynamic variable chaining (extracting JWT bearer tokens and injecting them across requests).

The test suite is organized into **5 functional modules** aligned with the system's microservice architecture:

```
postman_collection.json
├── 1. Health Checks & Connectivity              (Gateway, Auth, Product, Blockchain & RPC)
├── 2. Authentication & Identity                (Auth Service - JWT & Role Management)
├── 3. Manufacturers & Smart Contract Governance (Blockchain Service - Admin On-Chain Ops)
├── 4. Product Lifecycle (Registration Flow)     (2-Step: PostgreSQL Catalog + Sepolia EVM)
└── 5. Product Verification & Inspection        (Zero-Gas Verification & Tamper Detection)
```

---

### Service-Wise Test Breakdown

#### 1. Health Checks & Infrastructure Connectivity
* **Target Services:**
  * **API Gateway:** `GET http://localhost:8000/health`
  * **Auth Service:** `GET http://localhost:8001/health`
  * **Product Service:** `GET http://localhost:8002/health`
  * **Blockchain Service:** `GET http://localhost:8003/health`
  * **Ethereum Sepolia RPC:** `GET http://localhost:8000/api/blockchain/network`
* **What is Tested & Verified:**
  * **Microservice Liveness:** Validates HTTP `200 OK` status and payload structure (`{"status": "ok", "service": "<service-name>"}`) across all containers.
  * **Ethereum Network & Node Connection:** Validates that `blockchain-service` is actively connected to the Ethereum testnet RPC provider (`connected: true`).
  * **Chain & Contract Validation:** Asserts the target EVM chain ID (`11155111` for Sepolia), current synchronized block number, deployed smart contract address, and contract owner wallet address.

---

#### 2. Authentication & Identity Management (`auth-service`)
* **Target Endpoints:**
  * `POST http://localhost:8000/api/auth/login` (Admin Login)
  * `POST http://localhost:8000/api/auth/register` (Register Manufacturer Account)
  * `POST http://localhost:8000/api/auth/register` (Register Admin Account)
  * `POST http://localhost:8000/api/auth/login` (Manufacturer Login)
* **What is Tested & Verified:**
  * **Credential Authentication:** Verifies argon2/bcrypt password validation and JWT token issuance.
  * **Role-Based Token Claims:** Asserts that the decoded token correctly encodes user roles (`admin` vs. `manufacturer`).
  * **Automated Session State Chaining:** The Postman test script automatically extracts `access_token` from the login response and saves it to the `{{token}}` collection variable, dynamically authenticating subsequent requests.
  * **Registration Idempotency:** Validates account creation (`201 Created`) and handles existing user conflicts (`409 Conflict`) gracefully.

---

#### 3. Smart Contract Governance & Manufacturer Authorization (`blockchain-service`)
* **Target Endpoints:**
  * `GET http://localhost:8000/api/blockchain/manufacturers` (List Manufacturers)
  * `POST http://localhost:8000/api/blockchain/manufacturers` (Add Manufacturer On-Chain)
  * `GET http://localhost:8000/api/blockchain/manufacturers/{{manufacturer_wallet}}/is-authorized` (Check Status)
* **What is Tested & Verified:**
  * **Role & Governance Enforcement:** Verifies that only authenticated administrators bearing valid credentials and the contract owner's signing key can authorize new manufacturers.
  * **On-Chain State Modification:** Submits a signed transaction invoking `addManufacturer(wallet, mfgId, name)` on [`ProductRegistry.sol`](file:///d:/learning/sample-projects/product-verification/contracts/ProductRegistry.sol). Asserts status `added` and the return of a 32-byte Ethereum transaction hash (`tx_hash`).
  * **Authorization Registry Inspection:** Queries the smart contract mapping to ensure the target wallet's authorization status reflects `is_manufacturer: true`.

---

#### 4. Two-Step Product Lifecycle Management (`product-service` + `blockchain-service`)
* **Target Endpoints:**
  * **Step 1 (Catalog Storage):** `POST http://localhost:8000/api/products/`
  * **Step 2 (Cryptographic Anchoring):** `POST http://localhost:8000/api/blockchain/products/register`
* **What is Tested & Verified:**
  * **Hybrid Architecture Separation:**
    * **Step 1:** Verifies persistence of rich, mutable product metadata (name, serial number, model, batch, description) inside PostgreSQL 16. Asserts HTTP `201 Created`.
    * **Step 2:** Verifies deterministic canonical hashing (`keccak256(abi.encodePacked(productId, serialNumber, model, batch))`) and on-chain fingerprint anchoring signed by the manufacturer's private key.
  * **Smart Contract Invariants:** Asserts that only authorized manufacturer wallets can register products, validating transaction confirmation (`tx_hash`) and gas limit adherence on Sepolia.

---

#### 5. Gasless Public Verification & Anti-Counterfeiting (`blockchain-service`)
* **Target Endpoints:**
  * `POST http://localhost:8000/api/blockchain/products/verify` (Authentic Product Test)
  * `POST http://localhost:8000/api/blockchain/products/verify` (Tampered / Counterfeit Product Test)
  * `GET http://localhost:8000/api/products/{{test_product_id}}` (Off-Chain Catalog Query)
* **What is Tested & Verified:**
  * **Zero-Gas Public Verification:** Confirms that consumer product authenticity verification runs via EVM `view` functions requiring **zero gas** and **no authentication token**.
  * **Positive Verification (Authentic):** Submits exact matching parameters (`product_id`, `serial_number`, `model`, `batch`). Asserts `is_authentic == true`, returning the authorized manufacturer's Ethereum address, registration timestamp, and active status.
  * **Negative Verification (Counterfeit / Tamper Detection):** Submits an altered serial number (`FAKE_SERIAL_TAMPERED`). Asserts `is_authentic == false`, demonstrating that any mismatch in product attributes produces an unrecognizable Keccak-256 hash.
  * **Catalog Retrieval:** Confirms consumers can inspect the companion catalog specifications stored in the database.

---

### Collection Variables & Parameter Mapping

The collection uses parameterized variables to isolate test configuration from implementation code:

| Variable Name | Description | Scope / Handling |
| :--- | :--- | :--- |
| `{{gateway_url}}` | Base URL of the API Gateway (`http://localhost:8000`) | Directs traffic through central ingress |
| `{{token}}` | Bearer JWT access token | Dynamically populated by Login requests |
| `{{test_product_id}}` | Sample product identifier (e.g. `LUX-WAT-001`) | Used across 2-step registration & verification |
| `{{test_serial}}` | Serial number for hash verification | Verified in authentic & tampered scenarios |
| `{{manufacturer_wallet}}` | Public Ethereum wallet address (20 bytes / 42 chars) | Configured in manufacturer registration & on-chain whitelist |
| `{{owner_private_key}}` | Contract owner signing key (32 bytes / 66 chars) | Used by Admin to authorize manufacturers on-chain |
| `{{manufacturer_private_key}}` | Manufacturer signing key (32 bytes / 66 chars) | Used to sign on-chain product registration transactions |

> [!NOTE]
> Detailed troubleshooting and execution error resolutions are cataloged in [`ERROR_TROUBLESHOOTING.md`](file:///d:/learning/sample-projects/product-verification/ERROR_TROUBLESHOOTING.md) and [`OKF.md`](file:///d:/learning/sample-projects/product-verification/OKF.md).

---

### How to Run the Test Suite

1. **In Postman GUI:**
   * Open Postman $\rightarrow$ Click **Import** $\rightarrow$ Select [`postman_collection.json`](file:///d:/learning/sample-projects/product-verification/postman_collection.json).
   * Check or update the collection variables (`manufacturer_wallet`, keys) under the **Variables** tab if testing with custom wallets.
   * Right-click the collection $\rightarrow$ Click **Run Collection** $\rightarrow$ Execute all 5 folders sequentially.

2. **Headless via CLI (Newman):**
   ```bash
   npx newman run postman_collection.json --verbose
   ```