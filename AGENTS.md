# AI Agent Guidelines & Context Reference

## Authoritative Source of Truth
Whenever analyzing this codebase, designing new features, debugging issues, or answering any questions about the product, **you MUST refer to [OKF.md](OKF.md) (Operational Knowledge File)** as the primary source of truth. When OKF.md and the code disagree, trust the code and update OKF.md.

### Key Rules & Invariants
1. **Canonical Hashing:** The fingerprint is `keccak256(abi.encode(productId, serialNumber, model, batch))`, matching `ProductRegistry.hashProduct`. Do not use `abi.encodePacked` for these four strings: dynamic fields can be shifted into each other and collide. The pipe form `productId|serialNumber|model|batch` is a human label, not the hash preimage.
2. **Hybrid Architecture:** The Ethereum smart contract (`ProductRegistry.sol`) stores only 32-byte hashes (`bytes32`). All rich mutable metadata resides in PostgreSQL 16. A hash match means the submitted strings match a registered record. It does not prove a physical label is unique.
3. **Role Enforcement:**
   - Admin (`onlyOwner` on-chain, JWT `admin` off-chain): whitelists manufacturers. The UI signs `addManufacturer` in MetaMask with the owner account. Public signup cannot grant `admin` or `manufacturer`.
   - Manufacturer (`onlyManufacturer`): registers products and can deactivate their own. Catalog updates require `created_by` to match `x-user-id`, which the API gateway copies from the JWT. `is_active` is not changed in the database for an on-chain product until a `ProductDeactivated` receipt is checked.
   - Public / Consumer: uses zero-gas `view` functions (`verifyProduct`) to compare a submitted fingerprint with the stored one.
4. **Signing:** Product registration and recall are signed in MetaMask. The browser then calls `mark-on-chain` or `confirm-deactivation`. The product service updates the row only after the receipt matches. The gateway strips incoming `x-user-*` headers before setting them from the token. `created_by` is read from that header, not from the query string.
5. **Web3 calls:** Sync web3 work runs in a worker thread. Service-signed transactions use `get_transaction_count(address, "pending")` and a per-address lock around broadcast.
6. **API Gateway Routing:** External requests enter through API Gateway (`:8000`). Downstream ports trust `x-user-*` and should not be exposed off the machine.
7. **Observability:** Services emit structured JSON to stdout and rotating files under `/app/logs`. Loki and Grafana are commented out in `docker-compose.yml` and are not part of the default stack. There is no `monitoring/` directory in this repo.

Refer to [OKF.md](OKF.md) for the endpoint catalogs, database schemas, sequence diagrams, and Q&A knowledge base. Demo secrets (JWT secret, `postgres`/`postgres`, admin password `admin123`, Anvil account 0) are public and local-only.
