from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()


class Settings(BaseModel):
    app_name: str = "SmartFeed Automation"
    mongo_uri: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    mongo_db_name: str = os.getenv("MONGO_DB_NAME", "smartfeed")
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "")
    youtube_api_key: str = os.getenv("YOUTUBE_API_KEY", "")
    instagram_token: str = os.getenv("INSTAGRAM_TOKEN", "")
    output_dir: str = os.getenv("OUTPUT_DIR", "generated")
    font_path: str = os.getenv("FONT_PATH", "../assets/fonts/Montserrat-Regular.ttf")
    ffmpeg_binary: str = os.getenv("FFMPEG_BINARY", "ffmpeg")


settings = Settings()
