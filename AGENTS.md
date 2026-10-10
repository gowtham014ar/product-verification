# AI Agent Guidelines & Context Reference

## Authoritative Source of Truth
Whenever analyzing this codebase, designing new features, debugging issues, or answering any questions about the product, **you MUST refer to [OKF.md](file:///d:/learning/sample-projects/product-verification/OKF.md) (Operational Knowledge File)** as the primary source of truth.

### Key Rules & Invariants
1. **Canonical Hashing:** Always respect the deterministic packing order:
   `keccak256(abi.encodePacked(productId, serialNumber, model, batch))`
   Human string representation: `productId|serialNumber|model|batch`.
2. **Hybrid Architecture:** The Ethereum smart contract (`ProductRegistry.sol`) stores only 32-byte hashes (`bytes32`). All rich mutable metadata resides in PostgreSQL 16.
3. **Role Enforcement:** 
   - Admin (`onlyOwner`): Manages manufacturers on-chain and oversees system telemetry.
   - Manufacturer (`onlyManufacturer`): Registers products and can deactivate their own products.
   - Public / Consumer: Uses zero-gas `view` functions (`verifyProduct`) to inspect authenticity.
4. **API Gateway Routing:** All external requests enter through API Gateway (`:8000`), which strips incoming `x-user-*` headers, validates JWTs, and injects trusted identity headers to downstream microservices.
5. **Observability:** Telemetry logs are pushed as structured JSON to Grafana Loki (`:3100`) with fallback to rotating local files (`/app/logs/`).

Refer to [OKF.md](file:///d:/learning/sample-projects/product-verification/OKF.md) for the full endpoint catalogs, database schemas, sequence diagrams, and Q&A knowledge base.
