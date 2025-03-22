import pandas as pd
import math
from typing import List, Dict, Literal, Tuple

# Type for the team
Team = Literal["Team 1", "Team 2"]

# Constants
INITIAL_MC = 100_000
TAX_RATE = 0.05
BET_POOL_PERCENTAGE = 1 - TAX_RATE
INITIAL_LIQUIDITY = 10_000

# Function to calculate total liquidity


def totalliquidity(market_cap: float) -> float:
    return 100000 * math.sqrt(market_cap / 100000)

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
    return current_mc + mc_increase

# Function to simulate market cap growth


def simulate_market_cap_growth(
    final_mc: float,
    user_bet_amount: float,
    user_buy_mc: float,
    standard_buy_size: float = 100
) -> Tuple[float, List[Dict], float, float]:
    simulation_data = []
    user_buy_mc_value = user_buy_mc * 1000
    post_tax_standard_buy = standard_buy_size * BET_POOL_PERCENTAGE
    user_post_tax_buy = user_bet_amount * BET_POOL_PERCENTAGE
    all_buy_values_at_close = []

    current_mc = INITIAL_MC
    buy_number = 1
    user_buy_value_at_close = 0
    user_buy_included = False
    max_buys = 10000

    while current_mc < final_mc and buy_number <= max_buys:
        if not user_buy_included and user_buy_mc_value <= current_mc:
            user_buy_value_at_close = (
                user_post_tax_buy * final_mc) / current_mc
            all_buy_values_at_close = []

        opening_mc = current_mc
        new_mc = calculate_new_market_cap(opening_mc, post_tax_standard_buy)
        mc_increase = new_mc - opening_mc
        buy_value_at_close = (post_tax_standard_buy * final_mc) / opening_mc
        all_buy_values_at_close.append(buy_value_at_close)

        if buy_number <= 10 or buy_number % 10 == 0:
            simulation_data.append({
                "buy_number": buy_number,
                "pre_tax_buy": standard_buy_size,
                "post_tax_buy": post_tax_standard_buy,
                "openingMC": opening_mc,
                "closingMC": new_mc,
                "mcIncrease": mc_increase,
                "buyValueAtClose": buy_value_at_close,
            })

        current_mc = new_mc
        buy_number += 1

        if current_mc >= final_mc:
            break

    if not user_buy_included:
        user_buy_value_at_close = (
            user_post_tax_buy * final_mc) / min(user_buy_mc_value, final_mc)
        all_buy_values_at_close.append(user_buy_value_at_close)

    total_sum_value = sum(all_buy_values_at_close)
    user_rewards_percentage = (user_buy_value_at_close / total_sum_value) * 100

    for item in simulation_data:
        item["totalSumValue"] = total_sum_value
        item["rewardsPercentage"] = (
            item["buyValueAtClose"] / total_sum_value) * 100

    return total_sum_value, simulation_data, user_buy_value_at_close, user_rewards_percentage

# Function to calculate rewards


def calculate_rewards(
    user_bet_amount: float,
    user_buy_mc: float,
    team1_final_mc: float,
    team2_final_mc: float,
    winning_team_id: int
) -> Dict:
    winning_team_final_mc = team1_final_mc if winning_team_id == 1 else team2_final_mc
    user_tax_paid = user_bet_amount * TAX_RATE  # Calculate tax paid

    total_sum_value, simulation_data, user_buy_value_at_close, user_rewards_percentage = simulate_market_cap_growth(
        final_mc=winning_team_final_mc,
        user_bet_amount=user_bet_amount,
        user_buy_mc=user_buy_mc
    )

    team1_available_liquidity = availableliquidity(team1_final_mc)
    team2_available_liquidity = availableliquidity(team2_final_mc)

    losing_team_liquidity = team2_available_liquidity if winning_team_id == 1 else team1_available_liquidity

    # Calculate the percentage value in dollars
    percentage_value_in_dollars = (
        user_rewards_percentage / 100) * losing_team_liquidity

    user_post_tax_bet = user_bet_amount * BET_POOL_PERCENTAGE

    # Calculate Dollar Value Increase (Profit)
    dollar_increase = percentage_value_in_dollars - user_post_tax_bet

    # Add these values to the simulation data per row
    for row in simulation_data:
        row["PercentageValueInDollars"] = percentage_value_in_dollars
        row["DollarIncrease"] = dollar_increase

    # Return all values including percentage-based reward and profit increase
    return {
        "taxPaid": user_tax_paid,
        "userPostTaxBet": user_post_tax_bet,
        "userBuyValueAtClose": user_buy_value_at_close,
        "userRewardsPercentage": user_rewards_percentage,
        "totalSumValue": total_sum_value,
        "shareOfLosingTeamLiquidity": percentage_value_in_dollars,  # ✅ Value in dollars
        "estimatedSSBReward": user_post_tax_bet + percentage_value_in_dollars,
        "dollarIncrease": dollar_increase,  # ✅ Profit in dollars
        "simulationData": simulation_data
    }


# Simulated users
users = [
    {"name": "User 1", "bet_amount": 100, "buy_mc": 10, "team1_multiplier": 1.5,
        "team2_multiplier": 2.0, "winning_team": "Team 1"},
    {"name": "User 2", "bet_amount": 100, "buy_mc": 15, "team1_multiplier": 2.0,
        "team2_multiplier": 1.8, "winning_team": "Team 2"},
]

# List to store all results
all_results = []

# Loop through each user and calculate rewards
for user in users:
    result = calculate_rewards(
        # Access bet_amount from the user dictionary
        user_bet_amount=user["bet_amount"],
        # Access buy_mc from the user dictionary
        user_buy_mc=user["buy_mc"],
        # Access team1_multiplier from the user dictionary
        team1_multiplier=user["team1_multiplier"],
        # Access team2_multiplier from the user dictionary
        team2_multiplier=user["team2_multiplier"],
        # Access winning_team from the user dictionary
        winning_team=user["winning_team"]
    )

    # Add user info and the new values to the result
    for row in result["simulationData"]:
        row["User"] = user["name"]  # Add the user name to each row
        all_results.append(row)

if __name__ == "__main__":
  # Convert to Pandas DataFrame
  df = pd.DataFrame(all_results)

  # Display the first few rows
  print(df.head())

  # Save to a CSV file
  df.to_csv("good results.csv", index=False)

  print("Simulation results saved to good results.csv")
