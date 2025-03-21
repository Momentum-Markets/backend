from fastapi import FastAPI, HTTPException
from web3 import Web3
import os
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import Optional, List
import time

# Import our modules
from erc20_deployer import deploy_erc20_token, get_token_details, mint_tokens, ERC20_FULL_ABI
from momentum_markets_deployer import (
    deploy_momentum_markets, 
    deploy_team_tokens, 
    create_event, 
    settle_event, 
    get_event_details
)
from logger import setup_logger

# Initialize logger
logger = setup_logger('erc20_api')

# Load environment variables from .env file
load_dotenv()
logger.info("Environment variables loaded")

# Initialize FastAPI app
app = FastAPI()
logger.info("FastAPI application initialized")

# Configuration
RPC_URL = os.getenv("BASE_TESTNET_RPC_URL", "https://sepolia.base.org")  # Replace with actual URL
PRIVATE_KEY = os.getenv("PRIVATE_KEY")  # Your private key
ACCOUNT_ADDRESS = os.getenv("ACCOUNT_ADDRESS")  # Your wallet address
ETH_USD_PRICE_FEED = os.getenv("ETH_USD_PRICE_FEED")  # Chainlink ETH/USD price feed address

# Log configuration (without exposing private key)
if PRIVATE_KEY and ACCOUNT_ADDRESS:
    logger.info(f"Configuration loaded: RPC_URL={RPC_URL}, ACCOUNT_ADDRESS={ACCOUNT_ADDRESS[:6]}...{ACCOUNT_ADDRESS[-4:] if len(ACCOUNT_ADDRESS) > 10 else ''}")
else:
    logger.warning("Missing configuration: PRIVATE_KEY or ACCOUNT_ADDRESS not set in environment variables")

# Set up Web3 connection
w3 = Web3(Web3.HTTPProvider(RPC_URL))
if w3.is_connected():
    logger.info(f"Connected to blockchain at {RPC_URL}")
else:
    logger.error(f"Failed to connect to Base Testnet at {RPC_URL}")
    raise Exception("Failed to connect to Base Testnet")

# Input models for our API endpoints
class TokenDeployRequest(BaseModel):
    name: str
    symbol: str
    initial_supply: int
    decimals: Optional[int] = 18

class TokenMintRequest(BaseModel):
    contract_address: str
    to_address: str
    amount: int
    decimals: Optional[int] = 18

class MomentumDeployRequest(BaseModel):
    eth_usd_price_feed: Optional[str] = ETH_USD_PRICE_FEED
    liquidity_fee_recipient: str
    development_fee_recipient: str
    community_fee_recipient: str

class TeamTokensDeployRequest(BaseModel):
    event_id: int
    event_name: str
    team1_name: str
    team2_name: str

class EventCreateRequest(BaseModel):
    name: str
    start_time: int
    end_time: int
    team1_token: str
    team2_token: str

class EventSettleRequest(BaseModel):
    event_id: int
    winning_team: str

class BetWithETHRequest(BaseModel):
    event_id: int
    team_token: str
    amount: float  # Amount in ETH

class BetWithERC20Request(BaseModel):
    event_id: int
    team_token: str
    payment_token: str
    amount: float

# Root endpoint
@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {"message": "ERC20 Token and Momentum Markets API on Base Testnet"}

