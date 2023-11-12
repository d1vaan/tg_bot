import os
from datetime import date
import asyncio
import logging
import whisper
from aiogram import Bot, Dispatcher, types
import config
import speech_def


# Задаем токен вашего бота. Замените 'YOUR_BOT_TOKEN' на актуальный токен.
bot = Bot(token = config.token)

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
    user_id = message.from_user.id
    await message.answer(
        'Здравствуйте! Этот бот поможет Вам оценить уровень вашей дикции и прозношения.\n'
        f'Ваш уникальный id: {user_id}.\n'
        'Пожалуйста, запомните или запишите Ваш код. В дальнейшем он Вам потребуется\n'
        'для взаимодействия с вашим врачом.\n\n'
        'Для начала записи нажмите или напишите /recording'
    )

# Хэндлер для команды /recording
@dp.message_handler(commands=["recording"])
async def cmd_recording(message: types.Message):
    '''
    Функция реагирует на команду /recording и запускает
    функцию "send_next_word"
    '''
    await send_next_word(message.from_user.id)

# Функция для отправки следующего слова
async def send_next_word(user_id):
    '''
    Функция начинается после её вызова функцией cmd_recording и
    запускает поочерёдную отправку сообщений со словами/фразами, которые
    необходимо записать в голосовом пользователю.
    '''

    # получаем значение ключа "user_id" из словаря user_state, если пустое
    # то присуждаем переменное значение ключ-значение- {"current_word_index": 0}
    state = user_state.get(user_id, {"current_word_index": 0})
    
    # если значение ключа "current_word_index" в слова state меньше, чем
    # кол-во слов в списке word_list, то:
    if state["current_word_index"] < len(word_list):

        # переменная word равна слову из списка word_list, индекс которого
        # равен значению ключа "current_word_index" из словаря state
        word = word_list[state["current_word_index"]]

        # присуждаем ключу "awaiting_voice_response" значение True
        state["awaiting_voice_response"] = True

        # присуждаем ключу "current_word" значение word
        state["current_word"] = word
        await bot.send_message(user_id, f"Текст: {word}\nПожалуйста, отправьте голосовое сообщение с произношением этого текста.")
    else:
        await bot.send_message(user_id, "Вы прошли все слова. Спасибо за участие!")

    # записываем в словарь состояния пользователя его текущее состояние
    # из переменной-словаря state, ключ - id пользователя
    user_state[user_id] = state

# Функция для обработки голосового сообщения
@dp.message_handler(content_types=types.ContentType.VOICE)
async def handle_voice_message(message: types.Message):
    '''
    Функция активирована по-умолчанию и реагирует, если пользователь
    отправил голосовое сообщение. Если пользователем была запущена
    команда /recording, то бот записывает полученное голосовое в 
    созданную им директорию
    '''
    user_id = message.from_user.id
    state = user_state.get(user_id, {})
    
    if state.get("awaiting_voice_response", False):
        state["awaiting_voice_response"] = False
        word = state["current_word"]

        user_folder = f'/home/ubuntu/project/users_audio/{user_id}'
        os.makedirs(user_folder, exist_ok=True, mode=0o777)
        
        message_date = message.date
        date_folder = f'/home/ubuntu/project/users_audio/{user_id}/{message_date.year}-{message_date.month}-{message_date.day}'
        os.makedirs(date_folder, exist_ok=True, mode=0o777)

        voice_file_id = message.voice.file_id
        file_info = await bot.get_file(voice_file_id)
        voice_file = await bot.download_file(file_info.file_path)
        audio_path = os.path.join(date_folder, f"{word}.ogg")
        
        with open(audio_path, 'wb') as audio_file:
            audio_file.write(voice_file.read())

        state["current_word_index"] = state.get("current_word_index", 0) + 1
        user_state[user_id] = state


        await send_next_word(user_id)
    else:
        await bot.send_message(user_id, "Вы отправили голосовое сообщение, но оно не ожидалось. Пожалуйста, нажмите 'Далее' для продолжения.")

# Запуск поллинга (двунаправленной связи) новых апдейтов
async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())# tg_bot
