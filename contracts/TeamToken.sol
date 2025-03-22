// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title TeamToken
 * @dev ERC20 token representing a team in a betting event
 * Only the owner (Momentum Markets contract) can mint tokens
 * Tokens can be frozen after first transfer to prevent further transfers
 */
contract TeamToken is ERC20, Ownable {
    string public teamName;
    
    // Mapping to track frozen addresses
    mapping(address => bool) public frozenAddresses;
    
    // Event emitted when an address is frozen
    event AddressFrozen(address indexed account);
    
    constructor(
        string memory _name,
        string memory _symbol
    ) ERC20(_name, _symbol) Ownable(msg.sender) {
        
        // Mint 1 billion tokens (using 18 decimals)
        uint256 totalSupply = 1_000_000_000 * 10**18;
        
        // Mint half of the supply to the contract creator
        _mint(msg.sender, totalSupply);
    }
    
    /**
     * @dev Mint new tokens to an address
     * @param _to Address to mint tokens to
     * @param _amount Amount of tokens to mint
     */
    function mint(address _to, uint256 _amount) external onlyOwner {
        _mint(_to, _amount);
    }
    
    /**
     * @dev Bulk mint tokens to multiple addresses
     * @param _recipients Array of recipient addresses
     * @param _amounts Array of token amounts to mint
     */
    function bulkMint(address[] calldata _recipients, uint256[] calldata _amounts) external onlyOwner {
        require(_recipients.length == _amounts.length, "Arrays must have same length");
        
        for (uint256 i = 0; i < _recipients.length; i++) {
            _mint(_recipients[i], _amounts[i]);
        }
    }
    
    /**
     * @dev Freeze tokens at a specific address, preventing further transfers
     * @param _account Address to freeze tokens for
     */
    function freezeAddress(address _account) external onlyOwner {
        require(!frozenAddresses[_account], "Address already frozen");
        frozenAddresses[_account] = true;
        emit AddressFrozen(_account);
    }
    
    /**
     * @dev Override the ERC20 transfer function to enforce freezing
     */
    function transfer(address to, uint256 amount) public override returns (bool) {
        require(!frozenAddresses[_msgSender()], "Token transfers from this address are frozen");
        
        // If this is the first transfer to this address, freeze it after transfer
        bool shouldFreeze = !frozenAddresses[to] && to != address(0) && balanceOf(to) == 0;
        
        bool success = super.transfer(to, amount);
        
        if (success && shouldFreeze) {
            frozenAddresses[to] = true;
            emit AddressFrozen(to);
        }
        
        return success;
    }
    
    /**
     * @dev Override the ERC20 transferFrom function to enforce freezing
     */
    function transferFrom(address from, address to, uint256 amount) public override returns (bool) {
        require(!frozenAddresses[from], "Token transfers from this address are frozen");
        
        // If this is the first transfer to this address, freeze it after transfer
        bool shouldFreeze = !frozenAddresses[to] && to != address(0) && balanceOf(to) == 0;
        
        bool success = super.transferFrom(from, to, amount);
        
        if (success && shouldFreeze) {
            frozenAddresses[to] = true;
            emit AddressFrozen(to);
        }
        
        return success;
    }
    
    /**
     * @dev Override the ERC20 approve function to prevent approvals from frozen addresses
     */
    function approve(address spender, uint256 amount) public override returns (bool) {
        require(!frozenAddresses[_msgSender()], "Token approvals from this address are frozen");
        return super.approve(spender, amount);
    }

} 