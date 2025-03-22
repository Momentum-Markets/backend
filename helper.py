from logger import setup_logger
from web3_provider import get_web3
import json
import os
from models import Event, Team, User, Bet
from bet_calculator import calculate_new_market_cap, calculate_rewards, calculate_buy_value_at_close
import asyncio
from typing import List, Dict, Optional
from constants import EVENTS

w3 = get_web3()
logger = setup_logger("helper")

# Global variables
users = {}
finalized_team_market_caps = {}
events = EVENTS

def load_contract_abi(contract_name):
    """Load contract ABI from file"""
    try:
        with open(f'abi/{contract_name}.json', 'r') as f:
            abi = json.load(f)
            logger.info(f"{contract_name} contract ABI loaded successfully")
            return abi
    except FileNotFoundError:
        logger.error(f"Could not find the {contract_name} contract ABI file. Make sure the contract is compiled.")
        return []

def get_contract(contract_address, contract_abi):
    """Get contract instance"""
    return w3.eth.contract(
        address=w3.to_checksum_address(contract_address),
        abi=contract_abi
    )

async def sync_events_from_contract(momentum_markets_address, contract_abi):
    """
    Sync events from the contract to update our local events list.
    This ensures the event state (active, resolved, paused) is in sync with the blockchain.
    """
    try:
        if not momentum_markets_address or not contract_abi:
            logger.error("Cannot sync events: missing contract address or ABI")
            return

        logger.info(f"Syncing events from contract {momentum_markets_address}")
        
        momentum_contract = get_contract(momentum_markets_address, contract_abi)
        
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

async def aggregate_historical_bet_events(momentum_markets_address, contract_abi):
    """
    Aggregate historical bet events to initialize the application state.
    This will update market caps based on bet events and build the user list.
    """
    try:
        if not momentum_markets_address or not contract_abi:
            logger.error("Cannot aggregate historical events: missing contract address or ABI")
            return

        momentum_contract = get_contract(momentum_markets_address, contract_abi)
        
        logger.info(f"Aggregating historical BetPlaced events from contract {momentum_markets_address}")
        
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
                process_bet_event(event.args.user, event.args.eventId, event.args.teamId, 
                                 event.args.amount, event.args.taxAmount, event.args.netBetAmount)
            
            log_application_state()
            
        except Exception as e:
            logger.error(f"Error processing historical bet events: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error setting up historical event aggregation: {str(e)}")

def process_bet_event(user_address, event_id, team_id, amount, tax_amount, net_bet_amount):
    """Process a bet event and update the application state"""
    # Find the event in our list
    event_obj = next((e for e in events if e.id == event_id), None)
    if not event_obj:
        logger.warning(f"Event ID {event_id} not found in our events list")
        return
    
    # Find the team
    team = next((t for t in event_obj.teams if t.id == team_id), None)
    if not team:
        logger.warning(f"Team ID {team_id} not valid for event {event_id}")
        return
    
    # Update market cap
    current_mc = team.market_cap
    new_mc = calculate_new_market_cap(current_mc, net_bet_amount)
    
    # Update the team's market cap
    team.market_cap = new_mc
    
    # Update the team in the teams array
    for i, t in enumerate(event_obj.teams):
        if t.id == team_id:
            event_obj.teams[i] = team
            break
    
    # Update the event's total bet amount
    event_obj.total_bet_amount += amount
    
    # Update the event in the global events list
    for i, e in enumerate(events):
        if e.id == event_id:
            events[i] = event_obj
            break
    
    # Update the finalized_team_market_caps dictionary
    finalized_team_market_caps[team_id] = team.market_cap
    
    logger.info(f"Updated market cap for team {team.name} to {team.market_cap}")
    
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

