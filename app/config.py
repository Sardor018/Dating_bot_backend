from dotenv import load_dotenv
import os       

load_dotenv()

TELEGRAM_TOKEN, WEB_APP_URL = os.getenv("TELEGRAM_TOKEN"), os.getenv("WEB_APP_URL")  # Новые переменные окружения