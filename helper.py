from logger import setup_logger
from web3_provider import get_web3
import json


w3 = get_web3()
logger = setup_logger("helper")

# ERC20 ABI snippet needed for token operations
ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function"
    }
]

MOMENTUM_MARKETS_EVENTS_ABI = json.load(open("abi/MomentumMarkets.json"))

def get_user_and_balances_of_token(token_address: str, user_address: [str]):
    logger.info(f"Getting user and balances of token {token_address} for user {user_address}")
    token_contract = w3.eth.contract(address=token_address, abi=ERC20_ABI)
    
    balances = {}
    for user in user_address:
        balance = token_contract.functions.balanceOf(user).call()
        balances[user] = balance
    
    return balances

def listen_for_events(contract_address: str, from_block=0, to_block='latest'):
    """
    Listen for all events from the MomentumMarkets contract
    """
    logger.info(f"Listening for events from contract {contract_address}")
    contract = w3.eth.contract(address=contract_address, abi=MOMENTUM_MARKETS_EVENTS_ABI)
    
    # Get all events from the contract
    all_events = {
        'rewards_claimed': contract.events.RewardsClaimed,
        'rewards_set': contract.events.RewardsSet,
        'bet_placed': contract.events.BetPlaced,
        'event_created': contract.events.EventCreated,
        'event_resolved': contract.events.EventResolved
    }
    
    event_logs = {}
    
    for event_name, event in all_events.items():
        event_filter = event.createFilter(fromBlock=from_block, toBlock=to_block)
        event_logs[event_name] = event_filter.get_all_entries()
        logger.info(f"Found {len(event_logs[event_name])} {event_name} events")
    
    return event_logs

def listen_for_rewards_claimed(contract_address: str, from_block=0, to_block='latest'):
    """
    Listen specifically for RewardsClaimed events
    """
    logger.info(f"Listening for RewardsClaimed events from contract {contract_address}")
    contract = w3.eth.contract(address=contract_address, abi=MOMENTUM_MARKETS_EVENTS_ABI)
    
    event_filter = contract.events.RewardsClaimed.createFilter(fromBlock=from_block, toBlock=to_block)
    events = event_filter.get_all_entries()
    
    for event in events:
        logger.info(f"RewardsClaimed: User {event['args']['user']} claimed {event['args']['amount']} tokens for event {event['args']['eventId']}")
    
    return events

def listen_for_rewards_set(contract_address: str, from_block=0, to_block='latest'):
    """
    Listen specifically for RewardsSet events
    """
    logger.info(f"Listening for RewardsSet events from contract {contract_address}")
    contract = w3.eth.contract(address=contract_address, abi=MOMENTUM_MARKETS_EVENTS_ABI)
    
    event_filter = contract.events.RewardsSet.createFilter(fromBlock=from_block, toBlock=to_block)
    events = event_filter.get_all_entries()
    
    for event in events:
        logger.info(f"RewardsSet: User {event['args']['user']} was set {event['args']['amount']} tokens for event {event['args']['eventId']}")
    
    return events

def listen_for_bet_placed(contract_address: str, from_block=0, to_block='latest'):
    """
    Listen specifically for BetPlaced events
    """
    logger.info(f"Listening for BetPlaced events from contract {contract_address}")
    contract = w3.eth.contract(address=contract_address, abi=MOMENTUM_MARKETS_EVENTS_ABI)
    
    event_filter = contract.events.BetPlaced.createFilter(fromBlock=from_block, toBlock=to_block)
    events = event_filter.get_all_entries()
    
    for event in events:
        logger.info(f"BetPlaced: User {event['args']['user']} bet {event['args']['amount']} tokens on team {event['args']['teamId']} for event {event['args']['eventId']} (tax: {event['args']['taxAmount']}, net: {event['args']['netBetAmount']})")
    
    return events

def listen_for_event_created(contract_address: str, from_block=0, to_block='latest'):
    """
    Listen specifically for EventCreated events
    """
    logger.info(f"Listening for EventCreated events from contract {contract_address}")
    contract = w3.eth.contract(address=contract_address, abi=MOMENTUM_MARKETS_EVENTS_ABI)
    
    event_filter = contract.events.EventCreated.createFilter(fromBlock=from_block, toBlock=to_block)
    events = event_filter.get_all_entries()
    
    for event in events:
        logger.info(f"EventCreated: Event {event['args']['eventId']} created with name '{event['args']['name']}'")
    
    return events

def listen_for_event_resolved(contract_address: str, from_block=0, to_block='latest'):
    """
    Listen specifically for EventResolved events
    """
    logger.info(f"Listening for EventResolved events from contract {contract_address}")
    contract = w3.eth.contract(address=contract_address, abi=MOMENTUM_MARKETS_EVENTS_ABI)
    
    event_filter = contract.events.EventResolved.createFilter(fromBlock=from_block, toBlock=to_block)
    events = event_filter.get_all_entries()
    
    for event in events:
        logger.info(f"EventResolved: Event {event['args']['eventId']} has been resolved")
    
    return events
    