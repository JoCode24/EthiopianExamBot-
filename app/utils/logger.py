import logging
import os


def setup_logger():
    os.makedirs("logs", exist_ok=True)

    handlers = [logging.StreamHandler()]

    try:
        fh = logging.FileHandler("logs/bot.log", encoding="utf-8")
        handlers.append(fh)
    except Exception:
        pass

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers
    )

    logger = logging.getLogger("EthiopianExamBot")
    logger.info("Logger initialized successfully.")
    return logger


logger = setup_logger()