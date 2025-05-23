import logging
import os

log_level = int(os.getenv("LOG_LEVEL", "20"))
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s")
