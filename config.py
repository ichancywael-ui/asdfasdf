from dotenv import load_dotenv
import os

load_dotenv()

TOKEN = os.getenv("TOKEN")
ADMIN_ID = list(map(int, os.getenv("ADMIN_ID").split(",")))
GROUP_ID =  os.getenv("GROUP_ID")
API_KEY = os.getenv("API_KEY")
GSM = os.getenv("GSM")
BASE_URL = os.getenv("BASE_URL")

ICHANCY_USERNAME = os.getenv("ICHANCY_USERNAME")
ICHANCY_PASSWORD = os.getenv("ICHANCY_PASSWORD")
PARENT_ID = os.getenv("PARENT_ID")
ICHANCY_API = os.getenv("ICHANCY_API")
GROUP_ICHANCY_CHANNEL_ID = os.getenv("GROUP_ICHANCY_CHANNEL_ID")

LOGIN_URL_API = os.getenv("LOGIN_URL_API")
REGISTER_URL_API = os.getenv("REGISTER_URL_API")
SEARCH_URL_API = os.getenv("SEARCH_URL_API")
DEPOSIT_URL_API = os.getenv("DEPOSIT_URL_API")
WITHDRAW_URL_API = os.getenv("WITHDRAW_URL_API")

TOKKEN = os.getenv("TOKKEN")


