// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@chainlink/contracts/src/v0.8/interfaces/AggregatorV3Interface.sol";

/**
 * @title MomentumMarkets
 * @dev A decentralized prediction platform for sports betting on the Base network
 */
contract MomentumMarkets is Ownable {
    // Oracle interface for price feeds
    AggregatorV3Interface internal ethUsdPriceFeed;
    
    // Fee distribution
    uint256 public constant LIQUIDITY_FEE = 3; // 3%
    uint256 public constant DEVELOPMENT_FEE = 1; // 1%
    uint256 public constant COMMUNITY_FEE = 1; // 1%
    uint256 public constant TOTAL_FEE = 5; // 5%
    uint256 public constant MOMENTUM_POOL_PERCENTAGE = 95; // 95%
    
    // Fee recipient addresses
    address public liquidityFeeRecipient;
    address public developmentFeeRecipient;
    address public communityFeeRecipient;
    
    // Struct to represent a betting event
    struct BettingEvent {
        uint256 id;
        string name;
        uint256 startTime;
        uint256 endTime;
        bool isActive;
        bool isSettled;
        address team1Token;
        address team2Token;
        uint256 team1Pool; // Total USD value in team1
        uint256 team2Pool; // Total USD value in team2
        address winner; // Address of winning team token
    }
    
    // Struct to track individual bets
    struct Bet {
        address user;
        address teamToken;
        address paymentToken; // Address of the token used to bet (0x0 for ETH)
        uint256 amountPaid; // Amount of tokens or ETH paid
        uint256 usdValue; // USD value of the bet
    }
    
    // Events
    event EventCreated(uint256 indexed eventId, string name, address team1Token, address team2Token);
    event BetPlaced(uint256 indexed eventId, address indexed user, address teamToken, uint256 usdValue);
    event EventSettled(uint256 indexed eventId, address winningTeam);
    event RewardsClaimed(uint256 indexed eventId, address indexed user, uint256 rewardAmount);
    
    // Mappings
    mapping(uint256 => BettingEvent) public events;
    mapping(uint256 => mapping(address => Bet[])) public eventBets; // eventId => user => bets
    mapping(address => mapping(address => uint256)) public tokenPriceFeeds; // token => price feed address
    
    uint256 public nextEventId = 1;
    
    /**
     * @dev Constructor sets up the Momentum Markets platform
     * @param _ethUsdPriceFeed Chainlink price feed for ETH/USD
     * @param _liquidityFeeRecipient Address to receive liquidity fees
     * @param _developmentFeeRecipient Address to receive development fees
     * @param _communityFeeRecipient Address to receive community fees
     */
    constructor(
        address _ethUsdPriceFeed,
        address _liquidityFeeRecipient,
        address _developmentFeeRecipient,
        address _communityFeeRecipient
    ) Ownable(msg.sender) {
        ethUsdPriceFeed = AggregatorV3Interface(_ethUsdPriceFeed);
        liquidityFeeRecipient = _liquidityFeeRecipient;
        developmentFeeRecipient = _developmentFeeRecipient;
        communityFeeRecipient = _communityFeeRecipient;
    }
    
    /**
     * @dev Create a new betting event
     * @param _name Name of the event
     * @param _startTime Start time of the event
     * @param _endTime End time of the event
     * @param _team1Token ERC20 token representing team 1
     * @param _team2Token ERC20 token representing team 2
     */
    function createEvent(
        string memory _name,
        uint256 _startTime,
        uint256 _endTime,
        address _team1Token,
        address _team2Token
    ) external onlyOwner {
        require(_startTime > block.timestamp, "Start time must be in the future");
        require(_endTime > _startTime, "End time must be after start time");
        require(_team1Token != address(0) && _team2Token != address(0), "Invalid team token addresses");
        
        uint256 eventId = nextEventId++;
        
        events[eventId] = BettingEvent({
            id: eventId,
            name: _name,
            startTime: _startTime,
            endTime: _endTime,
            isActive: true,
            isSettled: false,
            team1Token: _team1Token,
            team2Token: _team2Token,
            team1Pool: 0,
            team2Pool: 0,
            winner: address(0)
        });
        
        emit EventCreated(eventId, _name, _team1Token, _team2Token);
    }
    
    /**
     * @dev Place a bet using ETH
     * @param _eventId ID of the event
     * @param _teamToken Address of the team token to bet on
     */
    function betWithETH(uint256 _eventId, address _teamToken) external payable {
        BettingEvent storage event_ = events[_eventId];
        require(event_.isActive, "Event is not active");
        require(block.timestamp >= event_.startTime && block.timestamp <= event_.endTime, "Event not in progress");
        require(_teamToken == event_.team1Token || _teamToken == event_.team2Token, "Invalid team token");
        require(msg.value > 0, "Bet amount must be greater than 0");
        
        // Get USD value of ETH
        uint256 usdValue = getEthUsdValue(msg.value);
        require(usdValue > 0, "USD value must be greater than 0");
        
        // Calculate fee amounts
        uint256 liquidityFeeAmount = (msg.value * LIQUIDITY_FEE) / 100;
        uint256 developmentFeeAmount = (msg.value * DEVELOPMENT_FEE) / 100;
        uint256 communityFeeAmount = (msg.value * COMMUNITY_FEE) / 100;
        uint256 momentumPoolAmount = msg.value - liquidityFeeAmount - developmentFeeAmount - communityFeeAmount;
        
        // Transfer fees
        (bool liquiditySent, ) = liquidityFeeRecipient.call{value: liquidityFeeAmount}("");
        require(liquiditySent, "Failed to send liquidity fee");
        
        (bool developmentSent, ) = developmentFeeRecipient.call{value: developmentFeeAmount}("");
        require(developmentSent, "Failed to send development fee");
        
        (bool communitySent, ) = communityFeeRecipient.call{value: communityFeeAmount}("");
        require(communitySent, "Failed to send community fee");
        
        // Store bet information
        Bet memory newBet = Bet({
            user: msg.sender,
            teamToken: _teamToken,
            paymentToken: address(0), // 0x0 represents ETH
            amountPaid: msg.value,
            usdValue: usdValue
        });
        
        eventBets[_eventId][msg.sender].push(newBet);
        
        // Update pools based on USD value
        if (_teamToken == event_.team1Token) {
            event_.team1Pool += usdValue;
        } else {
            event_.team2Pool += usdValue;
        }
        
        emit BetPlaced(_eventId, msg.sender, _teamToken, usdValue);
    }
    
    /**
     * @dev Place a bet using an ERC20 token
     * @param _eventId ID of the event
     * @param _teamToken Address of the team token to bet on
     * @param _paymentToken Address of the ERC20 token to pay with
     * @param _amount Amount of tokens to bet
     */
    function betWithERC20(uint256 _eventId, address _teamToken, address _paymentToken, uint256 _amount) external {
        BettingEvent storage event_ = events[_eventId];
        require(event_.isActive, "Event is not active");
        require(block.timestamp >= event_.startTime && block.timestamp <= event_.endTime, "Event not in progress");
        require(_teamToken == event_.team1Token || _teamToken == event_.team2Token, "Invalid team token");
        require(_amount > 0, "Bet amount must be greater than 0");
        require(_paymentToken != address(0), "Invalid payment token");
        
        // Get USD value of tokens
        uint256 usdValue = getTokenUsdValue(_paymentToken, _amount);
        require(usdValue > 0, "USD value must be greater than 0");
        
        // Calculate fee amounts (in tokens)
        uint256 liquidityFeeAmount = (_amount * LIQUIDITY_FEE) / 100;
        uint256 developmentFeeAmount = (_amount * DEVELOPMENT_FEE) / 100;
        uint256 communityFeeAmount = (_amount * COMMUNITY_FEE) / 100;
        uint256 momentumPoolAmount = _amount - liquidityFeeAmount - developmentFeeAmount - communityFeeAmount;
        
        // Transfer tokens from user
        IERC20 token = IERC20(_paymentToken);
        require(token.transferFrom(msg.sender, address(this), _amount), "Token transfer failed");
        
        // Transfer fees
        require(token.transfer(liquidityFeeRecipient, liquidityFeeAmount), "Failed to send liquidity fee");
        require(token.transfer(developmentFeeRecipient, developmentFeeAmount), "Failed to send development fee");
        require(token.transfer(communityFeeRecipient, communityFeeAmount), "Failed to send community fee");
        
        // Store bet information
        Bet memory newBet = Bet({
            user: msg.sender,
            teamToken: _teamToken,
            paymentToken: _paymentToken,
            amountPaid: _amount,
            usdValue: usdValue
        });
        
        eventBets[_eventId][msg.sender].push(newBet);
        
        // Update pools based on USD value
        if (_teamToken == event_.team1Token) {
            event_.team1Pool += usdValue;
        } else {
            event_.team2Pool += usdValue;
        }
        
        emit BetPlaced(_eventId, msg.sender, _teamToken, usdValue);
    }
    
    /**
     * @dev Settle an event by determining the winner
     * @param _eventId ID of the event
     * @param _winningTeam Address of the winning team token
     */
    function settleEvent(uint256 _eventId, address _winningTeam) external onlyOwner {
        BettingEvent storage event_ = events[_eventId];
        require(event_.isActive, "Event is not active");
        require(!event_.isSettled, "Event already settled");
        require(block.timestamp > event_.endTime, "Event not ended yet");
        require(_winningTeam == event_.team1Token || _winningTeam == event_.team2Token, "Invalid winning team");
        
        event_.isActive = false;
        event_.isSettled = true;
        event_.winner = _winningTeam;
        
        emit EventSettled(_eventId, _winningTeam);
    }
    
    /**
     * @dev Claim rewards for a settled event
     * @param _eventId ID of the event
     */
    function claimRewards(uint256 _eventId) external {
        BettingEvent storage event_ = events[_eventId];
        require(event_.isSettled, "Event not settled yet");
        require(event_.winner != address(0), "No winner determined");
        
        Bet[] storage userBets = eventBets[_eventId][msg.sender];
        require(userBets.length > 0, "No bets found for user");
        
        uint256 totalUserUsdValue = 0;
        bool hasWinningBet = false;
        
        // Calculate total USD value of user's bets on winning team
        for (uint256 i = 0; i < userBets.length; i++) {
            if (userBets[i].teamToken == event_.winner) {
                totalUserUsdValue += userBets[i].usdValue;
                hasWinningBet = true;
            }
        }
        
        require(hasWinningBet, "No winning bets found");
        
        // Calculate user's share of the winning pool
        uint256 winningPool = event_.winner == event_.team1Token ? event_.team1Pool : event_.team2Pool;
        uint256 totalPool = event_.team1Pool + event_.team2Pool;
        
        // User's percentage of the winning pool
        uint256 userPercentage = (totalUserUsdValue * 1e18) / winningPool;
        
        // Calculate BMM token reward
        uint256 userReward = (userPercentage * totalPool) / 1e18;
        
        // Mint BMM tokens to the user
        ERC20 bmmToken = ERC20(event_.winner);
        // This would need to be handled by a contract with minting capability
        // or by the contract owner through a separate endpoint
        
        emit RewardsClaimed(_eventId, msg.sender, userReward);
    }
    
    /**
     * @dev Set a price feed for a token
     * @param _token Address of the token
     * @param _priceFeed Address of the Chainlink price feed
     */
    function setTokenPriceFeed(address _token, address _priceFeed) external onlyOwner {
        require(_token != address(0), "Invalid token address");
        require(_priceFeed != address(0), "Invalid price feed address");
        tokenPriceFeeds[_token][_priceFeed] = 1;
    }
    
    /**
     * @dev Get ETH price in USD
     * @return price ETH price in USD (8 decimals)
     */
    function getEthUsdPrice() internal view returns (uint256) {
        (, int256 price, , , ) = ethUsdPriceFeed.latestRoundData();
        return uint256(price);
    }
    
    /**
     * @dev Get USD value of ETH amount
     * @param _ethAmount Amount of ETH in wei
     * @return usdValue USD value (scaled by 1e8)
     */
    function getEthUsdValue(uint256 _ethAmount) internal view returns (uint256) {
        uint256 ethPrice = getEthUsdPrice();
        return (_ethAmount * ethPrice) / 1e18;
    }
    
    /**
     * @dev Get USD value of token amount
     * @param _token Address of the token
     * @param _amount Amount of tokens
     * @return usdValue USD value (scaled by 1e8)
     */
    function getTokenUsdValue(address _token, uint256 _amount) internal view returns (uint256) {
        // For simplicity, we're just returning a placeholder
        // In a real implementation, this would use price feeds
        // or on-chain DEX prices to get accurate USD values
        
        // If token is ETH, use ETH/USD price feed
        if (_token == address(0)) {
            return getEthUsdValue(_amount);
        }
        
        // For other tokens, would need to implement token-specific logic
        // This is just a placeholder
        return _amount;
    }
    
    /**
     * @dev Update fee recipient addresses
     */
    function updateFeeRecipients(
        address _liquidityFeeRecipient,
        address _developmentFeeRecipient,
        address _communityFeeRecipient
    ) external onlyOwner {
        liquidityFeeRecipient = _liquidityFeeRecipient;
        developmentFeeRecipient = _developmentFeeRecipient;
        communityFeeRecipient = _communityFeeRecipient;
    }
    
    /**
     * @dev Receive function to accept ETH
     */
    receive() external payable {}
} 