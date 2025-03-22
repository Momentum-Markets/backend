from fastapi import FastAPI, HTTPException
from web3 import Web3
import os
from dotenv import load_dotenv
from models import Event, FinalizeEvent, Team, User, Bet
from constants import EVENTS, NZDD_CONTRACT_ADDRESS
from web3_provider import get_web3
import asyncio
import json
from bet_calculator import calculate_new_market_cap, calculate_rewards


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

events = EVENTS

# Dictionary to store users by their address
users = {}

# Load ABI for MomentumMarkets contract
try:
    with open('abi/MomentumMarkets.json', 'r') as f:
        contract_abi = json.load(f)
        logger.info("Momentum Markets contract ABI loaded successfully")
except FileNotFoundError:
    logger.error("Could not find the contract ABI file. Make sure the contract is compiled.")
    contract_abi = []

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
    
    momentum_contract = w3.eth.contract(
        address=Web3.to_checksum_address(MOMENTUM_MARKETS_ADDRESS),
        abi=contract_abi
    )
    
    # check if event is resolved
    is_resolved = momentum_contract.functions.isResolved(event_id).call()
    if is_resolved:
        raise HTTPException(status_code=400, detail="Event is already resolved")

    

    # Update event status and reconcile with contract state
    event.status = "finalized"
    event.is_active = False
    event.is_resolved = True
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

@app.post("/api/finalize-rewards/{event_id}")
async def collect_rewards(event_id: int):
    logger.info(f"Collecting rewards for event with ID: {event_id}")
    
    # check with contract if event is resolved
    momentum_contract = w3.eth.contract(
        address=Web3.to_checksum_address(MOMENTUM_MARKETS_ADDRESS),
        abi=contract_abi
    )
    is_resolved = momentum_contract.functions.isResolved(event_id).call()
    if not is_resolved:
        raise HTTPException(status_code=400, detail="Event is not resolved")

    # get winning team id
    winning_team_id = momentum_contract.functions.getWinningTeamId(event_id).call()
    if not winning_team_id:
        raise HTTPException(status_code=400, detail="Winning team is not found")
    
    # get winning team name
    winning_team = next((t for t in events[event_id].teams if t.id == winning_team_id), None)
    if not winning_team:
        raise HTTPException(status_code=400, detail="Winning team is not found")
    
    # Get all users who bet on the winning team
    winning_users = []
    user_rewards = []
    # Filter users who bet on the winning team
    for user_address, user_data in users.items():
        # Check if user has bets for this event
        try:
            # Get user bet information from the contract
            is_user_winner = user_data.bets[0].team_id == winning_team_id and user_data.bets[0].amount > 0
            # Check if user bet on the winning team
            if is_user_winner:
                user_reward = calculate_rewards(user_data.bets[0].amount, user_data.bets[0].market_cap_at_bet, winning_team.market_cap, winning_team.market_cap)
                winning_users.append(user_address)
                user_rewards.append(user_reward)
                logger.info(f"User {user_address} bet on winning team {winning_team.name}")
        except Exception as e:
            logger.error(f"Error checking bets for user {user_address}: {str(e)}")

    if len(winning_users) > 0:
        logger.info(f"Found {len(winning_users)} users who bet on the winning team {winning_team.name}")
        logger.info(f"User rewards: {user_rewards}")

        tx_hash = momentum_contract.functions.setRewards(event_id, winning_users, user_rewards).transact({'from': ACCOUNT_ADDRESS, 'gas': 1000000})
        logger.info(f"Transaction hash: {tx_hash}")

    return {"message": f"Rewards collected for event with ID {event_id}"}

@app.get("/api/users")
async def get_users():
    logger.info("Getting all users")
    return {"users": list(users.values())}

@app.get("/api/users/{address}")
async def get_user(address: str):
    logger.info(f"Getting user with address: {address}")
    if address in users:
        return {"user": users[address]}
    else:
        raise HTTPException(status_code=404, detail="User not found")

@app.on_event("startup")
async def startup_event():
    logger.info("Application starting up - initializing data from historical events")
    
    # First sync events from the contract
    await sync_events_from_contract()
    
    # Then aggregate historical events
    await aggregate_historical_bet_events()
    
    # Finally start listening for new events
    logger.info("Starting event listeners")
    asyncio.create_task(listen_for_bet_events())
    asyncio.create_task(listen_for_event_resolved_events())

