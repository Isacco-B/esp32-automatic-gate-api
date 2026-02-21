import json

from utils.timezone import now_unix

COUNTER_FILE = "/counters.json"
COUNTER_24H_FILE = "/counters_24h.json"


class CommandCounter:
    """
    Simple counter for tracking command executions.
    Maintains 24-hour and total counters.
    """

    def __init__(self):
        """Initialize counters and load existing data."""
        self.total_counters = {
            "gate": 0,
            "partial_gate": 0,
            "small_gate": 0,
            "garage_light": 0,
        }

        self.counters_24h = {
            "gate": [],
            "partial_gate": [],
            "small_gate": [],
            "garage_light": [],
        }

        self.load_counters()

    def load_counters(self) -> None:
        """Load counters from persistent storage."""
        try:
            with open(COUNTER_FILE, "r") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    self.total_counters.update(data)
                print(f"Loaded counters: {self.total_counters}")
        except (OSError, ValueError):
            print("No existing counters, starting fresh")

        try:
            with open(COUNTER_24H_FILE, "r") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    self.counters_24h = data
                self.cleanup_24h_counters()
        except (OSError, ValueError):
            print("No existing 24h counters")

    def save_counters(self) -> None:
        """Save counters to persistent storage."""
        try:
            with open(COUNTER_FILE, "w") as f:
                json.dump(self.total_counters, f)

            with open(COUNTER_24H_FILE, "w") as f:
                json.dump(self.counters_24h, f)
        except Exception as e:
            print(f"Error saving counters: {e}")

    def increment(self, command: str) -> None:
        """
        Increment counter for a command.
        """
        if command not in self.total_counters:
            print(f"Unknown command: {command}")
            return

        self.total_counters[command] += 1

        current_time = now_unix()
        if command not in self.counters_24h:
            self.counters_24h[command] = []
        self.counters_24h[command].append(current_time)

        self.cleanup_24h_counters()

        self.save_counters()

    def cleanup_24h_counters(self) -> None:
        """Remove timestamps older than 24 hours."""
        current_time = now_unix()
        cutoff_time = current_time - (24 * 3600)

        for command in self.counters_24h:
            # Keep only timestamps from last 24 hours
            self.counters_24h[command] = [
                ts for ts in self.counters_24h[command] if ts > cutoff_time
            ]

    def get_24h_counts(self) -> dict:
        """
        Get command counts for last 24 hours.
        """
        self.cleanup_24h_counters()

        counts = {}
        for command, timestamps in self.counters_24h.items():
            counts[command] = len(timestamps)

        return counts

    def get_total_counts(self) -> dict:
        """
        Get total command counts.
        """
        return self.total_counters.copy()

    def get_statistics(self) -> dict:
        """
        Get formatted statistics.
        """
        counts_24h = self.get_24h_counts()

        return {
            "last_24_hours": {
                "cancello": counts_24h.get("gate", 0),
                "pedonabile": counts_24h.get("partial_gate", 0),
                "cancellino": counts_24h.get("small_gate", 0),
                "luce_garage": counts_24h.get("garage_light", 0),
            },
            "totale": {
                "cancello": self.total_counters.get("gate", 0),
                "pedonabile": self.total_counters.get("partial_gate", 0),
                "cancellino": self.total_counters.get("small_gate", 0),
                "luce_garage": self.total_counters.get("garage_light", 0),
            },
        }

    def reset_counters(self, counter_type: str = "all") -> None:
        """
        Reset counters.
        """
        if counter_type in ["all", "24h"]:
            for command in self.counters_24h:
                self.counters_24h[command] = []

        if counter_type in ["all", "total"]:
            for command in self.total_counters:
                self.total_counters[command] = 0

        self.save_counters()
        print(f"Counters reset: {counter_type}")


counter = CommandCounter()
