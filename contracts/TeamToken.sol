// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title TeamToken
 * @dev ERC20 token representing a team in a betting event
 * Only the owner (Momentum Markets contract) can mint tokens
 */
contract TeamToken is ERC20, Ownable {
    string public teamName;
    string public eventName;
    uint256 public eventId;
    
    /**
     * @dev Constructor initializes the token
     * @param _name Token name (typically "BMM: Team Name")
     * @param _symbol Token symbol (typically "BMM-TEAM")
     * @param _teamName Name of the team
     * @param _eventName Name of the event
     * @param _eventId ID of the event in Momentum Markets
     * @param _owner Address of the Momentum Markets contract that will own this token
     */
    constructor(
        string memory _name,
        string memory _symbol,
        string memory _teamName,
        string memory _eventName,
        uint256 _eventId,
        address _owner
    ) ERC20(_name, _symbol) Ownable(_owner) {
        teamName = _teamName;
        eventName = _eventName;
        eventId = _eventId;
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
} 