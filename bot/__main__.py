import asyncio
import logging

import sqlalchemy
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeDefault
from sqlalchemy.orm import sessionmaker, Session

from bot.config_loader import Config, load_config
from bot.db.base import Base
from bot.handlers.commands import register_commands


async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="add_tag", description="Добавляет тэг с текстом"),
        BotCommand(command="remove_tag", description="Удаляет тэг"),
        BotCommand(command="edit_tag", description="Редактирует тэг"),
    ]
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
    pass


async def main():
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )

    config: Config = load_config()
    engine = sqlalchemy.create_engine(
        f"mysql+pymysql://{config.db.user}:{config.db.password}@{config.db.host}/{config.db.db_name}",
        echo=True,
    )

    Base.metadata.create_all(engine)

    bot = Bot(config.bot.token, parse_mode="HTML")

    def get_db_session() -> Session:
        session = sessionmaker(engine, expire_on_commit=False)
        return session()

    setattr(bot, "get_db_session", get_db_session)

    dp = Dispatcher(storage=MemoryStorage())

    register_commands(dp)

    await set_bot_commands(bot)

    try:
        await dp.start_polling(bot)
    finally:
        await dp.storage.close()
        await bot.session.close()


try:
    asyncio.run(main())
except (KeyboardInterrupt, SystemExit):
    logging.error("Bot stopped!")
