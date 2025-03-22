from models import Event, Team

NZDD_CONTRACT_ADDRESS = "0x0649fFCb4C950ce964eeBA6574FDfDE0478FDA5F"

EVENTS = [
  Event(
    id=1,
    name="UFC Fight Night - Leon Edwards vs. Sean Brady",
    event_time="2025-03-23 09:00:00",
    event_location="02 Arena, London, UK",
    teams=[
      Team(id=1, name="Leon Edwards"),
      Team(id=2, name="Sean Brady")
    ],
  ),
  Event(
    id=2,
    name="UFC Fight Night - Jan Blachowicz vs. Carlos Ulberg",
    event_time="2025-03-23 09:00:00",
    event_location="02 Arena, London, UK",
    teams=[
      Team(id=1, name="Jan Blachowicz"),
      Team(id=2, name="Carlos Ulberg")
    ],
  )
]