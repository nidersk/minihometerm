from minihometerm.core.services import CounterService


def test_counter_service_increments():
    svc = CounterService()
    assert svc.increment_and_get() == 1
    assert svc.increment_and_get() == 2
