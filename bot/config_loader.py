from dataclasses import dataclass
from os import getenv

from dotenv import load_dotenv


@dataclass
class Bot:
    token: str


@dataclass
class DB:
    host: str
    db_name: str
    user: str
    password: str


@dataclass
class Config:
    bot: Bot
    db: DB


def load_config():
    load_dotenv()
    # TODO: Add some checks here?
    return Config(
        bot=Bot(token=getenv("BOT_TOKEN")),
        db=DB(
            host=getenv("DB_HOST"),
            db_name=getenv("DB_NAME"),
            user=getenv("DB_USER"),
            password=getenv("DB_PASS"),
        ),
    )
