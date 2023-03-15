import logging
import asyncio
import sqlite3
import openai_secret_manager
import openai
import pyttsx3

import aiogram.utils.markdown as md
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.types.message import ContentType
from aiogram.types import Message
from aiogram.types import ParseMode
from aiogram.types.inline_keyboard import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher import FSMContext
from aiogram import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage


logging.basicConfig(level=logging.INFO)

bot = Bot(token='6143545907:AAHDe_zuGWlhUsHy_KKBIc6vItpXKiWZCbs')
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Setup OpenAI credentials
secrets = openai_secret_manager.get_secret("openai")
openai.api_key = secrets["api_key"]

# Setup Text-to-speech engine
engine = pyttsx3.init()

# Клавиатура стартового меню
start_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
start_keyboard.add(KeyboardButton("Приемная комиссия"),
                    KeyboardButton("О факультетах"),
                    KeyboardButton("VR-Обзор вуза"),
                    KeyboardButton("Поступление"),
                    KeyboardButton("Часто задаваемые вопросы"))

# Обработчик команды /start
@dp.message_handler(commands=['start'])
async def process_start_command(message: types.Message):
    await message.reply("Привет! Я чат-бот для абитуриентов. Выбери пункт меню:", reply_markup=start_keyboard)

# Клавиатура меню факультетов
faculties_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
faculties_keyboard.add(KeyboardButton("АФ"),
                       KeyboardButton("АДФ"),
                       KeyboardButton("ФЭУ"),
                       KeyboardButton("ФИЭиГХ"),
                       KeyboardButton("ФСЭиПСТ"),
                       KeyboardButton("СФ"),
                       KeyboardButton("Вернуться в стартовое меню"))

# Словарь с информацией о факультетах
faculties_info = {
    'АФ': 'Краткая информация о факультете АФ',
    'АДФ': 'Краткая информация о факультете АДФ',
    'ФЭУ': 'Краткая информация о факультете ФЭУ',
    'ФИЭиГХ': 'Краткая информация о факультете ФИЭиГХ',
    'ФСЭиПСТ': 'Краткая информация о факультете ФСЭиПСТ',
    'СФ': 'Краткая информация о факультете СФ'
}

directions = [
    {"name": "Направление 1", "score": 80},
    {"name": "Направление 2", "score": 85},
    {"name": "Направление 3", "score": 90},
]

# Подключение к базе данных
conn = sqlite3.connect('рейтинг.db')

# Создание таблицы, если ее нет
conn.execute('''CREATE TABLE IF NOT EXISTS abiturients
             (ID INTEGER PRIMARY KEY AUTOINCREMENT,
             NAME TEXT NOT NULL,
             SCORE INTEGER NOT NULL,
             DIRECTION TEXT NOT NULL);''')


# Определение состояний FSM
class Form(StatesGroup):
    direction = State()
    score = State()

# Обработчик нажатия на кнопки факультетов
@dp.message_handler(lambda message: message.text in faculties_info.keys(), content_types=["text"])
async def faculty_info_handler(message: Message):
    faculty_name = message.text
    info_text = faculties_info[faculty_name]
    await message.answer(info_text)

# Клавиатура меню поступления
entrance_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
entrance_keyboard.add(KeyboardButton("Проверить свои шансы на поступление"),
                       KeyboardButton("Подать документы"),
                       KeyboardButton("Рейтинговая таблица"),
                       KeyboardButton("Вернуться в стартовое меню"))

#Обработчик кнопки шансов
@dp.message_handler(text="Проверить свои шансы на поступление")
async def faq_handler(message: Message):
    await message.reply("Выберете свой факультет:", reply_markup=faculties_rate_keyboard)

# Создаем клавиатуру с кнопками направлений
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(*[types.KeyboardButton(direction) for direction in
                   ['Прикладная математика', 'Прикладная механика', 'Теплоэнергетика и теплотехника']])

    await message.answer("Выберите направление", reply_markup=keyboard)

    # Сохраняем выбранное направление в объекте состояния
    await state.set_state("get_scores")
    await state.update_data(direction=message.text)


