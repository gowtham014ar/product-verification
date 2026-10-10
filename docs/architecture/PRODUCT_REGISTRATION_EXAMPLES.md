# Product Registration Examples & Payloads Guide

This guide provides concrete, real-world examples for registering products in the **Product Verification System**, covering both the off-chain database record and on-chain Ethereum cryptographic registration.

---

## 1. Cryptographic Invariant & Canonical Order

Before submitting any product, the system calculates the deterministic cryptographic fingerprint using **Keccak-256**:

```text
Canonical String: productId|serialNumber|model|batch
Packing:          keccak256(abi.encodePacked(productId, serialNumber, model, batch))
```

> [!IMPORTANT]
> The four fields must match **character-for-character** during verification. If an attacker modifies even a single character in the off-chain database (e.g. changing serial or batch), the calculated hash diverges from the blockchain record, immediately flagging the item as **Counterfeit**.

---

## 2. Realistic Product Samples Across Verticals

### Vertical A: Luxury Goods (Swiss Watch)
* **Product ID:** `LUX-WAT-001`
* **Name:** `Submariner Oyster Perpetual 41mm`
* **Serial Number:** `ROX-882910-K`
* **Model:** `SUB-126610LN`
* **Batch:** `2026-CH-04`
* **Description:** `Oystersteel luxury diving timepiece with black Cerachrom bezel and luminescent display.`
* **Canonical String:** `LUX-WAT-001|ROX-882910-K|SUB-126610LN|2026-CH-04`

#### 1. Off-Chain Database Creation Payload (`POST /api/products/`)
```json
{
  "product_id": "LUX-WAT-001",
  "name": "Submariner Oyster Perpetual 41mm",
  "serial_number": "ROX-882910-K",
  "model": "SUB-126610LN",
  "batch": "2026-CH-04",
  "description": "Oystersteel luxury diving timepiece with black Cerachrom bezel and luminescent display."
}
```

#### 2. On-Chain Blockchain Registration Payload (`POST /api/blockchain/products/register`)
```json
{
  "product_id": "LUX-WAT-001",
  "serial_number": "ROX-882910-K",
  "model": "SUB-126610LN",
  "batch": "2026-CH-04",
  "manufacturer_private_key": "{{MANUFACTURER_PRIVATE_KEY}}"
}
```

#### 3. Public Verification Payload (`POST /api/blockchain/products/verify`)
```json
{
  "product_id": "LUX-WAT-001",
  "serial_number": "ROX-882910-K",
  "model": "SUB-126610LN",
  "batch": "2026-CH-04"
}
```

---

### Vertical B: Pharmaceuticals (Insulin Glargine)
* **Product ID:** `PHARM-INS-401`
* **Name:** `Lantus Solostar Insulin Pen 100U/mL`
* **Serial Number:** `SN-LT-2026-99014`
* **Model:** `SOLO-3ML`
* **Batch:** `BATCH-2026-Q1-EUR`
* **Description:** `Sterile subcutaneous injection solution; temperature-controlled cold chain item.`
* **Canonical String:** `PHARM-INS-401|SN-LT-2026-99014|SOLO-3ML|BATCH-2026-Q1-EUR`

#### 1. Off-Chain Database Creation Payload (`POST /api/products/`)
```json
{
  "product_id": "PHARM-INS-401",
  "name": "Lantus Solostar Insulin Pen 100U/mL",
  "serial_number": "SN-LT-2026-99014",
  "model": "SOLO-3ML",
  "batch": "BATCH-2026-Q1-EUR",
  "description": "Sterile subcutaneous injection solution; temperature-controlled cold chain item."
}
```

#### 2. On-Chain Blockchain Registration Payload (`POST /api/blockchain/products/register`)
```json
{
  "product_id": "PHARM-INS-401",
  "serial_number": "SN-LT-2026-99014",
  "model": "SOLO-3ML",
  "batch": "BATCH-2026-Q1-EUR",
  "manufacturer_private_key": "{{MANUFACTURER_PRIVATE_KEY}}"
}
```

#### 3. Public Verification Payload (`POST /api/blockchain/products/verify`)
```json
{
  "product_id": "PHARM-INS-401",
  "serial_number": "SN-LT-2026-99014",
  "model": "SOLO-3ML",
  "batch": "BATCH-2026-Q1-EUR"
}
```

---

### Vertical C: High-End Electronics (Flagship Laptop)
* **Product ID:** `ELEC-LAP-772`
* **Name:** `MacBook Pro 16-inch M3 Max`
* **Serial Number:** `C02ZX919MD6R`
* **Model:** `A2991-M3MAX`
* **Batch:** `B2026-OCT-FOX`
* **Description:** `Space Black 16-inch liquid retina XDR, 64GB Unified RAM, 1TB SSD.`
* **Canonical String:** `ELEC-LAP-772|C02ZX919MD6R|A2991-M3MAX|B2026-OCT-FOX`

