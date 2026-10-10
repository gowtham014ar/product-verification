# Step 3 — Service Guide & Testing Manual

This guide explains how to enable, run, and test every individual microservice in the Product Verification Platform. It includes standalone startup instructions, Docker Compose execution, and working copy-pasteable API examples with realistic payloads and expected responses.

---

## 1. How to Enable & Run the Services

You can run the platform in two ways:
1. **Full Stack with Docker Compose** (Recommended for end-to-end integration and demos).
2. **Individual Services in Standalone Mode** (Ideal for rapid local feature development and debugging).

---

### Option A: Running the Full Stack (Docker Compose)

Ensure your `.env` file is configured (copy from `.env.example`). Then start all containers:

```bash
# Start all containers in the background
docker compose up -d

# Check running container status
docker compose ps

# View live consolidated logs across all services
docker compose logs -f
```

To run only specific dependent services (e.g., PostgreSQL, Loki, and Auth Service):
```bash
docker compose up -d postgres loki auth-service
```

---

### Option B: Running Individual Services via Per-Service Docker Compose (Common DB)

Each service has its own dedicated `docker-compose.yml` that connects to a **shared, common PostgreSQL database** over the `product-verify-network`:

#### 1. Start the Common PostgreSQL Database
From the `database/` folder:
```bash
cd database
docker compose up -d
cd ..
```
*(Starts the common PostgreSQL database, initializes tables and seeds the admin user)*

#### 2. Start Any Specific Service in Isolation
Now you can start any service independently using its own `docker-compose.yml`:

```bash
# Run only Auth Service
cd services/auth-service
docker compose up -d

# Run only Product Service
cd services/product-service
docker compose up -d

# Run only Blockchain Service
cd services/blockchain-service
docker compose up -d

# Run only API Gateway
cd services/api-gateway
docker compose up -d

# Run only Frontend UI
cd frontend
docker compose up -d
```

---

### Option C: Running Individual Services Locally (Standalone Python)

If you prefer to run services outside Docker on your host machine:

#### 1. Setup Common Python Environment
From the repository root:
```bash
# Create and activate virtual environment
python -m venv .venv
# On Windows PowerShell:
.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

# Install shared requirements and service packages
pip install fastapi uvicorn[standard] sqlalchemy asyncpg psycopg2-binary web3 python-jose[cryptography] passlib[bcrypt] pydantic-settings httpx
```

#### 2. Start PostgreSQL & Loki (Dependencies)
```bash
docker compose up -d postgres loki
```

#### 3. Run a Specific Service
Set the appropriate environment variables and launch Uvicorn for that service:

##### Auth Service (Port 8001):
```bash
$env:DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/product_verification"
$env:JWT_SECRET_KEY="your-super-secret-key-32-chars-min"
$env:SERVICE_NAME="auth-service"
$env:LOG_DIR="./logs"
$env:PYTHONPATH=".;./services/common"
uvicorn services.auth-service.main:app --host 0.0.0.0 --port 8001 --reload
```

##### Product Service (Port 8002):
```bash
$env:DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/product_verification"
$env:JWT_SECRET_KEY="your-super-secret-key-32-chars-min"
$env:BLOCKCHAIN_SERVICE_URL="http://localhost:8003"
$env:SERVICE_NAME="product-service"
$env:LOG_DIR="./logs"
$env:PYTHONPATH=".;./services/common"
uvicorn services.product-service.main:app --host 0.0.0.0 --port 8002 --reload
```

##### Blockchain Service (Port 8003):
```bash
$env:ETH_RPC_URL="https://sepolia.infura.io/v3/YOUR_INFURA_KEY"
$env:CONTRACT_ADDRESS="0xYourDeployedContractAddress"
$env:OWNER_PRIVATE_KEY="0xYourMetaMaskPrivateKey"
$env:CHAIN_ID="11155111"
$env:SERVICE_NAME="blockchain-service"
$env:LOG_DIR="./logs"
$env:PYTHONPATH=".;./services/common"
uvicorn services.blockchain-service.main:app --host 0.0.0.0 --port 8003 --reload
```

