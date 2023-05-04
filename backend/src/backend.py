from __future__ import annotations
from abc import ABC, abstractmethod
from config import config


class Challenge(ABC):
    """A Challenge that can be started or stopped."""

    id: str

    @staticmethod
    def fetch(challenge_id: str, team_id: str) -> Challenge:
        """Fetches the appropriate Challenge instance given challenge ID and team ID."""
        pass

    @abstractmethod
    def expiration(self) -> int | None:
        """Returns the expiration time of a challenge in seconds, or None if it isn't running."""
        pass

    @abstractmethod
    def start(self):
        """Starts a challenge, or renews it if it was already running."""
        pass

    @abstractmethod
    def start(self):
        """Starts a challenge, or renews it if it was already running."""
        pass

    @abstractmethod
    def stop(self):
        """Stops a challenge if it's running."""
        pass


class SharedChallenge(Challenge):
    """A challenge with one shared instance among all teams."""

    def __init__(self, id: str):
        """Constructs a SharedChallenge given the challenge ID.

        Do not call this constructor directly; use Challenge.fetch instead."""
        self.id = id


class PerTeamChallenge(Challenge):
    """A challenge that needs to spawn a unique instance per team."""

    team_id: str

    def __init__(self, id: str, team_id: str):
        """Constructs a PerTeamChallenge given the challenge ID and team ID.

        Do not call this constructor directly; use Challenge.fetch instead."""
        self.id = id
        self.team_id = team_id