#### 1. Off-Chain Database Creation Payload (`POST /api/products/`)
```json
{
  "product_id": "ELEC-LAP-772",
  "name": "MacBook Pro 16-inch M3 Max",
  "serial_number": "C02ZX919MD6R",
  "model": "A2991-M3MAX",
  "batch": "B2026-OCT-FOX",
  "description": "Space Black 16-inch liquid retina XDR, 64GB Unified RAM, 1TB SSD."
}
```

#### 2. On-Chain Blockchain Registration Payload (`POST /api/blockchain/products/register`)
```json
{
  "product_id": "ELEC-LAP-772",
  "serial_number": "C02ZX919MD6R",
  "model": "A2991-M3MAX",
  "batch": "B2026-OCT-FOX",
  "manufacturer_private_key": "{{MANUFACTURER_PRIVATE_KEY}}"
}
```

#### 3. Public Verification Payload (`POST /api/blockchain/products/verify`)
```json
{
  "product_id": "ELEC-LAP-772",
  "serial_number": "C02ZX919MD6R",
  "model": "A2991-M3MAX",
  "batch": "B2026-OCT-FOX"
}
```

---

### Vertical D: Automotive / Performance Components
* **Product ID:** `AUTO-BRK-990`
* **Name:** `Brembo Carbon Ceramic Brake Rotor 380mm`
* **Serial Number:** `BRM-CCM-2026-781`
* **Model:** `CCM-GT3-380`
* **Batch:** `LOT-IT-2026-B`
* **Description:** `Track-grade lightweight carbon-silicon carbide composite brake disc assembly.`
* **Canonical String:** `AUTO-BRK-990|BRM-CCM-2026-781|CCM-GT3-380|LOT-IT-2026-B`

#### 1. Off-Chain Database Creation Payload (`POST /api/products/`)
```json
{
  "product_id": "AUTO-BRK-990",
  "name": "Brembo Carbon Ceramic Brake Rotor 380mm",
  "serial_number": "BRM-CCM-2026-781",
  "model": "CCM-GT3-380",
  "batch": "LOT-IT-2026-B",
  "description": "Track-grade lightweight carbon-silicon carbide composite brake disc assembly."
}
```

#### 2. On-Chain Blockchain Registration Payload (`POST /api/blockchain/products/register`)
```json
{
  "product_id": "AUTO-BRK-990",
  "serial_number": "BRM-CCM-2026-781",
  "model": "CCM-GT3-380",
  "batch": "LOT-IT-2026-B",
  "manufacturer_private_key": "{{MANUFACTURER_PRIVATE_KEY}}"
}
```

#### 3. Public Verification Payload (`POST /api/blockchain/products/verify`)
```json
{
  "product_id": "AUTO-BRK-990",
  "serial_number": "BRM-CCM-2026-781",
  "model": "CCM-GT3-380",
  "batch": "LOT-IT-2026-B"
}
```

---

## 3. End-to-End Registration Commands via cURL

### Step 1: Sign in as Manufacturer or Admin to get JWT Token
```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@productverify.local",
    "password": "admin123"
  }'
```
Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "role": "admin",
  "user_id": "..."
}
```

### Step 2: Create Product in Off-chain PostgreSQL
```bash
curl -X POST "http://localhost:8000/api/products/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" \
  -d '{
    "product_id": "LUX-WAT-001",
    "name": "Submariner Oyster Perpetual 41mm",
    "serial_number": "ROX-882910-K",
    "model": "SUB-126610LN",
    "batch": "2026-CH-04",
    "description": "Oystersteel luxury diving timepiece with black Cerachrom bezel and luminescent display."
  }'
```

### Step 3: Register Hash On-Chain via Blockchain Service
```bash
curl -X POST "http://localhost:8000/api/blockchain/products/register" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" \
  -d '{
    "product_id": "LUX-WAT-001",
    "serial_number": "ROX-882910-K",
    "model": "SUB-126610LN",
    "batch": "2026-CH-04",
    "manufacturer_private_key": "<YOUR_MANUFACTURER_PRIVATE_KEY>"
  }'
```
Response:
```json
{
  "tx_hash": "0x4a9f3b1238dc...319",
  "status": "confirmed"
}
```

### Step 4: Verify Product Authenticity (Free View Call, Public)
```bash
curl -X POST "http://localhost:8000/api/blockchain/products/verify" \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": "LUX-WAT-001",
    "serial_number": "ROX-882910-K",
    "model": "SUB-126610LN",
    "batch": "2026-CH-04"
  }'
```
Response:
```json
{
  "is_authentic": true,
  "manufacturer": "0x124cc1e013d9959e68e7b221f4ac1369370e7ffb",
  "registered_at": 1728234812,
  "active": true,
  "product_hash": "0x98ef3..."
}
```
