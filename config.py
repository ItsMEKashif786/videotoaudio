import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
MAX_FILE_SIZE = 50 * 1024 * 1024
DEFAULT_FORMAT = "mp3"
AUDIO_QUALITY = "192"
TEMP_DIR = "/tmp"
