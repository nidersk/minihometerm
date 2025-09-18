from .models import Counter


class CounterService:
    def __init__(self):
        self.counter = Counter()

    def increment_and_get(self) -> int:
        return self.counter.inc()
