
import input_handler
from logger import Logger


from telegram import Update, Message
from telegram.ext import (
    Application,
    ContextTypes,
    MessageHandler,
    filters
)


class TelegramIO:
    """
    Minimal Telegram input/output interface.

    Receives group messages from non-bot users and
    forwards them to a user-defined callback.
    """

    def __init__(self, token: str):
        """
        Initialize Telegram connection.

        Args:
            token: Telegram bot API token.
        """

        if not token:
            raise ValueError("Telegram token cannot be empty.")


        self.application = (
            Application.builder()
            .token(token)
            .build()
        )

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
    ):
        """
        Handle incoming group messages.

        Args:
            message: Message text.
            chat_id: Telegram chat ID.
            user_id: Telegram user ID.
        """
        IH = input_handler.InputHandler()
        output = IH.handle_input(message)
        if output is not None:
            await self.send_message(output, chat_id)

        

    async def send_message(self, message: str, chat_id: int):
        """
        Send a message to a Telegram chat.

        Args:
            message: Message text.
            chat_id: Destination Telegram chat ID.
        """

        return await self.application.bot.send_message(
            chat_id=chat_id,
            text=message
        )

    def run(self):
        """Start Telegram polling."""

        Logger.info("Telegram I/O started.")
        self.application.run_polling()
