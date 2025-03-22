// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title MomentumMarkets
 * @dev A decentralized prediction platform for sports betting on the Base network
 */
contract MomentumMarkets is Ownable(msg.sender) {
    // The ERC20 token that this contract will hold
    IERC20 public issuingToken;
    
    // Event data structure
    struct Event {
        uint256 id;
        string name;
        bool isActive;
        bool isResolved;
        uint256 totalBetAmount;
        uint256 winningTeamId;
    }
    
    // Bet data structure
    struct Bet {
        uint256 amount;
        bool claimed;
    }
    
    // Mapping from event ID to event details
    mapping(uint256 => Event) public events;
    
    // Mapping from event ID to mapping of user address to bet
    mapping(uint256 => mapping(address => Bet)) public userBets;
    
    // Mapping of user address to their rewards for each event
    mapping(uint256 => mapping(address => uint256)) public userRewards;
    
    // Funds for tax collection (5% of bets)
    uint256 public taxFund;
    
    // Fund that holds the total bet amounts (95% of bets)
    uint256 public betFund;
    
    // Tax rate in basis points (5% = 500 basis points)
    uint256 public constant TAX_RATE = 500;
    
    // Denominator for basis points calculations (100% = 10000)
    uint256 public constant BASIS_POINTS_DENOMINATOR = 10000;
    
    // Pause state to control betting functionality
    bool public paused = false;
    
    // Event emitted when rewards are claimed
    event RewardsClaimed(address indexed user, uint256 eventId, uint256 amount);
    
    // Event emitted when rewards are set
    event RewardsSet(address indexed user, uint256 eventId, uint256 amount);
    
    // Event emitted when a bet is placed
    event BetPlaced(address indexed user, uint256 eventId, uint256 teamId, uint256 amount, uint256 taxAmount, uint256 netBetAmount);
    
    // Event emitted when a new event is created
    event EventCreated(uint256 indexed eventId, string name);
    
    // Event emitted when an event is resolved
    event EventResolved(uint256 indexed eventId, uint256 winningTeamId);
    
    // Events emitted when the contract is paused or unpaused
    event Paused(address account);
    event Unpaused(address account);
    
    /**
     * @dev Modifier to make a function callable only when the contract is not paused
     */
    modifier whenNotPaused() {
        require(!paused, "Contract is paused");
        _;
    }
    
    /**
     * @dev Modifier to make a function callable only when the contract is paused
     */
    modifier whenPaused() {
        require(paused, "Contract is not paused");
        _;
    }
    
    /**
     * @dev Constructor sets the rewards token
     * @param _issuingToken Address of the ERC20 token used for rewards and betting
     */
    constructor(address _issuingToken) {
        issuingToken = IERC20(_issuingToken);
        taxFund = 0;
        betFund = 0;
    }
    
    /**
     * @dev Pauses the betting functionality
     */
    function pause() external onlyOwner whenNotPaused {
        paused = true;
        emit Paused(msg.sender);
    }
    
    /**
     * @dev Unpauses the betting functionality
     */
    function unpause() external onlyOwner whenPaused {
        paused = false;
        emit Unpaused(msg.sender);
    }
    
    /**
     * @dev Creates a new betting event
     * @param name The name of the event
     * @param eventId The ID of the event to create
     * @return eventId The ID of the newly created event
     */
    function createEvent(string calldata name, uint256 eventId) external onlyOwner returns (uint256) {
        require(events[eventId].id == 0, "Event ID already exists");
        
        Event memory eventData = Event({
            id: eventId,
            name: name,
            isActive: true,
            isResolved: false,
            totalBetAmount: 0,
            winningTeamId: 0
        });

        events[eventId] = eventData;
        
        emit EventCreated(eventId, name);
        return eventId;
    }

    function getUserTokenBalance(address user) public view returns (uint256) {
        return issuingToken.balanceOf(user);
    }
    
    /**
     * @dev Set rewards for multiple users for a specific event
     * @param eventId The ID of the event
     * @param users Array of user addresses
     * @param amounts Array of token amounts
     */
    function setRewards(uint256 eventId, address[] calldata users, uint256[] calldata amounts) external onlyOwner {
        require(events[eventId].id != 0, "Event does not exist");
        require(events[eventId].isResolved, "Event must be resolved first");
        require(users.length == amounts.length, "Arrays must be the same length");
        
        for (uint i = 0; i < users.length; i++) {
            userRewards[eventId][users[i]] = amounts[i];
            emit RewardsSet(users[i], eventId, amounts[i]);
        }
    }
    
    /**
     * @dev Resolves an event, marking it as no longer active
     * @param eventId The ID of the event to resolve
     * @param winningTeamId The ID of the winning team
     */
    function resolveEvent(uint256 eventId, uint256 winningTeamId) external onlyOwner {
        require(events[eventId].id != 0, "Event does not exist");
        require(events[eventId].isActive, "Event is not active");
        require(!events[eventId].isResolved, "Event already resolved");
        
        events[eventId].isActive = false;
        events[eventId].isResolved = true;
        events[eventId].winningTeamId = winningTeamId;
        
        emit EventResolved(eventId, winningTeamId);
    }
    
    /**
     * @dev Allows users to claim their rewards for a specific event
     * @param eventId The ID of the event
     */
    function claimRewards(uint256 eventId) external {
        require(events[eventId].id != 0, "Event does not exist");
        require(events[eventId].isResolved, "Event must be resolved first");
        
        uint256 amount = userRewards[eventId][msg.sender];
        require(amount > 0, "No rewards available");
        require(amount <= betFund, "Insufficient funds in bet fund");
        
        // Update state before transfer to prevent reentrancy
        userRewards[eventId][msg.sender] = 0;
        betFund -= amount;
        
        // Transfer the tokens to the user
        bool success = issuingToken.transfer(msg.sender, amount);
        require(success, "Token transfer failed");
        
        emit RewardsClaimed(msg.sender, eventId, amount);
    }
    
    /**
     * @dev Allows users to place a bet with tokens on a specific event
     * @param eventId The ID of the event to bet on
     * @param teamId The ID of the team to bet on
     * @param amount The amount of tokens to bet
     */
    function bet(uint256 eventId, uint256 teamId, uint256 amount) external whenNotPaused {
        require(events[eventId].id != 0, "Event does not exist");
        require(events[eventId].isActive, "Event is not active");
        require(!events[eventId].isResolved, "Event already resolved");
        require(amount > 0, "Bet amount must be greater than 0");
        require(issuingToken.allowance(msg.sender, address(this)) >= amount, "Insufficient allowance");
        require(userBets[eventId][msg.sender].amount == 0, "User has already placed a bet on this event");
        
        // Calculate the tax amount (5% of bet)
        uint256 taxAmount = (amount * TAX_RATE) / BASIS_POINTS_DENOMINATOR;
        
        // Calculate the net bet amount (95% of bet)
        uint256 netBetAmount = amount - taxAmount;
        
        // Transfer tokens from user to contract
        bool success = issuingToken.transferFrom(msg.sender, address(this), amount);
        require(success, "Token transfer failed");

        userBets[eventId][msg.sender] = Bet({
            amount: amount,
            claimed: false
        });

        // Update event total bet amount
        events[eventId].totalBetAmount += amount;
        
        betFund += netBetAmount;
        taxFund += taxAmount;
        
        emit BetPlaced(msg.sender, eventId, teamId, amount, taxAmount, netBetAmount);
    }
    
    /**
     * @dev Allows the owner to withdraw from the tax fund
     * @param amount The amount to withdraw
     */
    function withdrawTaxFund(uint256 amount) external onlyOwner {
        require(amount <= taxFund, "Insufficient tax fund balance");

        taxFund -= amount;

        bool success = issuingToken.transfer(owner(), amount);
        require(success, "Token transfer failed");
    }
    
    /**
     * @dev Retrieves the winning team ID for a specified event
     * @param eventId The ID of the event
     * @return winningTeamId The ID of the winning team
     */
    function getWinningTeamId(uint256 eventId) external view returns (uint256) {
        require(events[eventId].id != 0, "Event does not exist");
        require(events[eventId].isResolved, "Event not yet resolved");
        
        return events[eventId].winningTeamId;
    }
} 