async def sync_events_from_contract():
    """
    Sync events from the contract to update our local events list.
    This ensures the event state (active, resolved, paused) is in sync with the blockchain.
    """
    try:
        if not MOMENTUM_MARKETS_ADDRESS or not contract_abi:
            logger.error("Cannot sync events: missing contract address or ABI")
            return

        logger.info(f"Syncing events from contract {MOMENTUM_MARKETS_ADDRESS}")
        
        momentum_contract = w3.eth.contract(
            address=Web3.to_checksum_address(MOMENTUM_MARKETS_ADDRESS),
            abi=contract_abi
        )
        
        # First check for event creation events to ensure we have all events
        # Look back for events up to 10000 blocks (~1.5 days) or from genesis if less
        current_block = w3.eth.block_number
        from_block = max(0, current_block - 10000)
        
        try:
            # Get all EventCreated events
            creation_events = momentum_contract.events.EventCreated.get_logs(
                from_block=from_block,
                to_block=current_block
            )
            
            logger.info(f"Found {len(creation_events)} event creation events")
            
            # Process each creation event to ensure we have all events
            for creation_event in creation_events:
                event_id = creation_event.args.eventId
                event_name = creation_event.args.name
                
                # Check if we already have this event
                existing_event = next((e for e in events if e.id == event_id), None)
                if not existing_event:
                    # This is a new event from the contract we don't have locally
                    logger.info(f"Found new event on chain: ID {event_id}, Name: {event_name}")
                    # We need more info about teams, etc. to create a proper event
                    # For now just log it, you may need to fetch more details from contract
                    # or another source, or implement a fetch_event_details function
            
            # Now update existing events with their current state from contract
            for event in events:
                event_id = event.id
                
                # Get event state from contract
                try:
                    contract_event = momentum_contract.functions.events(event_id).call()
                    
                    # Extract values from contract event
                    if contract_event[0] != 0:  # event exists on chain
                        logger.info(f"Updating state for event ID {event_id} from contract")
                        
                        # Contract event structure (from MomentumMarkets.sol):
                        # uint256 id; (index 0)
                        # string name; (index 1)
                        # bool isActive; (index 2)
                        # bool isResolved; (index 3)
                        # uint256 totalBetAmount; (index 4)
                        # uint256 winningTeamId; (index 5)
                        
                        # Update our event with contract values
                        event.is_active = contract_event[2]
                        event.is_resolved = contract_event[3]
                        event.total_bet_amount = contract_event[4]
                        
                        # Only update status and winner if resolved
                        if contract_event[3]:  # isResolved
                            event.status = "finalized"
                            winning_team_id = contract_event[5]
                            
                            # Contract stores winning team ID as 1-based, convert to index
                            if winning_team_id > 0:
                                winner_index = winning_team_id - 1
                                event.winner_index = winner_index
                                logger.info(f"Event {event_id} has winning team index {winner_index}")
                        else:
                            # Check if the contract is paused
                            try:
                                is_paused = momentum_contract.functions.paused().call()
                                # If contract is paused, all events are effectively paused
                                # This is a global pause. For individual event pause, 
                                # we would need that feature in the contract
                                if is_paused:
                                    event.is_paused = True
                                    logger.info(f"Setting event {event_id} as paused due to contract pause")
                            except Exception as e:
                                logger.error(f"Error checking contract pause state: {str(e)}")
                except Exception as e:
                    logger.error(f"Error fetching event {event_id} from contract: {str(e)}")
            
            logger.info("Finished syncing events from contract")
            
        except Exception as e:
            logger.error(f"Error processing event creation events: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error setting up event sync: {str(e)}")

