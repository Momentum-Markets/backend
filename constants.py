from models import Event, Team

NZDD_CONTRACT_ADDRESS = "0x0649fFCb4C950ce964eeBA6574FDfDE0478FDA5F"

EVENTS = [
  Event(
    id=1,
    name="UFC: Edwards vs. Brady",
    tag="hot",
    category="MMA",
    event_time="March 23, 2025",
    teams=[
      Team(id=1, name="Leon Edwards"),
      Team(id=2, name="Sean Brady")
    ],
  ),
  Event(
    id=2,
    name="Premier League: Arsenal vs. Liverpool",
    tag="trending",
    category="Football",
    event_time="April 5, 2025",
    teams=[
      Team(id=1, name="Arsenal"),
      Team(id=2, name="Liverpool")
    ],
  ),
  Event(
    id=3,
    name="NFL: Chiefs vs. 49ers",
    tag="hot",
    category="American Football",
    event_time="Today, 8:00 PM",
    teams=[
      Team(id=1, name="Kansas City Chiefs"),
      Team(id=2, name="San Francisco 49ers")
    ],
  ),
  Event(
    id=4,
    name="NFL: Cowboys vs. Eagles",
    tag="trending",
    category="American Football",
    event_time="Tomorrow, 4:30 PM",
    teams=[
      Team(id=1, name="Dallas Cowboys"),
      Team(id=2, name="Philadelphia Eagles")
    ],
  ),
  Event(
    id=5,
    name="UFC Fight Night: Adesanya vs. Pereira",
    tag="trending",
    category="MMA",
    event_time="May 18, 2025",
    teams=[
      Team(id=1, name="Israel Adesanya"),
      Team(id=2, name="Alex Pereira")
    ],
  ),
  Event(
    id=6,
    name="Champions League Final",
    tag="hot",
    category="Football",
    event_time="May 31, 2025",
    teams=[
      Team(id=1, name="Real Madrid"),
      Team(id=2, name="Manchester City")
    ],
  ),
  Event(
    id=7,
    name="NFL: Ravens vs. Bengals",
    category="American Football",
    event_time="Saturday, 1:00 PM",
    teams=[
      Team(id=1, name="Baltimore Ravens"),
      Team(id=2, name="Cincinnati Bengals")
    ],
  ),
  Event(
    id=8,
    name="NFL: Bills vs. Dolphins",
    category="American Football",
    event_time="Sunday, 4:25 PM",
    teams=[
      Team(id=1, name="Buffalo Bills"),
      Team(id=2, name="Miami Dolphins")
    ],
  ),
  Event(
    id=9,
    name="La Liga: Barcelona vs. Real Madrid",
    category="Football",
    event_time="April 10, 2025",
    teams=[
      Team(id=1, name="Barcelona"),
      Team(id=2, name="Real Madrid")
    ],
  ),
  Event(
    id=10,
    name="Serie A: Juventus vs. Inter Milan",
    category="Football",
    event_time="April 17, 2025",
    teams=[
      Team(id=1, name="Juventus"),
      Team(id=2, name="Inter Milan")
    ],
  ),
  Event(
    id=11,
    name="Bellator 300: McKee vs. Pitbull",
    category="MMA",
    event_time="April 22, 2025",
    teams=[
      Team(id=1, name="AJ McKee"),
      Team(id=2, name="Patricio Pitbull")
    ],
  ),
  Event(
    id=12,
    name="UFC 301: O'Malley vs. Yan",
    category="MMA",
    event_time="June 15, 2025",
    teams=[
      Team(id=1, name="Sean O'Malley"),
      Team(id=2, name="Petr Yan")
    ],
  ),
]