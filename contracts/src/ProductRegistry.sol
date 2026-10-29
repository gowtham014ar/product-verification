// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title ProductRegistry
 * @notice On-chain registry for product authenticity verification.
 *         Stores only hashes — full product data lives in PostgreSQL.
 */
contract ProductRegistry {

    // ─── Structs ─────────────────────────────────────────────────────────────

    struct Manufacturer {
        bytes32 id;       // unique manufacturer ID (e.g. keccak256("MFG001"))
        string  name;     // human-readable name   (e.g. "ABC Electronics")
        address wallet;   // registered wallet address
        uint256 addedAt;  // block.timestamp when added
        bool    active;   // false = revoked
    }

    struct Product {
        // keccak256(abi.encode(productId, serialNumber, model, batch))
        // A match proves those strings were registered. It does not prove a
        // physical label is unique: a copied label presents the same strings.
        bytes32 productHash;
        address manufacturer;  // wallet that registered this product
        uint256 registeredAt;  // block.timestamp of registration
        bool    active;        // false = deactivated / recalled
    }

    // ─── State ────────────────────────────────────────────────────────────────

    address public owner;

    mapping(address => Manufacturer) public manufacturerInfo; // O(1) lookup
    address[] private manufacturerAddresses;                  // for enumeration

    mapping(bytes32 => Product) public products;

    // ─── Events ───────────────────────────────────────────────────────────────

    event ProductRegistered  (bytes32 indexed productId, address indexed manufacturer, uint256 timestamp);
    event ProductDeactivated (bytes32 indexed productId, address indexed by,           uint256 timestamp);
    event ManufacturerAdded  (address indexed wallet, bytes32 id, string name);
    event ManufacturerRemoved(address indexed wallet);

    // ─── Modifiers ────────────────────────────────────────────────────────────

    modifier onlyOwner() {
        require(msg.sender == owner, "Caller is not owner");
        _;
    }

    modifier onlyManufacturer() {
        require(manufacturerInfo[msg.sender].active, "Caller is not an authorized manufacturer");
        _;
    }

    // ─── Constructor ──────────────────────────────────────────────────────────

    constructor() {
        owner = msg.sender;
    }

    // ─── Admin ────────────────────────────────────────────────────────────────

    /**
     * @notice Grant manufacturer role with a unique ID and name.
     * @param _  Manufacturer's wallet address
     * @param _id      Unique manufacturer ID as bytes32 (e.g. keccak256("MFG001"))
     * @param _name    Human-readable company name
     */
    function addManufacturer(address _wallet, bytes32 _id, string calldata _name) external onlyOwner {
        require(_wallet != address(0),            "Invalid wallet address");
        require(!manufacturerInfo[_wallet].active, "Already an active manufacturer");
        require(bytes(_name).length > 0,           "Name is required");

        // Push to list only on first-ever registration of this wallet
        if (manufacturerInfo[_wallet].addedAt == 0) {
            manufacturerAddresses.push(_wallet);
        }

        manufacturerInfo[_wallet] = Manufacturer({
            id:      _id,
            name:    _name,
            wallet:  _wallet,
            addedAt: block.timestamp,
            active:  true
        });

        emit ManufacturerAdded(_wallet, _id, _name);
    }

    /**
     * @notice Revoke manufacturer role (soft delete — history is preserved).
     * @param _wallet Manufacturer's wallet address to deactivate
     */
    function removeManufacturer(address _wallet) external onlyOwner {
        require(manufacturerInfo[_wallet].active, "Not an active manufacturer");
        manufacturerInfo[_wallet].active = false;
        emit ManufacturerRemoved(_wallet);
    }

    // ─── Core Functions ───────────────────────────────────────────────────────

    /**
     * @notice Canonical fingerprint. abi.encode keeps a length prefix on each
     *         string, so shifting bytes across field boundaries changes the hash.
     *         ("ab","c",...) and ("a","bc",...) do not collide.
     */
    function hashProduct(
        string calldata productId,
        string calldata serialNumber,
        string calldata model,
        string calldata batch
    ) external pure returns (bytes32) {
        return keccak256(abi.encode(productId, serialNumber, model, batch));
    }

    /**
     * @notice Register a new product on-chain.
     * @param productId   bytes32 representation of the product's unique ID
     * @param productHash keccak256(abi.encode(productId, serial, model, batch))
     */
    function registerProduct(bytes32 productId, bytes32 productHash) external onlyManufacturer {
        require(products[productId].registeredAt == 0, "Product already registered");

        products[productId] = Product({
            productHash:  productHash,
            manufacturer: msg.sender,
            registeredAt: block.timestamp,
            active:       true
        });

        emit ProductRegistered(productId, msg.sender, block.timestamp);
    }

    /**
     * @notice Verify whether a product is authentic.
     * @param productId   The product's unique ID (bytes32)
     * @param productHash keccak256 hash recomputed by the application
     * @return isAuthentic  true only when this id is registered, active, and the hash matches.
     *         That means the submitted strings match a record. It does not
     *         prove the physical item is the only one carrying those strings.
     * @return manufacturer wallet that registered the product
     * @return registeredAt UNIX timestamp of registration
     * @return active       current active status
     */
    function verifyProduct(bytes32 productId, bytes32 productHash)
        external
        view
        returns (
            bool    isAuthentic,
            address manufacturer,
            uint256 registeredAt,
            bool    active
        )
    {
        Product memory p = products[productId];

        isAuthentic  = (p.registeredAt != 0 && p.active && p.productHash == productHash);
        manufacturer = p.manufacturer;
        registeredAt = p.registeredAt;
        active       = p.active;
    }

    /**
     * @notice Deactivate a product (recall / counterfeit flag).
     *         Only the registering manufacturer or owner can deactivate.
     * @param productId bytes32 product ID to deactivate
     */
    function deactivateProduct(bytes32 productId) external {
        Product storage p = products[productId];
        require(p.registeredAt != 0,                                 "Product not registered");
        require(p.manufacturer == msg.sender || msg.sender == owner, "Not authorized");
        require(p.active,                                            "Already deactivated");

        p.active = false;
        emit ProductDeactivated(productId, msg.sender, block.timestamp);
    }

    // ─── View ─────────────────────────────────────────────────────────────────

    /**
     * @notice Returns all currently active manufacturers.
     *         Iterates the address list and filters by active = true.
     */
    function getAllManufacturers() external view returns (Manufacturer[] memory) {
        // First pass: count active
        uint256 count = 0;
        for (uint256 i = 0; i < manufacturerAddresses.length; i++) {
            if (manufacturerInfo[manufacturerAddresses[i]].active) count++;
        }

        // Second pass: populate result array
        Manufacturer[] memory result = new Manufacturer[](count);
        uint256 idx = 0;
        for (uint256 i = 0; i < manufacturerAddresses.length; i++) {
            address addr = manufacturerAddresses[i];
            if (manufacturerInfo[addr].active) {
                result[idx] = manufacturerInfo[addr];
                idx++;
            }
        }
        return result;
    }

    /// @notice Get details for a specific manufacturer by wallet address
    function getManufacturer(address _wallet) external view returns (Manufacturer memory) {
        return manufacturerInfo[_wallet];
    }

    /// @notice Fetch all stored fields for a product (raw read, no hash check)
    function getProduct(bytes32 productId)
        external
        view
        returns (
            bytes32 productHash,
            address manufacturer,
            uint256 registeredAt,
            bool    active
        )
    {
        Product memory p = products[productId];
        return (p.productHash, p.manufacturer, p.registeredAt, p.active);
    }

    /// @notice Check if an address is an active authorized manufacturer
    function isManufacturer(address _addr) external view returns (bool) {
        return manufacturerInfo[_addr].active;
    }

    /// @notice Total count of ever-registered manufacturers (including removed)
    function manufacturerCount() external view returns (uint256) {
        return manufacturerAddresses.length;
    }
}
