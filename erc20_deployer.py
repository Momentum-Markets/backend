from web3 import Web3
import json
import os
from dotenv import load_dotenv
from logger import setup_logger

# Initialize logger
logger = setup_logger('erc20_deployer')

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

# Standard ERC20 ABI with more features
ERC20_FULL_ABI = [
    # Token metadata functions
    {"inputs":[],"name":"name","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"symbol","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"decimals","outputs":[{"internalType":"uint8","name":"","type":"uint8"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"totalSupply","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    
    # Basic ERC20 functions
    {"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"transfer","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"address","name":"owner","type":"address"},{"internalType":"address","name":"spender","type":"address"}],"name":"allowance","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"approve","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"address","name":"from","type":"address"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"transferFrom","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},
    
    # Minting capability (for admin)
    {"inputs":[{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"mint","outputs":[],"stateMutability":"nonpayable","type":"function"},
    
    # Events
    {"anonymous":False,"inputs":[{"indexed":True,"internalType":"address","name":"from","type":"address"},{"indexed":True,"internalType":"address","name":"to","type":"address"},{"indexed":False,"internalType":"uint256","name":"value","type":"uint256"}],"name":"Transfer","type":"event"},
    {"anonymous":False,"inputs":[{"indexed":True,"internalType":"address","name":"owner","type":"address"},{"indexed":True,"internalType":"address","name":"spender","type":"address"},{"indexed":False,"internalType":"uint256","name":"value","type":"uint256"}],"name":"Approval","type":"event"}
]

# Standard ERC20 bytecode with constructor parameters
# This is a template for an ERC20 token with constructor parameters: name, symbol, initial supply, decimals
ERC20_BYTECODE = "0x60806040523480156200001157600080fd5b5060405162000d3138038062000d318339810160408190526200003491620001c1565b6040518060400160405280600a81526020016926bcaa37b5b2b73232b960b11b8152506040518060400160405280600684526020016505553442d4360d41b81525081600390805190602001906200008d92919062000108565b508051620000a390600490602084019062000108565b505050620000b833620000be60201b60201c565b5050506200022a565b6001600160a01b038216620001195760405162461bcd60e51b815260206004820152601f60248201527f45524332303a206d696e7420746f20746865207a65726f206164647265737300604482015260640160405180910390fd5b80600260008282546200012d91906200020d565b90915550506001600160a01b03821660009081526020819052604081208054839290620001fc9084906200020d565b90915550506040518181526001600160a01b038316906000907fddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef9060200160405180910390a35050565b828054620001169062000226565b90600052602060002090601f0160209004810192826200013a576000855562000185565b82601f106200015557805160ff191683800117855562000185565b8280016001018555821562000185579182015b828111156200018557825182559160200191906001019062000168565b50620001939291506200019756ffffffffffffffffffffffffffffffffffffffffffff3c"

# Set up Web3 connection
w3 = Web3(Web3.HTTPProvider(RPC_URL))
if w3.is_connected():
    logger.info(f"Connected to blockchain at {RPC_URL}")
else:
    logger.error(f"Failed to connect to blockchain at {RPC_URL}")

def deploy_erc20_token(
    name: str, 
    symbol: str, 
    initial_supply: int, 
    decimals: int = 18,
    private_key: str = None, 
    sender_address: str = None
) -> dict:
    """
    Deploy a new ERC20 token with custom parameters.
    
    Args:
        name: Token name (e.g., "My Token")
        symbol: Token symbol (e.g., "MTK")
        initial_supply: Initial supply in token units (will be multiplied by 10^decimals)
        decimals: Token decimals (default: 18)
        private_key: Private key for transaction signing (defaults to env var)
        sender_address: Address of the token creator (defaults to env var)
    
    Returns:
        Dictionary with transaction hash and contract address
    """
    logger.info(f"Deploying new ERC20 token: name={name}, symbol={symbol}, initial_supply={initial_supply}, decimals={decimals}")
    
    if not w3.is_connected():
        error_msg = f"Failed to connect to blockchain at {RPC_URL}"
        logger.error(error_msg)
        raise Exception(error_msg)
    
    # Use provided keys or fall back to environment variables
    private_key = private_key or PRIVATE_KEY
    sender_address = sender_address or ACCOUNT_ADDRESS
    
    if not private_key or not sender_address:
        error_msg = "Private key and sender address must be provided or set in .env file"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    # Log the sender address (partially masked)
    masked_address = f"{sender_address[:6]}...{sender_address[-4:]}" if len(sender_address) > 10 else sender_address
    logger.info(f"Using sender address: {masked_address}")
    
    try:
        # Prepare the constructor arguments
        # Convert initial_supply to token units (with decimals)
        initial_supply_in_wei = initial_supply * (10 ** decimals)
        logger.debug(f"Initial supply in wei: {initial_supply_in_wei}")
        
        # Create contract factory with the ABI and bytecode
        token_contract = w3.eth.contract(abi=ERC20_FULL_ABI, bytecode=ERC20_BYTECODE)
        
        # Build the constructor transaction
        constructor_data = token_contract.constructor(
            name, 
            symbol, 
            initial_supply_in_wei, 
            decimals
        ).build_transaction({
            'from': sender_address,
            'gas': 2000000,
            'gasPrice': w3.to_wei('50', 'gwei'),
            'nonce': w3.eth.get_transaction_count(sender_address),
        })
        
        logger.debug(f"Transaction built with gas limit: {constructor_data['gas']}")
        
        # Sign the transaction
        signed_tx = w3.eth.account.sign_transaction(constructor_data, private_key=private_key)
        logger.debug("Transaction signed successfully")
        
        # Send the transaction
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        logger.info(f"Deploy transaction sent, hash: {tx_hash.hex()}")
        
        # Wait for the transaction receipt
        logger.info("Waiting for transaction confirmation...")
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        # Get the contract address
        contract_address = tx_receipt.contractAddress
        logger.info(f"Token deployed successfully at address: {contract_address}")
        
        result = {
            'tx_hash': tx_hash.hex(),
            'contract_address': contract_address,
            'token_name': name,
            'token_symbol': symbol,
            'decimals': decimals,
            'initial_supply': initial_supply,
        }
        logger.debug(f"Deployment result: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error deploying token: {str(e)}", exc_info=True)
        raise

def get_token_details(contract_address: str) -> dict:
    """
    Get details about a deployed ERC20 token.
    
    Args:
        contract_address: Address of the deployed ERC20 token
    
    Returns:
        Dictionary with token details
    """
    logger.info(f"Getting token details for contract: {contract_address}")
    
    token = w3.eth.contract(address=contract_address, abi=ERC20_FULL_ABI)
    
    try:
        name = token.functions.name().call()
        symbol = token.functions.symbol().call()
        decimals = token.functions.decimals().call()
        total_supply = token.functions.totalSupply().call()
        
        logger.info(f"Retrieved token details: {name} ({symbol})")
        logger.debug(f"Token decimals: {decimals}, total supply: {total_supply}")
        
        result = {
            'address': contract_address,
            'name': name,
            'symbol': symbol,
            'decimals': decimals,
            'total_supply': total_supply / (10 ** decimals),
            'total_supply_raw': total_supply
        }
        return result
    except Exception as e:
        logger.error(f"Error getting token details: {str(e)}", exc_info=True)
        return {'error': str(e), 'address': contract_address}

def mint_tokens(
    contract_address: str, 
    to_address: str, 
    amount: int, 
    decimals: int = 18,
    private_key: str = None, 
    sender_address: str = None
) -> str:
    """
    Mint new tokens and send them to the specified address.
    
    Args:
        contract_address: Address of the deployed ERC20 token
        to_address: Address to receive the minted tokens
        amount: Amount to mint in token units (will be multiplied by 10^decimals)
        decimals: Token decimals (default: 18)
        private_key: Private key for transaction signing (defaults to env var)
        sender_address: Address of the token creator (defaults to env var)
    
    Returns:
        Transaction hash
    """
    logger.info(f"Minting {amount} tokens to address: {to_address}")
    
    # Use provided keys or fall back to environment variables
    private_key = private_key or PRIVATE_KEY
    sender_address = sender_address or ACCOUNT_ADDRESS
    
    if not private_key or not sender_address:
        error_msg = "Private key and sender address must be provided or set in .env file"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    try:
        # Convert amount to token units with decimals
        amount_in_wei = amount * (10 ** decimals)
        logger.debug(f"Mint amount in wei: {amount_in_wei}")
        
        # Create contract instance
        token = w3.eth.contract(address=contract_address, abi=ERC20_FULL_ABI)
        
        # Build mint transaction
        tx = token.functions.mint(to_address, amount_in_wei).build_transaction({
            'from': sender_address,
            'gas': 200000,
            'gasPrice': w3.to_wei('50', 'gwei'),
            'nonce': w3.eth.get_transaction_count(sender_address),
        })
        
        logger.debug(f"Mint transaction built with gas limit: {tx['gas']}")
        
        # Sign and send transaction
        signed_tx = w3.eth.account.sign_transaction(tx, private_key=private_key)
        logger.debug("Transaction signed successfully")
        
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        logger.info(f"Mint transaction sent, hash: {tx_hash.hex()}")
        
        return tx_hash.hex()
    except Exception as e:
        logger.error(f"Error minting tokens: {str(e)}", exc_info=True)
        raise

# Example usage
if __name__ == "__main__":
    # Example: Deploy a new token
    # result = deploy_erc20_token(
    #     name="My Test Token",
    #     symbol="MTT",
    #     initial_supply=1000000,  # 1 million tokens
    #     decimals=18
    # )
    # print(f"Deployed token at: {result['contract_address']}")
    
    # Example: Get token details
    # details = get_token_details("0x1234...")  # Replace with actual address
    # print(f"Token: {details['name']} ({details['symbol']})")
    # print(f"Total Supply: {details['total_supply']} {details['symbol']}")
    
    # Example: Mint more tokens
    # tx_hash = mint_tokens(
    #     contract_address="0x1234...",  # Replace with actual address
    #     to_address="0xabcd...",  # Replace with recipient address
    #     amount=5000,  # 5000 tokens
    #     decimals=18
    # )
    # print(f"Minted tokens in transaction: {tx_hash}")
    logger.info("Import this module to use the ERC20 token deployment functions") 