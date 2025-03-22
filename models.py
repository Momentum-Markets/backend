from pydantic import BaseModel
from typing import Optional, List

MARKET_CAP = 100000

class Team(BaseModel):
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    market_cap: int = MARKET_CAP

class Event(BaseModel):
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    event_time: Optional[str] = None
    event_location: Optional[str] = None
    teams: List[Team]
    status: Optional[str] = "pending"  # pending, active, settled, finalized
    is_active: bool = True
    is_resolved: bool = False
    is_paused: bool = False
    total_bet_amount: int = 0
    winner_index: Optional[int] = None

class FinalizeEvent(BaseModel):
    winner_index: int

class Bet(BaseModel):
    event_id: int
    team_id: int
    amount: int
    tax_amount: int
    net_bet_amount: int
    market_cap_at_bet: int

class User(BaseModel):
    address: str
    balance: int
    bets: List[Bet]

class UserReward(BaseModel):
    address: str
    reward: int
