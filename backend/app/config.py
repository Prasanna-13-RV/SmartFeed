from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()


class Settings(BaseModel):
    app_name: str = "SmartFeed"
    output_dir: str = os.getenv("OUTPUT_DIR", "generated")
    base_url: str = os.getenv("BASE_URL", "http://localhost:8000")
    font_path: str = os.getenv("FONT_PATH", "../assets/fonts/Montserrat-Regular.ttf")
    ffmpeg_binary: str = os.getenv("FFMPEG_BINARY", "ffmpeg")
    yt_cookies_file: str = os.getenv("YT_COOKIES_FILE", "")
    yt_cookies_b64: str = os.getenv("YT_COOKIES_B64", "")
    cloudinary_cloud_name: str = os.getenv("CLOUDINARY_CLOUD_NAME", "")
    cloudinary_api_key: str = os.getenv("CLOUDINARY_API_KEY", "")
    cloudinary_api_secret: str = os.getenv("CLOUDINARY_API_SECRET", "")


settings = Settings()