def log_application_state():
    """Log the current state of the application (users, events, market caps)"""
    logger.info(f"Total users: {len(users)}")
    for address, user in users.items():
        logger.info(f"User {address}: Balance: {user.balance}")
        logger.info(f"  Bets for user {address}:")
        for bet in user.bets:
            logger.info(f"    Event ID: {bet.event_id}, Team ID: {bet.team_id}, Amount: {bet.amount}, "
                        f"Tax: {bet.tax_amount}, Net Amount: {bet.net_bet_amount}, "
                        f"Market Cap at Bet: {bet.market_cap_at_bet}")
            
    logger.info("Current events and team market caps:")
    for event in events:
        logger.info(f"Event ID: {event.id}, Name: {event.name}, Status: {event.status}, "
                   f"Paused: {event.is_paused}")
        logger.info(f"  Teams in this event:")
        for team in event.teams:
            logger.info(f"    Team ID: {team.id}, Name: {team.name}, Market Cap: {team.market_cap}")
            finalized_team_market_caps[team.id] = team.market_cap

async def listen_for_bet_events(momentum_markets_address, contract_abi):
    """
    Listen for BetPlaced events from the MomentumMarkets contract and 
    update the users and team market caps
    """
    try:
        if not momentum_markets_address or not contract_abi:
            logger.error("Cannot start event listener: missing contract address or ABI")
            return

        momentum_contract = get_contract(momentum_markets_address, contract_abi)
        
        logger.info(f"Starting to listen for BetPlaced events from contract {momentum_markets_address}")
        
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
                    # Process the bet event using our shared function
                    process_bet_event(
                        event.args.user, 
                        event.args.eventId, 
                        event.args.teamId,
                        event.args.amount, 
                        event.args.taxAmount, 
                        event.args.netBetAmount
                    )
                
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
        asyncio.create_task(listen_for_bet_events(momentum_markets_address, contract_abi))

async def listen_for_event_resolved_events(momentum_markets_address, contract_abi):
    """
    Listen for EventResolved events from the MomentumMarkets contract and 
    update the event status in our local events list
    """
    try:
        if not momentum_markets_address or not contract_abi:
            logger.error("Cannot start event resolver listener: missing contract address or ABI")
            return

        momentum_contract = get_contract(momentum_markets_address, contract_abi)
        
        logger.info(f"Starting to listen for EventResolved events from contract {momentum_markets_address}")
        
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
        asyncio.create_task(listen_for_event_resolved_events(momentum_markets_address, contract_abi))

def resolve_event(momentum_markets_address, contract_abi, account_address, event_id, winner_index):
    """Resolve an event by setting the winner"""
    try:
        momentum_contract = get_contract(momentum_markets_address, contract_abi)
        
        # Check if event is resolved
        event = momentum_contract.functions.events(event_id).call()
        if event[3]:  # is_resolved
            logger.error(f"Event {event_id} is already resolved")
            return None, "Event is already resolved"

        # Resolve the event
        tx_hash = momentum_contract.functions.resolveEvent(
            event_id, winner_index
        ).transact({'from': account_address, 'gas': 1000000})
        
        logger.info(f"Transaction hash for resolving event {event_id}: {tx_hash.hex()}")
        
        # Update local event status
        event_obj = next((e for e in events if e.id == event_id), None)
        if event_obj:
            event_obj.status = "finalized"
            event_obj.is_active = False
            event_obj.is_resolved = True
            event_obj.winner_index = winner_index
            
            # Update in global events list
            for i, e in enumerate(events):
                if e.id == event_id:
                    events[i] = event_obj
                    break
            
            logger.info(f"Event with ID {event_id} finalized in application state")
            
        return tx_hash.hex(), "Event finalized successfully"
    
    except Exception as e:
        logger.error(f"Error resolving event {event_id}: {str(e)}")
        return None, str(e)