async def aggregate_historical_bet_events():
    """
    Aggregate historical bet events to initialize the application state.
    This will update market caps based on bet events and build the user list.
    """
    try:
        if not MOMENTUM_MARKETS_ADDRESS or not contract_abi:
            logger.error("Cannot aggregate historical events: missing contract address or ABI")
            return

        momentum_contract = w3.eth.contract(
            address=Web3.to_checksum_address(MOMENTUM_MARKETS_ADDRESS),
            abi=contract_abi
        )
        
        logger.info(f"Aggregating historical BetPlaced events from contract {MOMENTUM_MARKETS_ADDRESS}")
        
        # Get current block number
        current_block = w3.eth.block_number
        
        # Look back for events up to 10000 blocks (~1.5 days) or from genesis if less
        from_block = max(0, current_block - 10000)
        
        logger.info(f"Querying events from block {from_block} to {current_block}")
        
        try:
            # Get all historical bet events
            bet_events = momentum_contract.events.BetPlaced.get_logs(
                from_block=from_block,
                to_block=current_block
            )
            
            logger.info(f"Found {len(bet_events)} historical bet events to process")
            
            # Process each event in chronological order
            for event in bet_events:
                # Process the bet event
                user_address = event.args.user
                event_id = event.args.eventId
                team_id = event.args.teamId
                amount = event.args.amount
                tax_amount = event.args.taxAmount
                net_bet_amount = event.args.netBetAmount
                
                # Find the event in our list
                event_obj = next((e for e in events if e.id == event_id), None)
                if not event_obj:
                    logger.warning(f"Historical event ID {event_id} not found in our events list")
                    continue
                
                # Skip processing if the event is paused or not active
                # For historical events, we still process them regardless of current pause state
                # since they were valid when they were made
                
                # Find the team
                if team_id <= len(event_obj.teams):
                    # Note the index adjustment (team_id starts from 1, list index from 0)
                    team = event_obj.teams[team_id - 1]
                    current_mc = team.market_cap
                    new_mc = calculate_new_market_cap(current_mc, net_bet_amount)
                    # Update the team's market cap
                    team.market_cap = new_mc
                    
                    # Update the event's total bet amount
                    event_obj.total_bet_amount += amount
                    
                    logger.info(f"Updated market cap for team {team.name} to {team.market_cap} from historical bet")
                else:
                    logger.warning(f"Historical Team ID {team_id} not valid for event {event_id}")
                    continue
                
                # Create a new bet record
                new_bet = Bet(
                    event_id=event_id,
                    team_id=team_id,
                    amount=amount,
                    tax_amount=tax_amount,
                    net_bet_amount=net_bet_amount,
                    market_cap_at_bet=team.market_cap
                )
                
                # Update user record
                if user_address in users:
                    # User exists, update their record
                    users[user_address].bets.append(new_bet)
                    logger.info(f"Added historical bet to existing user {user_address}")
                else:
                    # Create a new user with this bet
                    users[user_address] = User(
                        address=user_address,
                        balance=0,  # You might want to fetch this from the contract
                        bets=[new_bet]
                    )
                    logger.info(f"Created new user for address {user_address} from historical bet")
            
            logger.info(f"Completed processing historical bet events. Users: {len(users)}")
            # Log users and their bets in a more readable format
            logger.info(f"Total users: {len(users)}")
            for address, user in users.items():
                logger.info(f"User {address}: Balance: {user.balance}")
                logger.info(f"  Bets for user {address}:")
                for bet in user.bets:
                    logger.info(f"    Event ID: {bet.event_id}, Team ID: {bet.team_id}, Amount: {bet.amount}, Tax: {bet.tax_amount}, Net Amount: {bet.net_bet_amount}, Market Cap at Bet: {bet.market_cap_at_bet}")
            # Log events and team market caps
            logger.info("Current events and team market caps:")
            for event in events:
                logger.info(f"Event ID: {event.id}, Name: {event.name}, Status: {event.status}, Paused: {event.is_paused}")
                logger.info(f"  Teams in this event:")
                for team in event.teams:
                    logger.info(f"    Team ID: {team.id}, Name: {team.name}, Market Cap: {team.market_cap}")
            
        except Exception as e:
            logger.error(f"Error processing historical bet events: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error setting up historical event aggregation: {str(e)}")
        