##### API Gateway (Port 8000):
```bash
$env:AUTH_SERVICE_URL="http://localhost:8001"
$env:PRODUCT_SERVICE_URL="http://localhost:8002"
$env:BLOCKCHAIN_SERVICE_URL="http://localhost:8003"
$env:SERVICE_NAME="api-gateway"
$env:LOG_DIR="./logs"
$env:PYTHONPATH=".;./services/common"
uvicorn services.api-gateway.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 2. Health Checks Across All Services

Every service exposes a standardized `/health` endpoint:

```bash
# 1. API Gateway
curl http://localhost:8000/health
# Response: {"status":"ok","service":"api-gateway"}

# 2. Auth Service
curl http://localhost:8001/health
# Response: {"status":"ok","service":"auth-service"}

# 3. Product Service
curl http://localhost:8002/health
# Response: {"status":"ok","service":"product-service"}

# 4. Blockchain Service
curl http://localhost:8003/health
# Response: {"status":"ok","service":"blockchain-service"}
```

---

## 3. Working Testing Examples for Each Service

All client interactions typically go through the **API Gateway on port 8000** at `/api/...`.  
You can also test downstream services directly on their respective ports (`8001`, `8002`, `8003`) during component testing.

---

### 3.1. Authentication Service (`/api/auth`)

#### A. Register a Manufacturer User
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "manufacturer@acme.com",
    "password": "SecurePassword123!",
    "full_name": "ACME Electronics Corp",
    "role": "manufacturer",
    "wallet_address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
  }'
```
**Expected Response (`201 Created`):**
```json
{
  "id": "e2a48d88-3ef7-47b2-b13c-74591a27e310",
  "email": "manufacturer@acme.com",
  "full_name": "ACME Electronics Corp",
  "role": "manufacturer",
  "wallet_address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
  "is_active": true
}
```

#### B. Register an Admin User
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@platform.com",
    "password": "AdminMasterKey2026!",
    "full_name": "Platform Administrator",
    "role": "admin"
  }'
```

#### C. Login & Obtain JWT Token (Admin / Manufacturer)
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@productverify.local",
    "password": "admin123"
  }'
# (Or use "admin@productverify.com" / "admin123")
```
**Expected Response (`200 OK`):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "role": "admin",
  "user_id": "dd62b9f5-74ae-4aaf-8b34-1ef9973d5c1a"
}
```
> **Tip**: Save this admin token in a shell variable to authorize on-chain operations:
> `export ADMIN_TOKEN="eyJhbGciOi..."` (Linux/macOS) or `$ADMIN_TOKEN="eyJhbGciOi..."` (PowerShell)

#### D. Fetch Current User Profile (`/me`)
```bash
curl -X GET http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer $TOKEN"
```

---

### 3.2. Product Service (`/api/products`)

#### A. Create a New Product (Manufacturer or Admin Only)
```bash
curl -X POST http://localhost:8000/api/products/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "product_id": "PROD-2026-X1",
    "name": "Acme Ultra Smartwatch",
    "serial_number": "SN-987654321",
    "model": "WATCH-V2-PRO",
    "batch": "BATCH-2026-Q1"
  }'
```
**Expected Response (`201 Created`):**
```json
{
  "id": "c71f92e4-981e-450a-8bf7-46329bf311b5",
  "product_id": "PROD-2026-X1",
  "name": "Acme Ultra Smartwatch",
  "serial_number": "SN-987654321",
  "model": "WATCH-V2-PRO",
  "batch": "BATCH-2026-Q1",
  "product_hash": "0x5e2c56a81b...",
  "on_chain": false,
  "tx_hash": null,
  "created_by": "e2a48d88-3ef7-47b2-b13c-74591a27e310",
  "created_at": "2026-10-04T13:00:00Z"
}
```

#### B. List All Products (Public Read)
```bash
curl -X GET "http://localhost:8000/api/products/?skip=0&limit=10"
```

#### C. Get Product by Product ID (Public Read)
```bash
curl -X GET http://localhost:8000/api/products/PROD-2026-X1
```

#### D. Role Enforcement Test (Expected Forbidden 403)
Attempting to create a product using a user account with the `customer` role:
```bash
curl -X POST http://localhost:8000/api/products/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $CUSTOMER_TOKEN" \
  -d '{ ... }'