def set_rewards(momentum_markets_address, contract_abi, account_address, event_id):
    """Calculate and set rewards for users who bet on the winning team"""
    try:
        momentum_contract = get_contract(momentum_markets_address, contract_abi)
        
        # Check if event is resolved
        event = momentum_contract.functions.events(event_id).call()
        if not event[3]:  # not is_resolved
            logger.error(f"Event {event_id} is not resolved yet")
            return None, "Event is not resolved yet"
            
        # Get winning team id
        winning_team_id = int(event[5])  # winningTeamId
        if not winning_team_id:
            logger.error(f"No winning team set for event {event_id}")
            return None, "Winning team is not found"
        
        event_obj = next((e for e in events if e.id == event_id), None)
        if not event_obj:
            logger.error(f"Event {event_id} not found in local events")
            return None, "Event not found"
            
        # Get winning team and losing team
        winning_team = next((t for t in event_obj.teams if t.id == winning_team_id), None)
        losing_team = next((t for t in event_obj.teams if t.id != winning_team_id), None)
        
        if not winning_team or not losing_team:
            logger.error(f"Failed to identify winning/losing teams for event {event_id}")
            return None, "Teams could not be determined"
            
        # Calculate the total bet amount for the losing team (available liquidity)
        total_losing_team_bets = sum(
            user.bets[0].amount
            for user in users.values()
            if user.bets and user.bets[0].team_id == losing_team.id and user.bets[0].amount > 0
        )
        
        losing_team_liquidity = total_losing_team_bets
        logger.info(f"Total losing team bets: {total_losing_team_bets}")
        logger.info(f"Losing team available liquidity: {losing_team_liquidity}")
        
        # Prepare lists for winner's addresses and rewards
        winning_users = []
        user_rewards = []
        
        # Calculate rewards for each winning user
        for user_address, user_data in users.items():
            try:
                # Check if user bet on the winning team
                if (user_data.bets and 
                    user_data.bets[0].team_id == winning_team_id and 
                    user_data.bets[0].amount > 0):
                    
                    logger.info(f"User {user_address} bought at market cap: {user_data.bets[0].market_cap_at_bet}")
                    
                    # Calculate rewards
                    user_reward = calculate_rewards(
                        user_data.bets[0].amount, 
                        user_data.bets[0].market_cap_at_bet, 
                        winning_team.market_cap, 
                        losing_team.market_cap, 
                        losing_team_liquidity=losing_team_liquidity, 
                        winning_team_id=winning_team_id
                    )
                    
                    # Calculate buy value at close based on market cap growth
                    buy_value = calculate_buy_value_at_close(
                        user_data.bets[0].amount, 
                        user_data.bets[0].market_cap_at_bet, 
                        winning_team.market_cap
                    )
                    
                    winning_users.append(user_address)
                    user_rewards.append(user_reward["estimatedSSBReward"])
                    
                    logger.info(f"User {user_address} bet on winning team {winning_team.name}")
                    logger.info(f"Buy value at close: ${buy_value['buyValueAtClose']:.2f} (growth factor: {buy_value['growthFactor']:.2f}x)")
            except Exception as e:
                logger.error(f"Error calculating rewards for user {user_address}: {str(e)}")
                
        if not winning_users:
            logger.warning(f"No users found who bet on the winning team {winning_team.name}")
            return None, "No users found who bet on the winning team"
            
        logger.info(f"Found {len(winning_users)} users who bet on the winning team {winning_team.name}")
        logger.info(f"User rewards: {user_rewards}")
        
        # Set rewards in the contract
        tx_hash = momentum_contract.functions.setRewards(
            event_id, winning_users, user_rewards
        ).transact({'from': account_address, 'gas': 1000000})
        
        logger.info(f"Transaction hash for setting rewards for event {event_id}: {tx_hash.hex()}")
        return tx_hash.hex(), f"Rewards set for {len(winning_users)} users"
        
    except Exception as e:
        logger.error(f"Error setting rewards for event {event_id}: {str(e)}")
        return None, str(e)

def get_all_events():
    """Get all events"""
    return events

def get_event(event_id):
    """Get event by ID"""
    return next((e for e in events if e.id == event_id), None)

def get_all_users():
    """Get all users"""
    return list(users.values())

def get_user(address):
    """Get user by address"""
    return users.get(address)
