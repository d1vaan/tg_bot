import os
from datetime import date
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher.filters import Text
import config

# Задаем токен вашего бота. Замените 'YOUR_BOT_TOKEN' на актуальный токен.
bot = Bot(token=config.token)

# Создаем диспетчер для обработки команд и сообщений бота
dp = Dispatcher(bot)

# Создаем словарь для отслеживания состояния пользователя
user_state = {}

# Список слов, которые бот будет предлагать пользователю
word_list = config.words


# Хэндлер для команды /start
@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    '''
    Функция/команда реагирует на вызов команды /start в боте, при её вызове
    бот высылает приветственное сообщение и уведомляет о необходимости
    принять соглашение о персональных данных
    '''

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button_1 = types.KeyboardButton(text="Пользовательское соглашение")
    keyboard.add(button_1)

    user_id = message.from_user.id
    await message.answer(
        'Здравствуйте\! Этот бот предназначен для распознавания фонограмм,\n'
        'и поможет вам оценить уровень вашей дикции и произношения\.\n'
        f'Ваш уникальный id: {user_id} \n'
        'Пожалуйста, запомните или запишите Ваш код\. \n'
        'В дальнейшем он Вам потребуется для взаимодействия с вашим врачом\. \n\n'

        'Для дальнейшей работы с ботом вам необходимо ознакомиться с пользовательским соглашением\.',
        parse_mode="MarkdownV2",
        reply_markup=keyboard
    )


@dp.message_handler(Text(equals="Пользовательское соглашение"))
async def with_puree(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button_1 = types.KeyboardButton(text="Я ознакомился(-лась) с пользовательским соглашением.")
    keyboard.add(button_1)

    await message.reply(
        r'[пользовательского соглашения](https://docs.google.com/document/d/1lKXqAZj4xd_dm_fXI_e4W7OHQSWeigouvGX1LAk3i0M/edit?usp=sharing) ',
        parse_mode="MarkdownV2",
        reply_markup=keyboard)


@dp.message_handler(Text(equals="Я ознакомился(-лась) с пользовательским соглашением."))
async def start_recording(message: types.Message):
    user_id = message.from_user.id

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button_1 = types.KeyboardButton(text="Начать запись фонограмм.")
    keyboard.add(button_1)

    await message.answer(
        'Теперь вы можете начать запись фонограмм!',
        reply_markup=keyboard)


# Хэндлер для команды /recording
@dp.message_handler(Text(equals="Начать запись фонограмм."))
async def cmd_recording(message: types.Message):
    user_id = message.from_user.id

    # Проверим, существует ли пользователь в словаре user_state
    if user_id not in user_state:
        user_state[user_id] = {"current_word_index": 0, "session_number": 0, "session_status": "active"}

    session_status = user_state[user_id]["session_status"]

    if session_status == "active":
        user_state[user_id]["session_number"] += 1
        await send_next_word(user_id)
    elif session_status == "paused":
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        button_continue = types.KeyboardButton(text="Продолжить текущую сессию")
        button_new_session = types.KeyboardButton(text="Запустить новую сессию")
        keyboard.add(button_continue, button_new_session)
        await bot.send_message(user_id, "Сессия приостановлена. Выберите одну из опций:", reply_markup=keyboard)
    else:
        # Если сессия завершена, отправим сообщение об этом
        await bot.send_message(user_id, "Сессия завершена. Запустите новую сессию командой /recording.")


# Хэндлер для кнопок "Продолжить текущую сессию" и "Запустить новую сессию"
@dp.message_handler(Text(equals="Продолжить текущую сессию"))
async def continue_session(message: types.Message):
    user_id = message.from_user.id
    user_state[user_id]["session_status"] = "active"
    await send_next_word(user_id)


@dp.message_handler(Text(equals="Запустить новую сессию"))
async def new_session(message: types.Message):
    user_id = message.from_user.id
    user_state[user_id]["session_status"] = "active"
    user_state[user_id]["session_number"] += 1

    user_state[user_id]['current_word_index'] = 0
    
    await send_next_word(user_id)


# Хэндлер для остановки сессии
@dp.message_handler(Text(equals="Остановить запись фонограмм."))
async def stop_recording(message: types.Message):
    user_id = message.from_user.id

    # Проверяем существование пользователя в user_state
    if user_id not in user_state:
        await bot.send_message(user_id, "Ошибка: пользователь не найден в системе.")
        return

    user_state[user_id]["session_status"] = "paused"

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button_continue = types.KeyboardButton(text="Продолжить текущую сессию")
    button_new_session = types.KeyboardButton(text="Запустить новую сессию")
    keyboard.add(button_continue, button_new_session)

    await bot.send_message(user_id, 
        "Сессия приостановлена. Вы можете продолжить текущую сессию или запустить новую.",
        reply_markup=keyboard
        )



# Функция для отправки следующего слова
async def send_next_word(user_id):
    state = user_state.get(user_id, {"current_word_index": 0, "session_number": 1, "session_status": "active"})

    if state["current_word_index"] < len(word_list):
        word = word_list[state["current_word_index"]]
        session_number = state["session_number"]

        state["awaiting_voice_response"] = True
        state["current_word"] = word

        # Добавим кнопку "Остановить запись" вместе с кнопкой "Далее"
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        button_stop = types.KeyboardButton(text="Остановить запись фонограмм.")
        keyboard.add(button_stop)

        await bot.send_message(user_id, f"Текст: {word}\n"
                                        f"Пожалуйста, отправьте голосовое сообщение с произношением этого текста.",
                               reply_markup=keyboard)
    else:
        await bot.send_message(user_id, "Вы прошли все слова. Спасибо за участие!")

    user_state[user_id] = state


# Функция для обработки голосового сообщения
@dp.message_handler(content_types=types.ContentType.VOICE)
async def handle_voice_message(message: types.Message):
    user_id = message.from_user.id
    state = user_state.get(user_id, {})

    if state.get("awaiting_voice_response", False):
        state["awaiting_voice_response"] = False
        word = state["current_word"]
        session_number = state["session_number"]

        user_folder = f'/home/ubuntu/project/users_audio/{user_id}'
        os.makedirs(user_folder, exist_ok=True, mode=0o777)

        message_date = message.date
        date_folder = f'/home/ubuntu/project/users_audio/{user_id}/{message_date.year}-{message_date.month}-{message_date.day}'
        os.makedirs(date_folder, exist_ok=True, mode=0o777)

        voice_file_id = message.voice.file_id
        file_info = await bot.get_file(voice_file_id)
        voice_file = await bot.download_file(file_info.file_path)
        audio_path = os.path.join(date_folder, f"{word}_{session_number}.ogg")

        with open(audio_path, 'wb') as audio_file:
            audio_file.write(voice_file.read())

        state["current_word_index"] = state.get("current_word_index", 0) + 1
        user_state[user_id] = state

        await send_next_word(user_id)
    else:
        await bot.send_message(user_id,
                               "Вы отправили голосовое сообщение, но оно не ожидалось. Пожалуйста, нажмите 'Далее' для продолжения.")


# Запуск поллинга (двунаправленной связи) новых апдейтов
async def main():
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
