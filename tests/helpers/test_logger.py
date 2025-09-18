from minihometerm.helpers.logger import get_logger


def test_logger_creation():
    logger = get_logger("test_logger")
    logger.info("hello")
    assert logger.name == "test_logger"
