# Product Verification System — Presentation Slides

> **Slide source:** this markdown file. There is no `.pptx` or `.docx` in the repository.
> **Operational notes:** [`OKF.md`](../OKF.md)

---

## Slide 1: Executive Mission & System Purpose
* **Title:** Product Verification System — Blockchain Anti-Counterfeiting Platform
* **Subtitle:** Hybrid Ethereum Smart Contract & Microservices Architecture for Tamper-Proof Product Authenticity
* **The Counterfeiting Crisis:**
  - Counterfeiting of pharmaceuticals, luxury timepieces, electronics, and automotive parts causes hundreds of billions of dollars in losses annually and poses severe consumer safety risks.
  - Centralized databases are vulnerable to rogue administrator edits, compromised credentials, and single points of failure.
  - Replay attacks allow bad actors to replicate legitimate serial numbers onto thousands of fake products.
* **The Solution:**
  - An optimal **Hybrid Architecture**: Fast, scalable off-chain relational metadata paired with immutable on-chain Ethereum cryptographic proof.
  - Zero-gas verification for consumers worldwide.

---

## Slide 2: Hybrid Architecture (On-Chain + Off-Chain)
* **Title:** Optimal Division: Security, Scalability, and Economic Viability
* **Off-Chain Layer (FastAPI Microservices + PostgreSQL 16):**
  - Stores rich, mutable catalog metadata (descriptions, batch dates, SKUs, model details, images).
  - High-throughput relational queries, pagination, and instant full-text filtering.
  - Role-Based Access Control (RBAC): JWT HS256 tokens for `admin`, `manufacturer`, and `customer`.
* **On-Chain Layer (Ethereum Sepolia Testnet — `ProductRegistry.sol`):**
  - Deployed at: `0x816cef16DCabBbc4eE970c4dBDCa4444015bdbca` (Chain ID `11155111`).
  - Stores strictly a 32-byte cryptographic fingerprint (`bytes32` `keccak256`) per product.
  - Single SSTORE slot optimization drastically minimizes gas costs for manufacturers.
  - Gasless `view` verification functions run locally on Ethereum nodes via `eth_call`.

---

## Slide 3: Cryptographic Specification & Deterministic Hashing
* **Title:** Deterministic Canonical Packing & Tamper-Detection Mathematical Invariant
* **The 4-Part Canonical Packing Formula:**
  $$\text{keccak256}(\text{abi.encode}(\text{productId}, \text{serialNumber}, \text{model}, \text{batch}))$$
* **Human / QR Format:** `productId|serialNumber|model|batch`
  - *Example:* `LUX-WAT-001|ROX-882910-K|SUB-126610LN|2026-CH-04`
* **Tamper-Resistance Invariant:**
  - If any bad actor alters even a single byte in PostgreSQL (e.g. changing serial number or batch), the calculated hash mathematically diverges from the on-chain hash ($H_{\text{altered}} \neq H_{\text{contract}}$).
  - The smart contract immediately flags the item as **Not Authentic / Tampered**.
* **Governance Modifiers:**
  - `onlyManufacturer`: Only whitelisted manufacturer wallets can register products.
  - `onlyOwner`: Contract deployer controls manufacturer onboarding and emergency revocation.

---

## Slide 4: End-to-End Operational Process Flows
* **Title:** Life-Cycle Process Flows: Whitelisting, 2-Step Registration, and Public Verification
* **Flow 1: Manufacturer Onboarding (Admin Action):**
  - System Admin authenticates and calls `POST /api/blockchain/manufacturers`.
  - Smart contract executes `addManufacturer(wallet, id, name)` and emits `ManufacturerAdded`.
* **Flow 2: Two-Step Product Registration:**
  - **Step 1:** Manufacturer calls `POST /api/products/` to save metadata into PostgreSQL.
  - **Step 2:** MetaMask signs `registerProduct`. The catalog row is marked on-chain only after the receipt is checked.
  - Confirmed transaction hash is linked to the catalog record.
* **Flow 3: Gasless Public Verification (Zero Cost):**
  - Consumers enter the 4 canonical fields or scan a QR code.
  - Client queries `POST /api/blockchain/products/verify`.
  - Node performs an instant `eth_call` in under 200ms with zero gas fees.
  - Returns `is_authentic: true`, manufacturer wallet address, and registration timestamp.

---

## Slide 5: Containerization Architecture & Health Orchestration
* **Title:** Production-Grade Docker Mesh with Resilient Health Monitoring
* **Zero-Dependency Health Checks:**
  - All Python microservices run on ultra-lightweight `python:3.12-slim` base images.
  - Standard `curl` is omitted from slim images; health checks leverage Python's built-in `urllib.request`:
    ```yaml
    test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:<PORT>/health')"]
    ```
* **Startup Dependency Hierarchy:**
  - `postgres` (port `5432`) initiates schema and seeds initial admin.
  - `auth-service` (`8001`), `product-service` (`8002`), and `blockchain-service` (`8003`) start once DB is healthy.
  - `api-gateway` (`8000`) starts only after all core backend services are healthy.
  - `frontend` (Nginx Alpine, port `80`) launches once the gateway is ready.
* **Current Status:** All 6 containers are active and healthy on `product-verify-network`.

---

## Slide 6: Quality Assurance, UI Telemetry & Deliverable Suite
* **Title:** Automated Testing Suite, Live Telemetry, and Operational Artifacts
* **Postman Test Suite (`postman_collection.json`):**
  - Automated assertions validating active/healthy status across all microservices.
  - Real-time test of Ethereum Sepolia Web3 RPC connection (asserts Chain ID `11155111` and live block height).
  - Complete automated flows: Admin/Manufacturer login, token extraction, catalog creation, on-chain registration, and positive/negative verification tests.
* **User Interface (`UI_USER_GUIDE.md`):**
  - Real-time network indicator in top-right header (🟢 Sepolia).
  - Dedicated **"🌐 Network"** telemetry dashboard inspecting contract state and wallet authorization.
  - Step-by-step UI registration, login, and verification guide with sample test data.
* **Payload Examples (`PRODUCT_REGISTRATION_EXAMPLES.md` & `examples/products_sample.json`):**
  - Ready-to-use payloads for Luxury Goods, Pharmaceuticals, Flagship Electronics, and Automotive components.
