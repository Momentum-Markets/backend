from models import Event, Team

NZDD_CONTRACT_ADDRESS = "0x0649fFCb4C950ce964eeBA6574FDfDE0478FDA5F"

EVENTS = [
  Event(
    id=1,
    name="UFC Fight Night - Leon Edwards vs. Sean Brady",
    event_time="2025-03-23 09:00:00",
    event_location="02 Arena, London, UK",
    teams=[
      Team(name="Leon Edwards", contract_address=NZDD_CONTRACT_ADDRESS),
      Team(name="Sean Brady", contract_address=NZDD_CONTRACT_ADDRESS)
    ]
  ),
  Event(
    id=2,
    name="UFC Fight Night - Jan Blachowicz vs. Carlos Ulberg",
    event_time="2025-03-23 09:00:00",
    event_location="02 Arena, London, UK",
    teams=[
      Team(name="Jan Blachowicz", contract_address=NZDD_CONTRACT_ADDRESS),
      Team(name="Carlos Ulberg", contract_address=NZDD_CONTRACT_ADDRESS)
    ]
  )
]