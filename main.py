from fastapi import FastAPI, HTTPException
from web3 import Web3
import os
from dotenv import load_dotenv
from models import Event, FinalizeEvent
from constants import EVENTS


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


events = EVENTS

# Root endpoint
@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {"message": "ERC20 Token and Momentum Markets API on Base Testnet"}

@app.get("/api/events")
async def get_events():
    logger.info("Getting all events")
    return {"events": EVENTS}

@app.post("/api/finalize-event/{event_id}")
async def finalize_event(event_id: int, finalizeEvent: FinalizeEvent):
    logger.info(f"Finalizing event with ID: {event_id}")
    
    event = next((e for e in events if e.id == event_id), None)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    winner_index = finalizeEvent.winner_index
    if winner_index not in range(len(event.teams)):
        raise HTTPException(status_code=400, detail="Invalid winner index")

    event.status = "finalized"
    event.winner_index = winner_index
    # Find the index of the event in the events list
    event_index = next((i for i, e in enumerate(events) if e.id == event_id), None)
    if event_index is not None:
        # Update the event in the events list
        events[event_index] = event
        logger.info(f"Event with ID {event_id} updated in events list")
    else:
        logger.warning(f"Could not find event with ID {event_id} in events list for updating")

    return {"message": f"Event with ID {event_id} finalized"}
