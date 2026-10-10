# Step 4 — Blockchain Setup & Configuration Guide

This guide explains in detail **what blockchain parameters exist**, **why they are needed**, **how to obtain them**, and **how to update them** in the project's configuration files.

---

## 1. Summary of Required Blockchain Parameters

The platform requires 4 core configuration values to communicate with an EVM blockchain:

| Parameter | Type / Format | Where to Configure | Purpose |
|---|---|---|---|
| `ETH_RPC_URL` | URL (`https://...` or `http://...`) | `.env`, `docker-compose.yml` | The RPC node provider URL that `web3.py` connects to for reading and writing data to Ethereum. |
| `CONTRACT_ADDRESS` | 42-char Hex (`0x...`) | `.env`, `docker-compose.yml` | The on-chain address where your `ProductRegistry.sol` contract is deployed. |
| `CHAIN_ID` | Integer | `.env`, `docker-compose.yml` | Network identifier (`11155111` for Sepolia, `31337` for local Anvil, `1` for Mainnet). Prevents replay attacks across different chains. |
| `OWNER_PRIVATE_KEY` | 64-char Hex (prefixed with `0x`) | `.env`, `docker-compose.yml` | Private key of the contract deployer. Used by the backend to sign transactions that add or remove authorized manufacturers. |
| `Contract ABI` | JSON Array | `services/blockchain-service/contracts_abi/ProductRegistry.json` | Interface specification defining the contract's methods and event structures for `web3.py`. |

---

## 2. Step-by-Step: How to Obtain and Configure Each Detail

---

### Step 2.1: Setup MetaMask & Export Wallet Credentials