# Обработчик текстовых сообщений
@dp.message_handler(state="get_scores")
async def get_scores(message: types.Message, state: FSMContext):
    # Получаем количество баллов из сообщения пользователя
    try:
        scores = int(message.text)
    except ValueError:
        await message.answer("Некорректный ввод, пожалуйста, введите число")
        return

    # Получаем выбранное направление из объекта состояния
    async with state.proxy() as data:
        direction = data["direction"]

    # Получаем количество баллов из базы данных
    conn = sqlite3.connect('directions.db')
    cursor = conn.cursor()
    cursor.execute(f"SELECT scores FROM directions WHERE direction = '{direction}'")
    db_scores = cursor.fetchone()[0]
    conn.close()

    # Проверяем, хватает ли баллов для поступления
    if scores >= db_scores:
        await message.answer("У Вас хорошие шансы поступить")
    else:
        await message.answer("К сожалению, Ваша сумма меньше прошлогоднего проходного балла")

    # Сбрасываем объект состояния
    await state.finish()

#Обработчик кнопки подачи
@dp.message_handler(text="Подать документы")
async def faq_handler(message: Message):
    await message.reply("Отправьте ваше заявление:")

# Обработчик кнопки "Рейтинговая таблица"
@dp.callback_query_handler(lambda c: c.data == 'Рейтинговая таблица')
async def show_rating(call: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(InlineKeyboardButton(text="1", callback_data='direction_1'),
                 InlineKeyboardButton(text="2", callback_data='direction_2'),
                 InlineKeyboardButton(text="3", callback_data='direction_3'))
    await bot.send_message(call.from_user.id, "Выберите направление:", reply_markup=keyboard)


# Обработчик выбора направления
@dp.callback_query_handler(lambda c: c.data.startswith('direction'))
async def select_direction(call: types.CallbackQuery, state: FSMContext):
    direction = int(call.data.split('_')[1])
    await state.update_data(direction=direction)
    await Form.score.set()
    await bot.send_message(call.from_user.id, "Введите количество баллов:")


# Обработчик ввода баллов
@dp.message_handler(state=Form.score)
async def process_score(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['score'] = int(message.text)
    direction = data['direction']
    score = data['score']

    # Ищем место пользователя в рейтинге
    rows = conn.execute(f"SELECT COUNT(*) FROM abiturients WHERE SCORE > {score} AND DIRECTION = '{direction}'")
    rank = rows.fetchone()[0] + 1

    # Добавляем пользователя в базу данных
    conn.execute(
        f"INSERT INTO abiturients (NAME, SCORE, DIRECTION) VALUES ('{message.from_user.full_name}', {score}, '{direction}')")
    conn.commit()

    # Отправляем сообщение с результатом
    await bot.send_message(message.from_user.id, f"Ваше место в рейтинге для направления {direction}: {rank}")

    # Сбрасываем состояние FSM
    await state.finish()

# Клавиатура меню факультетов для баллов
faculties_rate_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
faculties_rate_keyboard.add(KeyboardButton("1. АФ"),
                       KeyboardButton("2. АДФ"),
                       KeyboardButton("3. ФЭУ"),
                       KeyboardButton("4. ФИЭиГХ"),
                       KeyboardButton("5. ФСЭиПСТ"),
                       KeyboardButton("6. СФ"),
                       KeyboardButton("Назад"),
                       KeyboardButton("Вернуться в стартовое меню"))

# Клавиатура направлений АФ
af_rate_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
af_rate_keyboard.add(KeyboardButton("Направление 1"),
                       KeyboardButton("Направление 2"),
                       KeyboardButton("Направление 3"),
                       KeyboardButton("Назад"),
                       KeyboardButton("Вернуться в стартовое меню"))

# Обработчик направления АФ
@dp.message_handler(text="1. АФ")
async def faq_handler(message: Message):
    await message.reply("Выберете направление:", reply_markup=af_rate_keyboard)

#Обработчик кнопки назад
@dp.message_handler(text="Назад")
async def faq_handler(message: Message):
    await message.reply("Вы вернулись назад", reply_markup=entrance_keyboard)

# Обработчик кнопки "Вернуться в стартовое меню"
@dp.message_handler(text="Вернуться в стартовое меню")
async def back_to_main_menu(message: types.Message):
    await message.reply("Вы вернулись назад, выберете пункт меню:", reply_markup=start_keyboard)

# Обработчик нажатий на кнопки стартового меню
@dp.message_handler(content_types=ContentType.TEXT)
async def process_menu_buttons(message: types.Message):
    if message.text == "Приемная комиссия":
        # Отправить главную информацию о приемной комиссии
        await message.answer("Ответственный секретарь приёмной комиссии\nНаталья Викторовна ОРЛОВА\n\n"
                        "Заместитель ответственного секретаря приёмной комиссии\nЭльвира Вячеславовна ТКАЧЕНКО\n\n"
                        "Сотрудники приёмной комиссии:\nНаталья Анатольевна КРОХИНА\nАнна Игоревна НАЛЁТОВА\n"
                        "Ксения Анатольевна ПЕДЬКО\nСветлана Петровна ШИШОВА\n\n"
                        "Время работы:\n| ПН-ЧТ | 09:00 – 18:00 |\n| ПТ | 09:00 – 17:00 |\n| перерыв | 13:00 – 14:00 |\n\n"
                        "Контакты:\n+7 (812) 316-20-26\n+7 (812) 316-11-23\n+7 (812) 575-94-53 (Целевой прием)\n"
                        "prc@spbgasu.ru\nvk.com/spbgasu_priemnaia\nt.me/spbgasupriemnaia")
    elif message.text == "О факультетах":
        # Открыть меню факультетов
        await message.answer("Выбери факультет:", reply_markup=faculties_keyboard)
    elif message.text == "VR-Обзор вуза":
        # Отправить ссылку на обзор
        await message.answer("Ссылка на VR-Обзор вуза: https://panorama.spbgasu.ru/")
    elif message.text == "Поступление":
        # Открыть меню поступления
        await message.answer("Выбери действие:", reply_markup=entrance_keyboard)
    elif message.text == "Часто задаваемые вопросы":
        # Открыть F.A.Q
        await message.answer("F.A.Q")

# Обработчик на F.A.Q
@dp.message_handler(text="5. Часто задаваемые вопросы")
async def faq_handler(message: Message):
    # Function to generate AI response
    async def generate_ai_response(query):
        response = openai.Completion.create(
            engine="davinci",
            prompt=query,
            temperature=0.7,
            max_tokens=1024,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )
        return response.choices[0].text.strip()

    # Function to generate speech from text
    def generate_speech(text):
        engine.say(text)
        engine.runAndWait()

    # Handler for start and help commands
    @dp.message_handler(commands=['start', 'help'])
    async def send_welcome(message: types.Message):
        await message.reply(
            "Привет! Я голосовой помощник СПБГАСУ. Напиши мне свой вопрос, и я постараюсь на него ответить. Если нужно, я могу произнести ответ вслух.")

    # Handler for text messages
    @dp.message_handler(content_types=['text'])
    async def handle_text_message(message: types.Message):
        text = message.text.lower()

        if 'формы обучения' in text:
            response = "СПБГАСУ предлагает следующие формы обучения: \n\n- очная \n- очно-заочная \n- заочная"
            await message.reply(response)
            generate_speech(response)

        elif 'даты проведения вступительных испытаний' in text:
            response = "Даты проведения вступительных испытаний можно узнать на официальном сайте СПБГАСУ в разделе 'Абитуриенту' или связавшись со службой приёмной комиссии университета."
            await message.reply(response)
            generate_speech(response)

        else:
            response = await generate_ai_response(text)
            await message.reply(response)
            generate_speech(response)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(dp.start_polling())
