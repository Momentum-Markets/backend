from web3 import Web3
import os
from dotenv import load_dotenv
from logger import setup_logger

# Initialize logger
logger = setup_logger('web3_provider')

# Load environment variables
load_dotenv()

class Web3Provider:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Web3Provider, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        # Configuration
        self.rpc_url = os.getenv("BASE_TESTNET_RPC_URL", "https://sepolia.base.org")
        self.private_key = os.getenv("PRIVATE_KEY")
        self.account_address = os.getenv("ACCOUNT_ADDRESS")
        
        # Log configuration (without exposing private key)
        if self.private_key and self.account_address:
            logger.info(f"Configuration loaded: RPC_URL={self.rpc_url}, ACCOUNT_ADDRESS={self.account_address[:6]}...{self.account_address[-4:] if len(self.account_address) > 10 else ''}")
        else:
            logger.warning("Missing configuration: PRIVATE_KEY or ACCOUNT_ADDRESS not set in environment variables")
        
        # Set up Web3 connection
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        if self.w3.is_connected():
            logger.info(f"Connected to blockchain at {self.rpc_url}")
        else:
            logger.error(f"Failed to connect to Base Testnet at {self.rpc_url}")
            raise Exception("Failed to connect to Base Testnet")
    
    def get_web3(self):
        return self.w3


# Create a convenience function to get the Web3 instance
def get_web3():
    return Web3Provider().get_web3() 