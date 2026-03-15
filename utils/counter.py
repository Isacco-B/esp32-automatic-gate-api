import json
import time

from utils.timezone import now_unix

COUNTER_FILE = "/counters.json"
COUNTER_24H_FILE = "/counters_24h.json"

RESET_HOUR = 23
RESET_MINUTE = 59


class CommandCounter:

    def __init__(self):
        self.total_counters = {
            "gate": 0,
            "partial_gate": 0,
            "small_gate": 0,
            "garage_light": 0,
        }

        self.counters_24h = {
            "gate": 0,
            "partial_gate": 0,
            "small_gate": 0,
            "garage_light": 0,
        }

        self.last_auto_reset_date = None

        self.load_counters()

    def _today_str(self) -> str:
        t = time.localtime(now_unix())
        return f"{t[0]:04d}-{t[1]:02d}-{t[2]:02d}"

    def _should_reset(self) -> bool:
        """Return True if it's 23:59 and the automatic daily reset hasn't run yet today."""
        t = time.localtime(now_unix())
        at_reset_time = t[3] == RESET_HOUR and t[4] >= RESET_MINUTE
        return at_reset_time and self._today_str() != self.last_auto_reset_date

    def _reset_24h_if_needed(self) -> None:
        if self._should_reset():
            for command in self.counters_24h:
                self.counters_24h[command] = 0
            self.last_auto_reset_date = self._today_str()
            self.save_counters()
            print(f"Daily counters reset at {self.last_auto_reset_date}")

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
                    self.counters_24h = data.get("counts", self.counters_24h)
                    self.last_auto_reset_date = data.get("last_auto_reset_date", None)
        except (OSError, ValueError):
            print("No existing 24h counters")

        self._reset_24h_if_needed()

    def save_counters(self) -> None:
        """Save counters to persistent storage."""
        try:
            with open(COUNTER_FILE, "w") as f:
                json.dump(self.total_counters, f)

            with open(COUNTER_24H_FILE, "w") as f:
                json.dump(
                    {
                        "counts": self.counters_24h,
                        "last_auto_reset_date": self.last_auto_reset_date,
                    },
                    f,
                )
        except Exception as e:
            print(f"Error saving counters: {e}")

    def increment(self, command: str) -> None:
        """Increment counter for a command."""
        if command not in self.total_counters:
            print(f"Unknown command: {command}")
            return

        self._reset_24h_if_needed()

        self.total_counters[command] += 1
        self.counters_24h[command] = self.counters_24h.get(command, 0) + 1
        self.save_counters()

    def get_statistics(self) -> dict:
        """Get formatted statistics."""
        self._reset_24h_if_needed()

        return {
            "last_24_hours": {
                "cancello": self.counters_24h.get("gate", 0),
                "pedonabile": self.counters_24h.get("partial_gate", 0),
                "cancellino": self.counters_24h.get("small_gate", 0),
                "luce_garage": self.counters_24h.get("garage_light", 0),
            },
            "totale": {
                "cancello": self.total_counters.get("gate", 0),
                "pedonabile": self.total_counters.get("partial_gate", 0),
                "cancellino": self.total_counters.get("small_gate", 0),
                "luce_garage": self.total_counters.get("garage_light", 0),
            },
        }

    def reset_counters(self, counter_type: str = "all") -> None:
        """Reset counters by type: '24h', 'total', or 'all'."""
        if counter_type in ["all", "24h"]:
            for command in self.counters_24h:
                self.counters_24h[command] = 0

        if counter_type in ["all", "total"]:
            for command in self.total_counters:
                self.total_counters[command] = 0

        self.save_counters()
        print(f"Counters reset: {counter_type}")


counter = CommandCounter()
