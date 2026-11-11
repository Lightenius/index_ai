
import input_handler
from logger import Logger
from chat_history import ChatHistory

from telegram import Update, Message
from telegram.ext import (
    Application,
    ContextTypes,
    MessageHandler,
    filters
)

APOLOGY_MESSAGE = (
    "Üzgünüz, yanıt hazırlanırken bir hata oluştu. "
    "Lütfen daha sonra tekrar deneyin."
)


class TelegramIO:
    """
    Minimal Telegram input/output interface.

    Receives group messages from non-bot users and
    forwards them to a user-defined callback.
    """

    IH = None

    def __init__(self, token: str):
        """
        Initialize Telegram connection.

        Args:
            token: Telegram bot API token.
        """

        if not token:
            raise ValueError("Telegram token cannot be empty.")

        self.IH = input_handler.InputHandler()
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
        self.application.add_error_handler(self._handle_application_error)

    
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

        if not message.text:
            return

        ChatHistory.h.setdefault(chat.id, []).append(message.text)

        try:
            await self.send_message("Yanıt Hazırlanıyor...", chat_id=chat.id)
        except Exception as error:
            Logger.error(
                f"Could not send the response status to chat {chat.id}: {error}",
                exc_info=True,
            )

        try:
            await self.on_group_message(
                message=message.text,
                chat_id=chat.id,
                user_id=user.id
            )
        except Exception as error:
            Logger.error(
                f"Failed to process a message in chat {chat.id}: {error}",
                exc_info=True,
            )
            await self._send_apology(chat.id)


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
        try:
            if message.count(".doc") != 0: await self.send_message("Dokümanlar kontrol ediliyor.", chat_id=chat_id)
            output = await self.IH.handle_input(message, chat_id=chat_id)
            if not isinstance(output, str) or not output.strip():
                Logger.error(
                    f"Response generation returned no usable response for chat {chat_id}."
                )
                await self._send_apology(chat_id)
                return

            await self.send_message(output, chat_id, is_llm_message=True)
        except Exception as error:
            Logger.error(
                f"Failed to create or send a response to chat {chat_id}: {error}",
                exc_info=True,
            )
            await self._send_apology(chat_id)


    async def _send_apology(self, chat_id: int) -> None:
        try:
            await self.send_message(APOLOGY_MESSAGE, chat_id=chat_id)
        except Exception as error:
            Logger.error(
                f"Could not send the apology message to chat {chat_id}: {error}",
                exc_info=True,
            )


    async def _handle_application_error(
        self,
        update: object,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        error = context.error
        if error is None:
            Logger.error("Telegram reported an error without exception details.")
            return

        Logger.error(
            f"Unhandled Telegram application error: {error}",
            exc_info=(type(error), error, error.__traceback__),
        )

        

    async def send_message(self, message: str, chat_id: int, is_llm_message: bool = False):
        """
        Send a message to a Telegram chat.

        Args:
            message: Message text.
            chat_id: Destination Telegram chat ID.
        """
        if is_llm_message:
            ChatHistory.h[chat_id].append(message)

        return await self.application.bot.send_message(
            chat_id=chat_id,
            text=message
        )

    def run(self):
        """Start Telegram polling."""

        Logger.info("Telegram I/O started.")
        try:
            self.application.run_polling()
        except KeyboardInterrupt:
            # run_polling performs its own updater and application shutdown.
            Logger.info("Keyboard interrupt received. Telegram stopped gracefully.")
