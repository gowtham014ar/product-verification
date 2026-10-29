// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Script, console} from "forge-std/Script.sol";
import {ProductRegistry} from "../src/ProductRegistry.sol";

/// @notice Deploy ProductRegistry. The deployer becomes `owner`.
///
///   forge script contracts/script/Deploy.s.sol --rpc-url $ETH_RPC_URL --broadcast
///
/// `OWNER_PRIVATE_KEY` is read from the environment (0x-prefixed hex is accepted).
/// This script does not verify the source. After deployment, verify it yourself:
///
///   forge verify-contract <deployed-address> ProductRegistry \
///     --chain sepolia --etherscan-api-key $ETHERSCAN_API_KEY \
///     --watch
contract Deploy is Script {
    function run() external returns (ProductRegistry registry) {
        uint256 key = vm.envUint("OWNER_PRIVATE_KEY");
        vm.startBroadcast(key);
        registry = new ProductRegistry();
        vm.stopBroadcast();
        console.log("ProductRegistry", address(registry));
    }
}
