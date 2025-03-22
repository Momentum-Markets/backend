import pandas as pd
import math
from typing import List, Dict, Literal, Tuple
from logger import setup_logger


logger = setup_logger("bet_calculator")

# Type for the team
Team = Literal["Team 1", "Team 2"]

# Constants
INITIAL_MC = 100_000
TAX_RATE = 0.05
BET_POOL_PERCENTAGE = 1 - TAX_RATE
INITIAL_LIQUIDITY = 10_000

# Function to calculate total liquidity


def totalliquidity(market_cap: float) -> float:
    return 10000 * math.sqrt(market_cap / 100000)

# Function to calculate available liquidity


def availableliquidity(market_cap: float) -> float:
    if market_cap <= 100000:
        return 0
    return totalliquidity(market_cap) - 10000

# Function to calculate new market cap


def calculate_new_market_cap(current_mc: float, post_tax_buy: float) -> float:
    mc_ratio = current_mc / 100000
    mc_increase_factor = 20 * math.sqrt(mc_ratio)
    mc_increase = post_tax_buy * mc_increase_factor
    return int(current_mc + mc_increase)

# Function to calculate rewards
def losing_team_share_of_liquidity(user_rewards_percentage: float, losing_team_liquidity: float) -> float:
    return (user_rewards_percentage / 100) * losing_team_liquidity


def calculate_rewards(
    user_bet_amount: float,
    user_buy_mc: float,
    team1_final_mc: float,
    team2_final_mc: float,
    losing_team_liquidity: float,
    winning_team_id: int
) -> Dict:
    winning_team_final_mc = team1_final_mc if winning_team_id == 1 else team2_final_mc
    losing_team_final_mc = team2_final_mc if winning_team_id == 1 else team1_final_mc
    user_tax_paid = user_bet_amount * TAX_RATE  # Calculate tax paid

    user_post_tax_bet = user_bet_amount * BET_POOL_PERCENTAGE

    # Fix: Calculate the percentage based on the user's contribution relative to market cap
    # Current calculation is incorrect as it divides market cap by liquidity
    user_rewards_percentage = (user_post_tax_bet / user_buy_mc) * 100
    logger.info(f"User rewards percentage: {user_rewards_percentage}")
    losing_team_share_of_liquidity_val = losing_team_share_of_liquidity(user_rewards_percentage, losing_team_liquidity) * 10
    logger.info(f"Losing team share of liquidity: {losing_team_share_of_liquidity_val}")
    # Return all values including percentage-based reward and profit increase
    return {
        "taxPaid": user_tax_paid,
        "userPostTaxBet": user_post_tax_bet,
        "estimatedSSBReward": user_post_tax_bet + losing_team_share_of_liquidity_val,
    }

def calculate_buy_value_at_close(user_bet_amount: float, user_buy_mc: float, final_mc: float) -> Dict:
    """
    Calculate the value of a user's bet at event close, based on market cap growth.
    
    Args:
        user_bet_amount: The amount the user bet
        user_buy_mc: The market cap at the time of the user's bet
        final_mc: The final market cap at event close
        
    Returns:
        Dict containing the post-tax bet amount, growth factor, and buy value at close
    """
    # Calculate post-tax bet amount
    user_post_tax_bet = user_bet_amount * BET_POOL_PERCENTAGE
    
    # Calculate market cap growth factor
    growth_factor = final_mc / user_buy_mc
    
    # Calculate buy value at close
    buy_value_at_close = user_post_tax_bet * growth_factor
    
    logger.info(f"Initial bet: ${user_bet_amount}, Post-tax: ${user_post_tax_bet}")
    logger.info(f"MC at buy: ${user_buy_mc}, Final MC: ${final_mc}, Growth factor: {growth_factor:.2f}x")
    logger.info(f"Buy value at close: ${buy_value_at_close:.2f}")
    
    return {
        "userPostTaxBet": user_post_tax_bet,
        "growthFactor": growth_factor,
        "buyValueAtClose": buy_value_at_close
    }