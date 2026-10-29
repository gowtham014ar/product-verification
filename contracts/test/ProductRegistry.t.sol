// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Test} from "forge-std/Test.sol";
import {ProductRegistry} from "../src/ProductRegistry.sol";

contract ProductRegistryTest is Test {
    ProductRegistry internal registry;
    address internal manufacturer = makeAddr("manufacturer");
    address internal otherManufacturer = makeAddr("other");
    address internal stranger = makeAddr("stranger");

    function setUp() public {
        registry = new ProductRegistry();
        registry.addManufacturer(manufacturer, _id("MFG001"), "Acme");
        registry.addManufacturer(otherManufacturer, _id("MFG002"), "Other Co");
    }

    function testOwnerIsDeployer() public view {
        assertEq(registry.owner(), address(this));
    }

    function testStrangerCannotAddManufacturer() public {
        vm.prank(stranger);
        vm.expectRevert(abi.encodeWithSignature("Error(string)", "Caller is not owner"));
        registry.addManufacturer(makeAddr("new"), _id("MFG003"), "New Co");
    }

    function testManufacturerCannotAddManufacturer() public {
        vm.prank(manufacturer);
        vm.expectRevert(abi.encodeWithSignature("Error(string)", "Caller is not owner"));
        registry.addManufacturer(makeAddr("new"), _id("MFG003"), "New Co");
    }

    function testOwnerCanAddAndRemoveManufacturer() public {
        address wallet = makeAddr("third");
        registry.addManufacturer(wallet, _id("MFG003"), "Third");
        assertTrue(registry.isManufacturer(wallet));

        registry.removeManufacturer(wallet);
        assertFalse(registry.isManufacturer(wallet));

        vm.prank(wallet);
        vm.expectRevert(abi.encodeWithSignature("Error(string)", "Caller is not an authorized manufacturer"));
        registry.registerProduct(_id("P-AFTER-REVOKE"), bytes32(uint256(1)));
    }

    function testCannotAddActiveManufacturerTwice() public {
        vm.expectRevert(abi.encodeWithSignature("Error(string)", "Already an active manufacturer"));
        registry.addManufacturer(manufacturer, _id("MFG001"), "Acme");
    }

    function testStrangerCannotRegister() public {
        vm.prank(stranger);
        vm.expectRevert(abi.encodeWithSignature("Error(string)", "Caller is not an authorized manufacturer"));
        registry.registerProduct(_id("P10001"), keccak256("hash"));
    }

    function testManufacturerCanRegisterAndDuplicateReverts() public {
        bytes32 id = _id("P10001");
        bytes32 productHash = registry.hashProduct("P10001", "SN001928", "ABC-X1", "B2026-09");

        vm.prank(manufacturer);
        registry.registerProduct(id, productHash);

        (bytes32 stored, address who, uint256 registeredAt, bool active) = registry.getProduct(id);
        assertEq(stored, productHash);
        assertEq(who, manufacturer);
        assertGt(registeredAt, 0);
        assertTrue(active);

        vm.prank(manufacturer);
        vm.expectRevert(abi.encodeWithSignature("Error(string)", "Product already registered"));
        registry.registerProduct(id, productHash);
    }

    function testOtherManufacturerCannotDeactivate() public {
        bytes32 id = _id("P10002");
        vm.prank(manufacturer);
        registry.registerProduct(id, bytes32(uint256(2)));

        vm.prank(otherManufacturer);
        vm.expectRevert(abi.encodeWithSignature("Error(string)", "Not authorized"));
        registry.deactivateProduct(id);
    }

    function testRegisteringManufacturerCanDeactivate() public {
        bytes32 id = _id("P10003");
        bytes32 productHash = keccak256("recall-me");
        vm.prank(manufacturer);
        registry.registerProduct(id, productHash);

        vm.prank(manufacturer);
        registry.deactivateProduct(id);

        (bool isAuthentic,, uint256 registeredAt, bool active) = registry.verifyProduct(id, productHash);
        assertFalse(isAuthentic);
        assertGt(registeredAt, 0);
        assertFalse(active);

        vm.prank(manufacturer);
        vm.expectRevert(abi.encodeWithSignature("Error(string)", "Already deactivated"));
        registry.deactivateProduct(id);
    }

    function testOwnerCanDeactivate() public {
        bytes32 id = _id("P10004");
        vm.prank(manufacturer);
        registry.registerProduct(id, bytes32(uint256(4)));

        registry.deactivateProduct(id);
        (,,, bool active) = registry.getProduct(id);
        assertFalse(active);
    }

    function testVerifyMatchingRecord() public {
        bytes32 id = _id("P10005");
        bytes32 productHash = registry.hashProduct("P10005", "SN", "M", "B");
        vm.prank(manufacturer);
        registry.registerProduct(id, productHash);

        (bool isAuthentic, address who, uint256 registeredAt, bool active) =
            registry.verifyProduct(id, productHash);
        assertTrue(isAuthentic);
        assertEq(who, manufacturer);
        assertGt(registeredAt, 0);
        assertTrue(active);
    }

    function testVerifyRejectsDifferentHash() public {
        bytes32 id = _id("P10006");
        vm.prank(manufacturer);
        registry.registerProduct(id, registry.hashProduct("P10006", "SN", "M", "B"));

        (bool isAuthentic,,,) = registry.verifyProduct(id, registry.hashProduct("P10006", "OTHER", "M", "B"));
        assertFalse(isAuthentic);
    }

    function testVerifyUnknownProduct() public view {
        (bool isAuthentic, address who, uint256 registeredAt, bool active) =
            registry.verifyProduct(_id("MISSING"), bytes32(uint256(9)));
        assertFalse(isAuthentic);
        assertEq(who, address(0));
        assertEq(registeredAt, 0);
        assertFalse(active);
    }

    function testHashProductUsesAbiEncode() public view {
        bytes32 encoded = registry.hashProduct("ab", "c", "m", "b");
        assertEq(encoded, keccak256(abi.encode("ab", "c", "m", "b")));
        assertTrue(encoded != registry.hashProduct("a", "bc", "m", "b"));

        // encodePacked drops the length prefix, so these two tuples collide.
        assertEq(
            keccak256(abi.encodePacked("ab", "c", "m", "b")),
            keccak256(abi.encodePacked("a", "bc", "m", "b"))
        );
    }

    /// Right-pad a short UTF-8 id into bytes32, matching services/common/crypto/hashing.py.
    function _id(string memory value) internal pure returns (bytes32 result) {
        bytes memory raw = bytes(value);
        require(raw.length <= 32, "id too long");
        for (uint256 i = 0; i < raw.length; i++) {
            result |= bytes32(raw[i]) >> (i * 8);
        }
    }
}
