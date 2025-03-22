from fastapi import FastAPI, HTTPException
from web3 import Web3
import os
from dotenv import load_dotenv
from models import Event, FinalizeEvent, Team, User, Bet
from constants import EVENTS, NZDD_CONTRACT_ADDRESS
from web3_provider import get_web3
import asyncio
import json
from bet_calculator import calculate_new_market_cap, calculate_rewards, calculate_buy_value_at_close
import helper
from fastapi.middleware.cors import CORSMiddleware

from logger import setup_logger

# Initialize logger
logger = setup_logger('erc20_api')

# Load environment variables from .env file
load_dotenv()
logger.info("Environment variables loaded")

# Initialize FastAPI app
app = FastAPI()
logger.info("FastAPI application initialized")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)
logger.info("CORS middleware configured to allow all origins")

# Configuration
PRIVATE_KEY = os.getenv("PRIVATE_KEY")  # Your private key
ACCOUNT_ADDRESS = os.getenv("ACCOUNT_ADDRESS")  # Your wallet address
MOMENTUM_MARKETS_ADDRESS = os.getenv("MOMENTUM_MARKETS_ADDRESS")  # MomentumMarkets contract address

# Log configuration (without exposing private key)
if PRIVATE_KEY and ACCOUNT_ADDRESS:
    logger.info(f"Configuration loaded: ACCOUNT_ADDRESS={ACCOUNT_ADDRESS[:6]}...{ACCOUNT_ADDRESS[-4:] if len(ACCOUNT_ADDRESS) > 10 else ''}")
else:
    logger.warning("Missing configuration: PRIVATE_KEY or ACCOUNT_ADDRESS not set in environment variables")

# Get Web3 connection from singleton provider
w3 = get_web3()
logger.info("Web3 connection initialized from provider")

# Load ABI for MomentumMarkets contract
contract_abi = helper.load_contract_abi('MomentumMarkets')

# Root endpoint
@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {"message": "ERC20 Token and Momentum Markets API on Base Testnet"}

@app.get("/api/events")
async def get_events():
    logger.info("Getting all events")
    return {"events": helper.get_all_events()}

@app.get("/api/events/{event_id}")
async def get_event(event_id: int):
    logger.info(f"Getting event with ID: {event_id}")
    event = helper.get_event(event_id)
    if event:
        return {"event": event}


@app.post("/api/finalize-event/{event_id}")
async def finalize_event(event_id: int, finalizeEvent: FinalizeEvent):
    logger.info(f"Finalizing event with ID: {event_id}")
    
    # Validate event ID
    events = helper.get_all_events()
    event = next((e for e in events if e.id == event_id), None)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    winner_index = finalizeEvent.winner_index
    if winner_index not in range(len(event.teams)):
        raise HTTPException(status_code=400, detail="Invalid winner index")
    
    # Call the helper function to resolve the event
    tx_hash, message = helper.resolve_event(
        MOMENTUM_MARKETS_ADDRESS, contract_abi, ACCOUNT_ADDRESS, event_id, winner_index
    )
    
    if not tx_hash:
        raise HTTPException(status_code=400, detail=message)
    
    return {"message": f"Event with ID {event_id} finalized", "tx_hash": tx_hash}

@app.post("/api/finalize-rewards/{event_id}")
async def collect_rewards(event_id: int):
    logger.info(f"Collecting rewards for event with ID: {event_id}")
    
    # Call the helper function to set rewards
    tx_hash, message = helper.set_rewards(
        MOMENTUM_MARKETS_ADDRESS, contract_abi, ACCOUNT_ADDRESS, event_id
    )
    
    if not tx_hash:
        raise HTTPException(status_code=400, detail=message)
    
    return {"message": f"Rewards collected for event with ID {event_id}", "tx_hash": tx_hash}

@app.get("/api/users")
async def get_users():
    logger.info("Getting all users")
    return {"users": helper.get_all_users()}

@app.get("/api/users/{address}")
async def get_user(address: str):
    logger.info(f"Getting user with address: {address}")
    user = helper.get_user(address)
    if user:
        return {"user": user}
    else:
        raise HTTPException(status_code=404, detail="User not found")

@app.on_event("startup")
async def startup_event():
    logger.info("Application starting up - initializing data from historical events")
    
    # First sync events from the contract
    await helper.sync_events_from_contract(MOMENTUM_MARKETS_ADDRESS, contract_abi)
    
    # Then aggregate historical events
    await helper.aggregate_historical_bet_events(MOMENTUM_MARKETS_ADDRESS, contract_abi)
    
    # Finally start listening for new events
    logger.info("Starting event listeners")
    asyncio.create_task(helper.listen_for_bet_events(MOMENTUM_MARKETS_ADDRESS, contract_abi))
    asyncio.create_task(helper.listen_for_event_resolved_events(MOMENTUM_MARKETS_ADDRESS, contract_abi))
