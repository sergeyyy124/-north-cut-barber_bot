import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, DB_PATH
from database import init_db
from handlers import router


async def main() -> None:
    """Создаёт базу данных, подключает роутер обработчиков и запускает бота."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Инициализируем таблицы SQLite перед приёмом сообщений
    init_db(DB_PATH)

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    logging.info("Бот барбершопа NORTH CUT запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