```
**Expected Response:** `403 Forbidden` (`{"detail": "Insufficient permissions"}`).

---

### 3.3. Blockchain Service (`/api/blockchain`)

#### A. Query Network Telemetry
Check if the service is successfully communicating with the Ethereum node (Sepolia or Anvil):
```bash
curl -X GET http://localhost:8000/api/blockchain/network
```
**Expected Response:**
```json
{
  "connected": true,
  "chain_id": 11155111,
  "block_number": 6842103,
  "contract": "0x1234567890123456789012345678901234567890",
  "rpc": "https://sepolia.infura.io/v3/YOUR_INFURA_KEY"
}
```

#### B. Authorize a Manufacturer On-Chain (Owner / Admin Only)
Authorizing a manufacturer writes directly to the Ethereum smart contract (`ProductRegistry.sol::addManufacturer`), allowing this manufacturer wallet to sign product registrations.

> [!IMPORTANT]
> **Difference Between Postman User Registration vs. Smart Contract Whitelisting:**
> 1. `POST /api/auth/register` (Auth Service): Registers a user profile in **PostgreSQL**. This provides login credentials (`email`, `password`) and a JWT token. It **does NOT** write to the Ethereum smart contract!
> 2. `POST /api/blockchain/manufacturers` (Blockchain Service): Writes to the **Ethereum Smart Contract**. This grants the manufacturer's wallet on-chain rights (`mapping(address => Manufacturer)`).
> 
> *The UI "Manufacturers" table queries `GET /api/blockchain/manufacturers` directly from the smart contract! If a manufacturer was only registered via `/api/auth/register`, they will NOT appear in the UI or on-chain until this blockchain endpoint is called.*

**cURL / Postman Request:**
```bash
curl -X POST http://localhost:8000/api/blockchain/manufacturers \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "wallet_address": "0x27b1FdB04752BBC536007a920D24ACB045561c26",
    "manufacturer_id": "MFG001",
    "name": "Micro Laboratories",
    "owner_private_key": "0x<YOUR_32_BYTE_HEX_PRIVATE_KEY>"
  }'
```

**Field Specifications:**
* `wallet_address`: **20 bytes** (42 hex characters with `0x`, e.g. `0x27b1FdB04752BBC536007a920D24ACB045561c26`). This is the manufacturer's public Ethereum address.
* `manufacturer_id`: Unique business identifier string (e.g. `MFG001`).
* `name`: Company name string (e.g. `Micro Laboratories`).
* `owner_private_key`: **32 bytes** (66 hex characters with `0x`, e.g. `0x4f3edf983ac636a65a842ce7c78d9aa706d3b113bce9c46f30d7d21715b23b1d`). Exported from MetaMask (`Account Details → Show Private Key`). If left blank, defaults to `OWNER_PRIVATE_KEY` in `.env`.

> [!CAUTION]
> **Common Error: "The private key must be exactly 32 bytes long, instead of 20 bytes"**  
> This error happens when a **20-byte public wallet address** (`0x` + 40 characters = 42 total) is accidentally entered into the `owner_private_key` or `manufacturer_private_key` field instead of a **32-byte secret private key** (`0x` + 64 characters = 66 total).
>
> | Type | Byte Size | Character Length | Example Format | Purpose |
> |---|---|---|---|---|
> | **Wallet Address (Public)** | 20 bytes | 42 chars | `0x27b1FdB04752BBC536007a920D24ACB045561c26` | Public recipient / identity |
> | **Private Key (Secret)** | 32 bytes | 66 chars | `0x4f3edf983ac... (64 hex digits)` | Signs EVM transactions |

**Expected Response (`200 OK`):**
```json
{
  "tx_hash": "0x8f7d9c12b3a4e5f67890abcdef1234567890abcdef1234567890abcdef123456",
  "status": "added"
}
```

#### C. List All On-Chain Manufacturers (Public Read)
Queries `ProductRegistry.sol::getAllManufacturers()`:
```bash
curl -X GET http://localhost:8000/api/blockchain/manufacturers
```
**Expected Response:**
```json
[
  {
    "id": "0x4d46473030310000000000000000000000000000000000000000000000000000",
    "name": "Micro Laboratories",
    "wallet": "0x27b1FdB04752BBC536007a920D24ACB045561c26",
    "added_at": 1728384912,
    "active": true
  }
]
```

#### D. Check if a Wallet is Authorized
```bash
curl -X GET http://localhost:8000/api/blockchain/manufacturers/0x27b1FdB04752BBC536007a920D24ACB045561c26/is-authorized
```
**Expected Response:**
```json
{
  "wallet": "0x27b1FdB04752BBC536007a920D24ACB045561c26",
  "is_manufacturer": true
}
```

#### D. Register Product On-Chain (Manufacturer Signed)
Provide the manufacturer's private key to sign the transaction:
```bash
curl -X POST http://localhost:8000/api/blockchain/products/register \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $MANUFACTURER_TOKEN" \
  -d '{
    "product_id": "PROD-2026-X1",
    "serial_number": "SN-987654321",
    "model": "WATCH-V2-PRO",
    "batch": "BATCH-2026-Q1",
    "manufacturer_private_key": "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"
  }'