1. Install the [MetaMask Browser Extension](https://metamask.io/).
2. Create a new wallet (or use an existing development wallet).
3. **Switch Network to Sepolia Testnet**:
   - In MetaMask, click the network dropdown in the top-left corner.
   - Enable **Show test networks**.
   - Select **Sepolia**.
4. **Copy Public Wallet Address**:
   - Click on your account name (e.g., `Account 1`) to copy your address (`0x...`). This address will become the **Contract Owner**.
5. **Export Your Private Key**:
   - Click the three dots icon (`⋮`) next to your account name $\rightarrow$ **Account Details**.
   - Click **Show Private Key**.
   - Enter your MetaMask password and hold the button to reveal the private key.
   - Copy the private key (a 64-character hexadecimal string).
   - Ensure it starts with `0x`. If it does not, prepend `0x` to it.
   > ⚠️ **CRITICAL WARNING**: Never share this private key, commit it to GitHub, or use a wallet with real mainnet assets. Keep a dedicated development wallet for testnet projects.

---

### Step 2.2: Get Free Sepolia Test ETH

Transactions on Sepolia require test ETH to pay for gas. You can claim free Sepolia ETH from any of these faucets:

- **Google Cloud Web3 Faucet** (Fastest, no login required): [cloud.google.com/application/web3/faucet/ethereum/sepolia](https://cloud.google.com/application/web3/faucet/ethereum/sepolia)
- **Alchemy Sepolia Faucet**: [sepoliafaucet.com](https://sepoliafaucet.com)
- **Infura Sepolia Faucet**: [www.infura.io/faucet/sepolia](https://www.infura.io/faucet/sepolia)
- **Sepolia PoW Faucet**: [sepolia-faucet.pk910.de](https://sepolia-faucet.pk910.de)

Paste your public wallet address from Step 2.1 into the faucet and request 0.1 to 0.5 Sepolia ETH. Once confirmed, you will see the balance appear in MetaMask.

---

### Step 2.3: Get Your Ethereum RPC Provider URL (`ETH_RPC_URL`)

To allow the Python microservice to communicate with the Sepolia network, you need an RPC URL.

#### Option 1: Infura (Recommended)
1. Sign up for free at [infura.io](https://www.infura.io).
2. Create a new API Key $\rightarrow$ Select **Web3 API** $\rightarrow$ Network: **Ethereum**.
3. Under **Endpoints**, select **Sepolia**.
4. Copy the URL:
   ```
   https://sepolia.infura.io/v3/YOUR_INFURA_API_KEY
   ```

#### Option 2: Alchemy
1. Sign up for free at [alchemy.com](https://www.alchemy.com).
2. Create an App $\rightarrow$ Chain: **Ethereum** $\rightarrow$ Network: **Ethereum Sepolia**.
3. Click **API Key** and copy the HTTPS URL:
   ```
   https://eth-sepolia.g.alchemy.com/v2/YOUR_ALCHEMY_KEY
   ```

#### Option 3: Public Free RPC (No signup required)
You can use public RPC endpoints for quick testing, though rate limits may apply:
```
https://rpc.sepolia.org
https://ethereum-sepolia-rpc.publicnode.com
```

---

### Step 2.4: Deploy the Smart Contract (`ProductRegistry.sol`)

#### Deploying via Remix IDE (Easiest & Fastest)
1. Open [Remix IDE](https://remix.ethereum.org) in your browser.
2. In the file explorer, create a new file named `ProductRegistry.sol`.
3. Copy and paste the entire code from `contracts/src/ProductRegistry.sol`.
4. Go to the **Solidity Compiler** tab on the left:
   - Select compiler version `0.8.20`.
   - Click **Compile ProductRegistry.sol**.
5. Go to the **Deploy & Run Transactions** tab:
   - Under **Environment**, choose **Injected Provider - MetaMask**.
   - MetaMask will prompt you to connect. Ensure your network is set to **Sepolia** and your account has Sepolia ETH.
   - Ensure the contract selected is `ProductRegistry`.
   - Click the orange **Deploy** button.
   - Confirm the transaction in the MetaMask popup.
6. **Copy the Contract Address**:
   - Once the transaction confirms, expand the **Deployed Contracts** section at the bottom.
   - Click the copy icon next to `ProductRegistry at 0x...`.
   - This is your `CONTRACT_ADDRESS`.

---

#### Deploying via Foundry (CLI Alternative)
If you have Foundry installed locally:
```bash
# In the contracts/ directory
forge build

forge script script/Deploy.s.sol:DeployScript \
  --rpc-url https://sepolia.infura.io/v3/YOUR_INFURA_KEY \
  --broadcast \
  --private-key 0xYOUR_METAMASK_PRIVATE_KEY
```
Foundry will log the deployed contract address in the terminal.

---

### Step 2.5: Update the Configuration Files

Now inject these parameters into your project.

#### 1. Update `.env`
Create or edit `.env` in the project root:

```bash
# Copy from template if not already present
cp .env.example .env
```

Set the values:
```ini
# Ethereum RPC Provider
ETH_RPC_URL=https://sepolia.infura.io/v3/your_actual_infura_key_here

# Deployed Contract Address from Remix or Foundry
CONTRACT_ADDRESS=0x71C2B80F1f24d77053e1a0642f4D3507B5786C10

# MetaMask Private Key of the deployer (Owner)
OWNER_PRIVATE_KEY=0x4f3edf983ac636a65a842ce7c78d9aa706d3b113bce9c46f30d7d21715b23b1d

# Chain ID (11155111 for Sepolia)
CHAIN_ID=11155111

# Secret key for JWT generation
JWT_SECRET_KEY=9a48d281f6e2b104c995ad3e120d5718a3c9b74052e468da21b0e9f1a7b6c5d4
```

#### 2. Verify Contract ABI
The contract ABI is already pre-generated and stored in:
`services/blockchain-service/contracts_abi/ProductRegistry.json`

If you ever add new methods or change function signatures in `ProductRegistry.sol`:
1. In Remix, go to the **Compile** tab and click **ABI** (bottom copy button).
2. Paste the updated JSON into `services/blockchain-service/contracts_abi/ProductRegistry.json`.

---

### Step 2.6: Test and Verify the Blockchain Connection

Once you have updated `.env`, restart the services:

```bash
docker compose up -d --build blockchain-service api-gateway
```

Now execute the network health check:
```bash
curl http://localhost:8000/api/blockchain/network
```

**Expected Successful Response:**
```json
{
  "connected": true,
  "chain_id": 11155111,
  "block_number": 6842918,
  "contract": "0x71C2B80F1f24d77053e1a0642f4D3507B5786C10",
  "rpc": "https://sepolia.infura.io/v3/..."
}
```

If `connected: true` and `block_number` is a positive integer, your blockchain integration is 100% active and operational!

---

## 3. Alternative: Running Completely Offline with Local Anvil

If you do not have Sepolia test ETH, or want instant local development without internet dependency, you can use Foundry's built-in **Anvil** blockchain.

### 1. Start Anvil
```bash
anvil --port 8545
```
Anvil prints 10 pre-funded test accounts and their private keys.

### 2. Update `.env` for Anvil:
```ini
ETH_RPC_URL=http://host.docker.internal:8545
CONTRACT_ADDRESS=0x5FbDB2315678afecb367f032d93F642f64180aa3
OWNER_PRIVATE_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
CHAIN_ID=31337
```

### 3. Deploy Contract to Anvil:
```bash
forge create contracts/src/ProductRegistry.sol:ProductRegistry \
  --rpc-url http://localhost:8545 \
  --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
```
Update `CONTRACT_ADDRESS` in `.env` with the deployed address output by the command.

---

## 4. Troubleshooting Common Blockchain Issues

| Issue / Error | Root Cause | Solution |
|---|---|---|
| `"web3 not connected"` | Invalid `ETH_RPC_URL` or network connectivity failure. | Check your Infura/Alchemy API key. Ensure no trailing whitespace or extra quotes in `.env`. |
| `"Contract not loaded"` | `CONTRACT_ADDRESS` is zero address (`0x00...`) or empty. | Deploy the contract first and paste the real 42-character address into `.env`. |
| `"insufficient funds for gas * price + value"` | Deployer or manufacturer wallet balance is 0 ETH. | Claim test ETH from a Sepolia faucet (Section 2.2). |
| `"Transaction reverted: ..."` | On-chain revert condition triggered: e.g., manufacturer not authorized, or product ID already exists. | 1. Ensure the wallet was added via `POST /api/blockchain/manufacturers`.<br/>2. Ensure you use a unique `product_id`. |
| `"nonce too low"` | Consecutive transactions submitted before previous mined. | Wait for the previous transaction receipt to confirm before firing the next write. |
| `"401 Unauthorized" on RPC` | Expired or incorrect Infura/Alchemy API key. | Generate a fresh project key in your Infura/Alchemy developer console. |
