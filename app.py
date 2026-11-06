import streamlit as st
import interface
import dotenv
from telegram_io import TelegramIO
import input_handler
from logger import Logger

Logger.system("Starting the application...")


dotenv.load_dotenv(".env")
TELEGRAM_BOT_TOKEN = dotenv.get_key(".env", "TELEGRAM_BOT_TOKEN")
IH = input_handler.InputHandler()


global telegram
telegram = TelegramIO(
    token=TELEGRAM_BOT_TOKEN
)

telegram.run()
# interface.run()

 
