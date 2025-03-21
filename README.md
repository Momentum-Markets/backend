# Momentum Markets Platform

A cutting-edge decentralized prediction platform on the Base network, reimagining how users engage with high-stakes outcomes.

## Overview

Momentum Markets allows participants to lock in ETH or ERC20 tokens on Base Sepolia, directing 95% of each contribution to a shared Momentum Pool that grows with community input. The remaining 5% supports the ecosystem:
- 3% for liquidity
- 1% for development
- 1% for community incentives

This ensures sustainability without mid-event exits.

## Key Features

- **Dynamic Market Cap Scaling**: The market cap scales with participation (e.g., $700K on Team 1 reaches 7x), boosting individual stakes.
- **Reward Distribution**: At the event's close, successful predictors earn $BMM tokens based on their contribution's share of the winning pool.
- **Multi-Token Support**: Bet with ETH or any ERC20 token.
- **Oracle Integration**: Uses Chainlink price feeds to get accurate USD values for tokens.

## Project Structure

```
momentum-markets/
├── contracts/
│   ├── MomentumMarkets.sol
│   └── TeamToken.sol
├── logs/
├── erc20_deployer.py
├── momentum_markets_deployer.py
├── logger.py
├── main.py
├── requirements.txt
└── README.md
```

## Smart Contracts

### MomentumMarkets.sol

The main contract that handles:
- Event creation and management
- Betting with ETH or ERC20 tokens
- Fee distribution
- Event settlement
- Reward calculations and distribution

### TeamToken.sol

ERC20 token representing a team in a betting event:
- Minted to winners after event settlement
- Owned by the MomentumMarkets contract
- Represents a user's stake in the Momentum Pool

## API Endpoints

### ERC20 Token Management

- `GET /` - Root endpoint
- `POST /deploy-token` - Deploy a new ERC20 token
- `GET /token/{contract_address}` - Get token details
- `POST /mint-tokens` - Mint more tokens
- `GET /balance/{contract_address}/{address}` - Check token balance

### Momentum Markets Platform

- `POST /deploy-momentum-markets` - Deploy the Momentum Markets platform
- `POST /deploy-team-tokens` - Deploy team tokens for an event
- `POST /create-event` - Create a new betting event
- `POST /settle-event` - Settle an event by determining the winner
- `GET /event/{event_id}` - Get event details

## Setup and Installation

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Configure environment variables in a `.env` file:
   ```
   BASE_TESTNET_RPC_URL=https://sepolia.base.org
   PRIVATE_KEY=your_private_key
   ACCOUNT_ADDRESS=your_account_address
   ETH_USD_PRICE_FEED=chainlink_eth_usd_price_feed_address
   ```
4. Run the API server:
   ```
   uvicorn main:app --reload
   ```

## Usage Example

1. Deploy the Momentum Markets platform
2. Create an event and deploy team tokens
3. Place bets on a team using ETH or ERC20 tokens
4. After the event concludes, settle the event
5. Winners can claim their rewards

## License

MIT

## Contact

For inquiries, please contact the Momentum Markets team. 