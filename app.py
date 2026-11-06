from logger import Logger
from chat_history import ChatHistory

def main() -> None:
    try:
        import dotenv
        from telegram_io import TelegramIO
        from chat_history import ChatHistory

        ChatHistory.reset()

        Logger.system("Starting the application...")

        dotenv.load_dotenv(".env")
        telegram_bot_token = dotenv.get_key(
            ".env",
            "TELEGRAM_BOT_TOKEN",
        )

        if not telegram_bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN is not configured.")

        TelegramIO(token=telegram_bot_token).run()
    except KeyboardInterrupt:
        Logger.info("Shutdown requested. The application stopped gracefully.")
    except Exception as error:
        Logger.critical(
            f"Application startup or runtime failed: {error}",
            exc_info=True,
        )
    finally:
        ChatHistory.saveHistory()
        Logger.info("Chat history saved to chat_log")
        Logger.info("Application shutdown complete.")


if __name__ == "__main__":
    main()
