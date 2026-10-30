import datetime
from collections import deque
import logging
import os

from dotenv import load_dotenv
from telegram import Update, Message
from telegram.ext import (
    Application,
    ContextTypes,
    MessageHandler,
    filters
)

import llm_manager

# Load environment variables from .env
load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
MESSAGE_HISTORY_SIZE = int(os.getenv("MESSAGE_HISTORY_SIZE", 10))

class TelegramBot:
    """
    Handles Telegram bot initialization, incoming group messages
    and outgoing group messages.
    """

    # Using collections.deque completely avoids Queue await issues 
    # and automatically drops old items when maxlen is reached.
    current_chat = deque(maxlen=MESSAGE_HISTORY_SIZE)

    def __init__(self, token: str):
        """
        Initializes the Telegram bot.

        Args:
            token (str): Telegram Bot API token.

        Raises:
            ValueError: If the provided token is empty.
        """
        if not token:
            raise ValueError("Telegram bot token is not configured.")

        self.application = (
            Application.builder()
            .token(token)
            .build()
        )

        self._register_handlers()

    def _register_handlers(self):
        """
        Registers Telegram message handlers.

        Only text messages sent in groups or supergroups
        are handled. Messages sent by bots are ignored.
        """
        self.application.add_handler(
            MessageHandler(
                filters.ChatType.GROUPS
                & filters.TEXT
                & ~filters.COMMAND,
                self._handle_group_message
            )
        )

    async def _handle_group_message(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):
        """
        Processes incoming group messages.

        Extracts message information and forwards it to
        on_group_message().

        Args:
            update (Update): Telegram update containing the message.
            context (ContextTypes.DEFAULT_TYPE): Telegram context.
        """
        message = update.effective_message
        user = update.effective_user
        chat = update.effective_chat

        if not message or not user or not chat:
            return

        # Ignore messages sent by bots.
        if user.is_bot:
            return

        # FIXED: Added await here so the handler runs
        await self.on_group_message(
            message=message.text,
            chat_id=chat.id,
            user_id=user.id
        )

    async def on_group_message(
        self,
        message: str,
        chat_id: int,
        user_id: int
    ) -> None:
        """
        Called whenever a non-bot user sends a text message
        to a group where this bot is present.

        Args:
            message (str): Received message text.
            chat_id (int): Telegram group chat ID.
            user_id (int): Telegram user ID of the sender.
        """
        # FIXED: Appending to deque doesn't need checks or await statements
        TelegramBot.current_chat.append({
            "role": "user",
            "content": message
        })

        logging.info(
            "Group message | Chat: %s | User: %s | Message: %s",
            chat_id,
            user_id,
            message
        )

        # FIXED: Removed 'await' because ask_direct_llm returns a normal string
        response = llm_manager.ask_msglist_llm(TelegramBot.current_chat)
        
        sent = await self.send_group_message(response, chat_id)
        print(f"____________________\nSent message: \n{sent.text} \nto chat_id: {chat_id}\n--------------------\n")
        print(f"____________________\nCurrent Chat History: \n{TelegramBot.current_chat}\n--------------------\n")

    async def send_group_message(
        self,
        message: str,
        chat_id: int
    ) -> Message:
        """
        Sends a text message to a specified Telegram group.

        Args:
            message (str): Message text to send.
            chat_id (int): Telegram group chat ID.

        Returns:
            Message: Telegram message object returned by the API.
        """
        # FIXED: Appending to deque doesn't need checks or await statements
        
        if message[0:4] != "/ooc":
            TelegramBot.current_chat.append({
                "role": "assistant",
                "content": message
            })
        else:
            print(f"Out of context message: {message}")
        
        return await self.application.bot.send_message(
            chat_id=chat_id,
            text=message
        )

    def run(self):
        """
        Starts the bot using long polling.
        """
        logging.info("Telegram bot is starting...")
        self.application.run_polling()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s"
    )

    bot = TelegramBot(TOKEN)
    bot.run()