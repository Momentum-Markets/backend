from web3 import Web3
import json
import os
from dotenv import load_dotenv
from logger import setup_logger
import time

# Initialize logger
logger = setup_logger('momentum_markets')

# Load environment variables
load_dotenv()
logger.info("Environment variables loaded")

# Configuration
RPC_URL = os.getenv("BASE_TESTNET_RPC_URL", "https://sepolia.base.org")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
ACCOUNT_ADDRESS = os.getenv("ACCOUNT_ADDRESS")

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
    logger.error(f"Failed to connect to blockchain at {RPC_URL}")

# ABIs (These would typically be loaded from JSON files)
MOMENTUM_MARKETS_ABI = [] # Placeholder
TEAM_TOKEN_ABI = [] # Placeholder

# Contract addresses (to be set after deployment)
momentum_markets_address = None

def deploy_momentum_markets(eth_usd_price_feed, liquidity_fee_recipient, development_fee_recipient, community_fee_recipient):
    """
    Deploy the MomentumMarkets contract
    
    Args:
        eth_usd_price_feed: Address of the ETH/USD price feed contract
        liquidity_fee_recipient: Address to receive liquidity fees (3%)
        development_fee_recipient: Address to receive development fees (1%)
        community_fee_recipient: Address to receive community fees (1%)
        
    Returns:
        Dictionary with transaction hash and contract address
    """
    logger.info("Deploying MomentumMarkets contract")

    # This would load the contract bytecode from a file
    bytecode = "" # Placeholder - would be loaded from compilation output
    
    momentum_markets = w3.eth.contract(abi=MOMENTUM_MARKETS_ABI, bytecode=bytecode)
    
    # Build constructor transaction
    constructor_data = momentum_markets.constructor(
        eth_usd_price_feed,
        liquidity_fee_recipient,
        development_fee_recipient,
        community_fee_recipient
    ).build_transaction({
        'from': ACCOUNT_ADDRESS,
        'gas': 5000000,
        'gasPrice': w3.to_wei('50', 'gwei'),
        'nonce': w3.eth.get_transaction_count(ACCOUNT_ADDRESS),
    })
    
    # Sign and send transaction
    signed_tx = w3.eth.account.sign_transaction(constructor_data, private_key=PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    
    logger.info(f"MomentumMarkets deployment transaction sent, hash: {tx_hash.hex()}")
    
    # Wait for transaction receipt
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    contract_address = tx_receipt.contractAddress
    
    logger.info(f"MomentumMarkets deployed at address: {contract_address}")
    
    # Store contract address for future use
    global momentum_markets_address
    momentum_markets_address = contract_address
    
    return {
        'tx_hash': tx_hash.hex(),
        'contract_address': contract_address
    }

def deploy_team_tokens(event_id, event_name, team1_name, team2_name):
    """
    Deploy two team tokens for a betting event
    
    Args:
        event_id: ID of the event
        event_name: Name of the event
        team1_name: Name of team 1
        team2_name: Name of team 2
        
    Returns:
        Dictionary with team token addresses
    """
    logger.info(f"Deploying team tokens for event {event_id}: {team1_name} vs {team2_name}")
    
    if not momentum_markets_address:
        raise ValueError("MomentumMarkets contract must be deployed first")
    
    # This would load the contract bytecode from a file
    bytecode = "" # Placeholder - would be loaded from compilation output
    
    # Deploy Team 1 Token
    team1_token_name = f"BMM: {team1_name}"
    team1_token_symbol = f"BMM-{team1_name[:4].upper()}"
    
    team1_token = w3.eth.contract(abi=TEAM_TOKEN_ABI, bytecode=bytecode)
    team1_constructor = team1_token.constructor(
        team1_token_name,
        team1_token_symbol,
        team1_name,
        event_name,
        event_id,
        momentum_markets_address
    ).build_transaction({
        'from': ACCOUNT_ADDRESS,
        'gas': 3000000,
        'gasPrice': w3.to_wei('50', 'gwei'),
        'nonce': w3.eth.get_transaction_count(ACCOUNT_ADDRESS),
    })
    
    signed_tx1 = w3.eth.account.sign_transaction(team1_constructor, private_key=PRIVATE_KEY)
    tx_hash1 = w3.eth.send_raw_transaction(signed_tx1.rawTransaction)
    tx_receipt1 = w3.eth.wait_for_transaction_receipt(tx_hash1)
    team1_address = tx_receipt1.contractAddress
    
    logger.info(f"Team 1 token deployed at address: {team1_address}")
    
    # Wait briefly between deployments
    time.sleep(2)
    
    # Deploy Team 2 Token
    team2_token_name = f"BMM: {team2_name}"
    team2_token_symbol = f"BMM-{team2_name[:4].upper()}"
    
    team2_token = w3.eth.contract(abi=TEAM_TOKEN_ABI, bytecode=bytecode)
    team2_constructor = team2_token.constructor(
        team2_token_name,
        team2_token_symbol,
        team2_name,
        event_name,
        event_id,
        momentum_markets_address
    ).build_transaction({
        'from': ACCOUNT_ADDRESS,
        'gas': 3000000,
        'gasPrice': w3.to_wei('50', 'gwei'),
        'nonce': w3.eth.get_transaction_count(ACCOUNT_ADDRESS),
    })
    
    signed_tx2 = w3.eth.account.sign_transaction(team2_constructor, private_key=PRIVATE_KEY)
    tx_hash2 = w3.eth.send_raw_transaction(signed_tx2.rawTransaction)
    tx_receipt2 = w3.eth.wait_for_transaction_receipt(tx_hash2)
    team2_address = tx_receipt2.contractAddress
    
    logger.info(f"Team 2 token deployed at address: {team2_address}")
    
    return {
        'event_id': event_id,
        'event_name': event_name,
        'team1_name': team1_name,
        'team1_token_address': team1_address,
        'team1_token_name': team1_token_name,
        'team1_token_symbol': team1_token_symbol,
        'team2_name': team2_name,
        'team2_token_address': team2_address,
        'team2_token_name': team2_token_name,
        'team2_token_symbol': team2_token_symbol
    }

def create_event(name, start_time, end_time, team1_token, team2_token):
    """
    Create a new betting event on the MomentumMarkets platform
    
    Args:
        name: Name of the event
        start_time: Start timestamp of the event (UNIX timestamp)
        end_time: End timestamp of the event (UNIX timestamp)
        team1_token: Address of team 1 token
        team2_token: Address of team 2 token
        
    Returns:
        Event ID and transaction details
    """
    logger.info(f"Creating event: {name}")
    
    if not momentum_markets_address:
        raise ValueError("MomentumMarkets contract must be deployed first")
    
    # Get contract instance
    momentum_markets = w3.eth.contract(address=momentum_markets_address, abi=MOMENTUM_MARKETS_ABI)
    
    # Build transaction
    tx = momentum_markets.functions.createEvent(
        name,
        start_time,
        end_time,
        team1_token,
        team2_token
    ).build_transaction({
        'from': ACCOUNT_ADDRESS,
        'gas': 500000,
        'gasPrice': w3.to_wei('50', 'gwei'),
        'nonce': w3.eth.get_transaction_count(ACCOUNT_ADDRESS),
    })
    
    # Sign and send transaction
    signed_tx = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    
    logger.info(f"Event creation transaction sent, hash: {tx_hash.hex()}")
    
    # Wait for transaction receipt
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    
    # Parse event logs to get event ID
    event_id = None
    for log in tx_receipt.logs:
        try:
            parsed_log = momentum_markets.events.EventCreated().process_log(log)
            event_id = parsed_log.args.eventId
            break
        except:
            continue
    
    if event_id is not None:
        logger.info(f"Event created with ID: {event_id}")
    else:
        logger.warning("Could not determine event ID from transaction logs")
    
    return {
        'tx_hash': tx_hash.hex(),
        'event_id': event_id
    }

def settle_event(event_id, winning_team):
    """
    Settle an event by determining the winner
    
    Args:
        event_id: ID of the event
        winning_team: Address of the winning team token
        
    Returns:
        Transaction details
    """
    logger.info(f"Settling event {event_id} with winning team {winning_team}")
    
    if not momentum_markets_address:
        raise ValueError("MomentumMarkets contract must be deployed first")
    
    # Get contract instance
    momentum_markets = w3.eth.contract(address=momentum_markets_address, abi=MOMENTUM_MARKETS_ABI)
    
    # Build transaction
    tx = momentum_markets.functions.settleEvent(
        event_id,
        winning_team
    ).build_transaction({
        'from': ACCOUNT_ADDRESS,
        'gas': 300000,
        'gasPrice': w3.to_wei('50', 'gwei'),
        'nonce': w3.eth.get_transaction_count(ACCOUNT_ADDRESS),
    })
    
    # Sign and send transaction
    signed_tx = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    
    logger.info(f"Event settlement transaction sent, hash: {tx_hash.hex()}")
    
    # Wait for transaction receipt
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    
    return {
        'tx_hash': tx_hash.hex(),
        'event_id': event_id,
        'winning_team': winning_team
    }

def get_event_details(event_id):
    """
    Get details about a betting event
    
    Args:
        event_id: ID of the event
        
    Returns:
        Dictionary with event details
    """
    logger.info(f"Getting details for event {event_id}")
    
    if not momentum_markets_address:
        raise ValueError("MomentumMarkets contract must be deployed first")
    
    # Get contract instance
    momentum_markets = w3.eth.contract(address=momentum_markets_address, abi=MOMENTUM_MARKETS_ABI)
    
    # Call function
    event_data = momentum_markets.functions.events(event_id).call()
    
    # Format result
    event_details = {
        'id': event_data[0],
        'name': event_data[1],
        'start_time': event_data[2],
        'end_time': event_data[3],
        'is_active': event_data[4],
        'is_settled': event_data[5],
        'team1_token': event_data[6],
        'team2_token': event_data[7],
        'team1_pool': event_data[8],
        'team2_pool': event_data[9],
        'winner': event_data[10]
    }
    
    # Get team token details
    team1_token = w3.eth.contract(address=event_details['team1_token'], abi=TEAM_TOKEN_ABI)
    team2_token = w3.eth.contract(address=event_details['team2_token'], abi=TEAM_TOKEN_ABI)
    
    event_details['team1_name'] = team1_token.functions.teamName().call()
    event_details['team2_name'] = team2_token.functions.teamName().call()
    
    return event_details 