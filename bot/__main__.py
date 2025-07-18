import logging.config
import sys

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand

from api.config.logging import LOGGING
from bot.config.bot import RUNNING_MODE, TELEGRAM_API_TOKEN, RunningMode
from bot.handlers import router
from aiogram.client.default import DefaultBotProperties
logging.config.dictConfig(LOGGING)
logger = logging.getLogger(__name__)

bot = Bot(token=TELEGRAM_API_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dispatcher = Dispatcher()
dispatcher.include_router(router)  # вся логика в router

async def set_bot_commands() -> None:
    await bot.set_my_commands(
        [
            BotCommand(command="/start", description="Запустить бота"),
            BotCommand(command="/register", description="Регистрация"),
            BotCommand(command="/subjects", description="Список предметов"),
            BotCommand(command="/history", description="История прохождений"),
        ]
    )

@dispatcher.startup()
async def on_startup() -> None:
    await set_bot_commands()

def run_polling() -> None:
    dispatcher.run_polling(bot)

def run_webhook() -> None:
    raise NotImplementedError("Webhook mode not supported yet.")

if __name__ == "__main__":
    if RUNNING_MODE == RunningMode.LONG_POLLING:
        run_polling()
    elif RUNNING_MODE == RunningMode.WEBHOOK:
        run_webhook()
    else:
        logger.error("Unknown running mode")
        sys.exit(1)
