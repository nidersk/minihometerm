from dataclasses import dataclass


@dataclass
class Counter:
    value: int = 0

    def inc(self, by: int = 1) -> int:
        self.value += by
        return self.value
