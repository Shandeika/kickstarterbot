import logging
import random

from aiogram import types, Dispatcher, Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from bot.db.models import Tag, User


router = Router()


@router.message(Command("start"))
async def cmd_start(message: types.Message):
    bot_user = await message.bot.me()
    await message.answer(
        "Привет! Я помогу тебе легко начинать диалог с начального сообщения.\n"
        f"Просто сконфигурируй сообщение или вообще созать свои и начинать диалог с простого "
        f"использования inline конструкции @{bot_user.username} start"
    )

    session = message.bot.get_db_session()
    user = session.query(User).filter(User.user_id == message.from_user.id).first()
    if user is None:
        user = User(user_id=message.from_user.id, username=message.from_user.username)
        session.add(user)
        session.commit()


@router.inline_query()
async def inline_cmd(query: types.InlineQuery):
    logging.debug("Start inline query")
    session = query.bot.get_db_session()
    logging.debug("Got db session")
    user = session.query(User).filter(User.user_id == query.from_user.id).first()
    tags = user.tags
    if query.query in [tag.tag for tag in tags]:
        tags = [tag for tag in tags if query.query in tag.tag]
    elif query.query == "":
        tags = user.tags
    else:
        tags = [tag for tag in tags if query.query in tag.text]
    logging.debug("Got tags")

    results = list()
    logging.debug(f"Got results list ({len(results)})")
    for tag in tags:
        logging.debug(f"Got tag ({tag})")
        results.append(
            types.InlineQueryResultArticle(
                id=str(tag.id),
                title=tag.tag,
                description=f"{tag.text[:47]}...",
                input_message_content=types.InputTextMessageContent(
                    message_text=tag.text
                ),
            )
        )
    logging.debug(f"Got results final ({results})")
    await query.bot.answer_inline_query(query.id, results=results[:50])
    logging.debug("End inline query")
    session.close()


class AddTagStates(StatesGroup):
    start = State()
    WaitingForTag = State()
    WaitingForText = State()


@router.message(Command("add_tag"))
async def add_tag(message: types.Message, state: FSMContext):
    await message.answer("Введите тег")
    await state.set_state(AddTagStates.WaitingForTag)


@router.message(AddTagStates.WaitingForTag, F.text)
async def process_tag(message: types.Message, state: FSMContext):
    tag = message.text
    long_text = len(tag) > 30
    with_space = " " in tag
    if long_text or with_space:
        await message.answer(
            text=(
                "Тег не соответствует требованиям, попробуйте другой\n"
                "Требования:\n"
                "1. Тег не должен содержать пробелы\n"
                "2. Тег не должен быть длиннее 30 символов"
            ),
            parse_mode="markdown",
        )
    else:
        await state.update_data(tag=tag)
        await message.answer("Введите текст")
        await state.set_state(AddTagStates.WaitingForText)


@router.message(AddTagStates.WaitingForText, F.text)
async def process_text(message: types.Message, state: FSMContext):
    text = message.text
    long_text = len(text) > 2000
    if long_text:
        await message.answer(
            text=(
                "Текст не соответствует требованиям, попробуйте другой\n"
                "Требования:\n"
                "1. Текст не должен быть длиннее 2000 символов"
            ),
            parse_mode="markdown",
        )
    else:
        data = await state.get_data()
        tag = data.get("tag")
        await message.answer(f"Тег: <code>{tag}</code>\n\nТекст:\n<code>{text}</code>")
        session = message.bot.get_db_session()
        user = session.query(User).filter(User.user_id == message.from_user.id).first()
        if user is None:
            user = User(
                user_id=message.from_user.id, username=message.from_user.username
            )
            session.add(user)
        session.add(Tag(tag=tag, text=text, user=user))
        session.commit()
        session.close()
        await message.answer("Тег успешно добавлен в базу данных")

        await state.clear()


class RemoveTagStates(StatesGroup):
    WaitingForTag = State()
    WaitingForApproval = State()


@router.message(Command("remove_tag"))
async def remove_tag(message: types.Message, state: FSMContext):
    await message.answer("Введите тег")
    await state.set_state(RemoveTagStates.WaitingForTag)


@router.message(RemoveTagStates.WaitingForTag, F.text)
async def process_tag(message: types.Message, state: FSMContext):
    tag = message.text
    session = message.bot.get_db_session()
    tags = session.query(Tag).filter(Tag.user_id == message.from_user.id).all()
    if tag not in [tag.tag for tag in tags]:
        await message.answer("Такого тега нет в базе данных")
    else:
        await state.update_data(tag=tag)
        await message.answer("Подтвердите удаление")
        first_number = random.randint(1, 10)
        second_number = random.randint(1, 10)
        await state.update_data(
            first_number=first_number,
            second_number=second_number,
            sum=first_number + second_number,
        )
        await message.answer(
            f"Напишите правильный ответ: {first_number} + {second_number} = ?"
        )
        await state.set_state(RemoveTagStates.WaitingForApproval)


@router.message(RemoveTagStates.WaitingForApproval, F.text)
async def process_approval(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if message.text == str(data.get("sum")):
        session = message.bot.get_db_session()
        session.query(Tag).filter(Tag.tag == data.get("tag")).delete()
        session.commit()
        session.close()
        await message.answer("Тег успешно удален из базы данных")
        await state.clear()
    else:
        await message.answer("Неправильный ответ")


class EditTagStates(StatesGroup):
    WaitingForTag = State()
    WaitingForText = State()


@router.message(Command("edit_tag"))
async def edit_tag(message: types.Message, state: FSMContext):
    await message.answer("Введите тег")
    await state.set_state(EditTagStates.WaitingForTag)


@router.message(EditTagStates.WaitingForTag, F.text)
async def process_tag(message: types.Message, state: FSMContext):
    tag = message.text
    session = message.bot.get_db_session()
    tags = session.query(Tag).filter(Tag.user_id == message.from_user.id).all()
    if tag not in [tag.tag for tag in tags]:
        await message.answer("Такого тега нет в базе данных")
    else:
        tag = (
            session.query(Tag)
            .filter(Tag.tag == tag and Tag.user_id == message.from_user.id)
            .first()
        )
        await state.update_data(tag=tag.tag)
        await message.answer(f"Текущий текст:\n<code>{tag.text}</code>")
        await message.answer("Введите новый текст")
        await state.set_state(EditTagStates.WaitingForText)
    session.close()


@router.message(EditTagStates.WaitingForText, F.text)
async def process_text(message: types.Message, state: FSMContext):
    text = message.text
    data = await state.get_data()
    tag = data.get("tag")
    session = message.bot.get_db_session()
    tag = (
        session.query(Tag)
        .filter(Tag.tag == tag and Tag.user_id == message.from_user.id)
        .first()
    )
    tag.text = text
    session.commit()
    session.close()
    await message.answer("Тег успешно изменен в базе данных")
    await state.clear()


def register_commands(dp: Dispatcher):
    dp.include_router(router=router)