# Deploy a new ERC20 token
@app.post("/deploy-token")
async def deploy_token(token_request: TokenDeployRequest):
    logger.info(f"Deploy token request received: name={token_request.name}, symbol={token_request.symbol}, supply={token_request.initial_supply}")
    try:
        result = deploy_erc20_token(
            name=token_request.name,
            symbol=token_request.symbol,
            initial_supply=token_request.initial_supply,
            decimals=token_request.decimals
        )
        logger.info(f"Token deployed successfully at {result['contract_address']}")
        return result
    except Exception as e:
        logger.error(f"Error deploying token: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Get token details
@app.get("/token/{contract_address}")
async def token_details(contract_address: str):
    logger.info(f"Token details request for contract: {contract_address}")
    try:
        details = get_token_details(contract_address)
        if "error" in details:
            logger.warning(f"Error retrieving token details: {details['error']}")
            raise HTTPException(status_code=404, detail=details["error"])
        logger.info(f"Token details retrieved successfully: {details['name']} ({details['symbol']})")
        return details
    except Exception as e:
        logger.error(f"Error getting token details: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Mint more tokens
@app.post("/mint-tokens")
async def create_tokens(mint_request: TokenMintRequest):
    logger.info(f"Mint request received: amount={mint_request.amount} to={mint_request.to_address}")
    try:
        tx_hash = mint_tokens(
            contract_address=mint_request.contract_address,
            to_address=mint_request.to_address,
            amount=mint_request.amount,
            decimals=mint_request.decimals
        )
        logger.info(f"Tokens minted successfully, tx_hash: {tx_hash}")
        return {"tx_hash": tx_hash}
    except Exception as e:
        logger.error(f"Error minting tokens: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Check balance
@app.get("/balance/{contract_address}/{address}")
async def get_balance(contract_address: str, address: str):
    logger.info(f"Balance check requested for address {address} on contract {contract_address}")
    try:
        token = w3.eth.contract(address=contract_address, abi=ERC20_FULL_ABI)
        balance_wei = token.functions.balanceOf(address).call()
        
        # Get token decimals for proper formatting
        decimals = token.functions.decimals().call()
        
        # Format the balance as a decimal
        balance = balance_wei / (10 ** decimals)
        token_symbol = token.functions.symbol().call()
        
        logger.info(f"Balance retrieved: {balance} {token_symbol}")
        logger.debug(f"Raw balance: {balance_wei}")
        
        return {
            "address": address,
            "contract_address": contract_address,
            "balance_raw": balance_wei,
            "balance": balance,
            "token_symbol": token_symbol
        }
    except Exception as e:
        logger.error(f"Error checking balance: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Deploy the Momentum Markets platform
@app.post("/deploy-momentum-markets")
async def deploy_markets(deploy_request: MomentumDeployRequest):
    logger.info("Deploy Momentum Markets request received")
    try:
        result = deploy_momentum_markets(
            eth_usd_price_feed=deploy_request.eth_usd_price_feed,
            liquidity_fee_recipient=deploy_request.liquidity_fee_recipient,
            development_fee_recipient=deploy_request.development_fee_recipient,
            community_fee_recipient=deploy_request.community_fee_recipient
        )
        logger.info(f"Momentum Markets deployed successfully at {result['contract_address']}")
        return result
    except Exception as e:
        logger.error(f"Error deploying Momentum Markets: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Deploy team tokens for an event
@app.post("/deploy-team-tokens")
async def deploy_teams(token_request: TeamTokensDeployRequest):
    logger.info(f"Deploy team tokens request received: event={token_request.event_name}, teams={token_request.team1_name} vs {token_request.team2_name}")
    try:
        result = deploy_team_tokens(
            event_id=token_request.event_id,
            event_name=token_request.event_name,
            team1_name=token_request.team1_name,
            team2_name=token_request.team2_name
        )
        logger.info(f"Team tokens deployed successfully: {result['team1_token_address']} and {result['team2_token_address']}")
        return result
    except Exception as e:
        logger.error(f"Error deploying team tokens: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Create a new betting event
@app.post("/create-event")
async def create_betting_event(event_request: EventCreateRequest):
    logger.info(f"Create event request received: name={event_request.name}")
    try:
        result = create_event(
            name=event_request.name,
            start_time=event_request.start_time,
            end_time=event_request.end_time,
            team1_token=event_request.team1_token,
            team2_token=event_request.team2_token
        )
        logger.info(f"Event created successfully with ID: {result['event_id']}")
        return result
    except Exception as e:
        logger.error(f"Error creating event: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Settle an event
@app.post("/settle-event")
async def settle_betting_event(settle_request: EventSettleRequest):
    logger.info(f"Settle event request received: event_id={settle_request.event_id}")
    try:
        result = settle_event(
            event_id=settle_request.event_id,
            winning_team=settle_request.winning_team
        )
        logger.info(f"Event {result['event_id']} settled successfully with winner: {result['winning_team']}")
        return result
    except Exception as e:
        logger.error(f"Error settling event: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Get event details
@app.get("/event/{event_id}")
async def get_event(event_id: int):
    logger.info(f"Event details request for event: {event_id}")
    try:
        details = get_event_details(event_id)
        logger.info(f"Event details retrieved successfully: {details['name']}")
        return details
    except Exception as e:
        logger.error(f"Error getting event details: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))