```
**Expected Response:**
```json
{
  "tx_hash": "0x3a4b5c6d7e8f90123456789abcdef1234567890abcdef...",
  "status": "confirmed"
}
```

#### E. Verify Authentic Product (Public Read — Zero Gas)
No token or private key needed:
```bash
curl -X POST http://localhost:8000/api/blockchain/products/verify \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": "PROD-2026-X1",
    "serial_number": "SN-987654321",
    "model": "WATCH-V2-PRO",
    "batch": "BATCH-2026-Q1"
  }'
```
**Expected Response (`Authentic`):**
```json
{
  "is_authentic": true,
  "manufacturer": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
  "registered_at": 1728043200,
  "active": true,
  "product_hash": "0x5e2c56a81b..."
}
```

#### F. Verify Counterfeit or Tampered Product
Submit the product with an altered serial number (`SN-COUNTERFEIT`):
```bash
curl -X POST http://localhost:8000/api/blockchain/products/verify \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": "PROD-2026-X1",
    "serial_number": "SN-COUNTERFEIT",
    "model": "WATCH-V2-PRO",
    "batch": "BATCH-2026-Q1"
  }'
```
**Expected Response (`Tampered / Counterfeit Detected`):**
```json
{
  "is_authentic": false,
  "manufacturer": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
  "registered_at": 1728043200,
  "active": true,
  "product_hash": "0x9999999999..."
}
```
*(Notice `is_authentic: false` because the calculated hash does not match the on-chain recorded hash).*

#### G. Deactivate a Product (Recall / Stolen)
```bash
curl -X POST http://localhost:8000/api/blockchain/products/deactivate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $MANUFACTURER_TOKEN" \
  -d '{
    "product_id": "PROD-2026-X1",
    "signer_private_key": "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"
  }'
```
**Expected Response:**
```json
{
  "tx_hash": "0x1234def...",
  "status": "deactivated"
}
```

---

## 4. Frontend UI Testing

The frontend is served automatically via Docker Compose on port `80` (or open `frontend/index.html` in your browser).

### Step-by-step UI testing walkthrough:
1. **Open Frontend**: Navigate to `http://localhost`.
2. **Network Check**: Click the **Network** tab to confirm the green "Connected" badge with the chain ID and latest block number.
3. **Login / Register**: Click the **Login** button at the top right:
   - Register a new manufacturer account or sign in.
   - The UI stores the JWT in `localStorage` and shows your user role badge.
4. **Register Product**:
   - Go to the **Register Product** tab.
   - Enter Product ID, Name, Serial Number, Model, and Batch.
   - Paste your manufacturer private key.
   - Click **Register on Blockchain**. The UI creates the catalog entry and submits the blockchain transaction, displaying the transaction hash.
5. **Verify Product**:
   - Go to the **Verify Product** tab.
   - Enter the exact same details and click **Verify Authenticity**.
   - See the verified badge with the timestamp and manufacturer address.
   - Change one character of the serial number and click **Verify** again—see the warning badge indicating authenticity failure.

---

## 5. Log & Monitoring Verification

### 1. View Local Fallback Logs
Logs are saved on the disk in each service's log directory:
```bash
# In Docker:
docker exec -it product-verify-gateway tail -n 20 /app/logs/api-gateway.log
docker exec -it product-verify-blockchain tail -n 20 /app/logs/blockchain-service.log

# On Host:
tail -f services/api-gateway/logs/api-gateway.log
```

### 2. View Grafana Dashboards
- Open `http://localhost:3000` in your browser.
- Login with username `admin`, password `admin123`.
- Navigate to **Dashboards** $\rightarrow$ **Product Verification — Service Logs**.
- You will see live visual panels for:
  - Real-time Service Log Stream
  - Errors & Exceptions
  - Blockchain Transactions & Verifications
  - User Authentication Audits
