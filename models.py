from pydantic import BaseModel
from typing import Optional, List

class Team(BaseModel):
    name: str
    description: Optional[str] = None
    contract_address: Optional[str] = None


class Event(BaseModel):
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    event_time: Optional[str] = None
    event_location: Optional[str] = None
    teams: List[Team]
    status: Optional[str] = "pending"  # pending, active, settled
    winner_index: Optional[int] = None

class FinalizeEvent(BaseModel):
    winner_index: int