async def listen_for_bet_events():
    """
    Listen for BetPlaced events from the MomentumMarkets contract and 
    update the users and team market caps
    """
    try:
        if not MOMENTUM_MARKETS_ADDRESS or not contract_abi:
            logger.error("Cannot start event listener: missing contract address or ABI")
            return

        momentum_contract = w3.eth.contract(
            address=Web3.to_checksum_address(MOMENTUM_MARKETS_ADDRESS),
            abi=contract_abi
        )
        
        logger.info(f"Starting to listen for BetPlaced events from contract {MOMENTUM_MARKETS_ADDRESS}")
        
        # Track the last processed block to avoid missing events
        last_processed_block = w3.eth.block_number
        
        while True:
            try:
                # Instead of using a filter that expires, we'll poll for events each cycle
                current_block = w3.eth.block_number
                
                # Get events from the last processed block to the current block
                bet_events = momentum_contract.events.BetPlaced.get_logs(
                    from_block=last_processed_block + 1,
                    to_block=current_block
                )
                
                # Update the last processed block
                last_processed_block = current_block
                
                for event in bet_events:
                    # Process the bet event
                    user_address = event.args.user
                    event_id = event.args.eventId
                    team_id = event.args.teamId
                    amount = event.args.amount
                    tax_amount = event.args.taxAmount
                    net_bet_amount = event.args.netBetAmount
                    
                    # Find the event in our list
                    event_obj = next((e for e in events if e.id == event_id), None)
                    if not event_obj:
                        logger.warning(f"Event ID {event_id} not found in our events list")
                        continue
                    
                    # Skip processing if the event is paused or not active
                    if event_obj.is_paused:
                        logger.warning(f"Event ID {event_id} is paused, but a bet was placed. This may indicate a sync issue.")
                    
                    if not event_obj.is_active:
                        logger.warning(f"Event ID {event_id} is not active, but a bet was placed. This may indicate a sync issue.")
                    
                    # Find the team
                    if team_id <= len(event_obj.teams):
                        # Note the index adjustment (team_id starts from 1, list index from 0)
                        team = event_obj.teams[team_id - 1]
                        current_mc = team.market_cap
                        new_mc = calculate_new_market_cap(current_mc, net_bet_amount)
                        # Update the team's market cap
                        team.market_cap = new_mc
                        
                        # Update the event's total bet amount
                        event_obj.total_bet_amount += amount
                        
                        logger.info(f"Updated market cap for team {team.name} to {team.market_cap}")
                    else:
                        logger.warning(f"Team ID {team_id} not valid for event {event_id}")
                        continue
                    
                    # Create a new bet record
                    new_bet = Bet(
                        event_id=event_id,
                        team_id=team_id,
                        amount=amount,
                        tax_amount=tax_amount,
                        net_bet_amount=net_bet_amount,
                        market_cap_at_bet=team.market_cap
                    )
                    
                    # Update user record
                    if user_address in users:
                        # User exists, update their record
                        users[user_address].bets.append(new_bet)
                        logger.info(f"Added bet to existing user {user_address}")
                    else:
                        # Create a new user with this bet
                        users[user_address] = User(
                            address=user_address,
                            balance=0,  # You might want to fetch this from the contract
                            bets=[new_bet]
                        )
                        logger.info(f"Created new user for address {user_address}")
                
                # Sleep to avoid excessive CPU usage
                await asyncio.sleep(10)
                
            except Exception as e:
                logger.error(f"Error processing bet events: {str(e)}")
                # Don't lose progress on error, just sleep and continue
                await asyncio.sleep(30)  # Sleep longer on error
    
    except Exception as e:
        logger.error(f"Error setting up bet event listener: {str(e)}")
        # Try to restart the listener after a delay if there's a fatal error
        await asyncio.sleep(60)
        asyncio.create_task(listen_for_bet_events())

async def listen_for_event_resolved_events():
    """
    Listen for EventResolved events from the MomentumMarkets contract and 
    update the event status in our local events list
    """
    try:
        if not MOMENTUM_MARKETS_ADDRESS or not contract_abi:
            logger.error("Cannot start event resolver listener: missing contract address or ABI")
            return

        momentum_contract = w3.eth.contract(
            address=Web3.to_checksum_address(MOMENTUM_MARKETS_ADDRESS),
            abi=contract_abi
        )
        
        logger.info(f"Starting to listen for EventResolved events from contract {MOMENTUM_MARKETS_ADDRESS}")
        
        # Track the last processed block to avoid missing events
        last_processed_block = w3.eth.block_number
        
        while True:
            try:
                # Poll for events each cycle
                current_block = w3.eth.block_number
                
                # Get events from the last processed block to the current block
                resolved_events = momentum_contract.events.EventResolved.get_logs(
                    from_block=last_processed_block + 1,
                    to_block=current_block
                )
                
                # Update the last processed block
                last_processed_block = current_block
                
                for resolved_event in resolved_events:
                    # Process the event resolved event
                    event_id = resolved_event.args.eventId
                    winning_team_id = resolved_event.args.winningTeamId
                    
                    logger.info(f"Received EventResolved for event ID {event_id} with winning team ID {winning_team_id}")
                    
                    # Find the event in our list
                    event_obj = next((e for e in events if e.id == event_id), None)
                    if not event_obj:
                        logger.warning(f"Event ID {event_id} not found in our events list")
                        continue
                    
                    # Convert 1-based team ID to 0-based index
                    winner_index = winning_team_id - 1
                    
                    # Update event status
                    event_obj.status = "finalized"
                    event_obj.is_active = False
                    event_obj.is_resolved = True
                    event_obj.winner_index = winner_index
                    
                    # Log the update
                    logger.info(f"Updated event {event_id} to resolved status with winning team index {winner_index}")
                    
                    # Log the winner team name
                    if winner_index < len(event_obj.teams):
                        winning_team = event_obj.teams[winner_index]
                        logger.info(f"Winning team for event {event_id}: {winning_team.name}")
                
                # Sleep to avoid excessive CPU usage
                await asyncio.sleep(10)
                
            except Exception as e:
                logger.error(f"Error processing event resolved events: {str(e)}")
                # Don't lose progress on error, just sleep and continue
                await asyncio.sleep(30)  # Sleep longer on error
    
    except Exception as e:
        logger.error(f"Error setting up event resolver listener: {str(e)}")
        # Try to restart the listener after a delay if there's a fatal error
        await asyncio.sleep(60)
        asyncio.create_task(listen_for_event_resolved_events())
