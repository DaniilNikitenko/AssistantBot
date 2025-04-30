# Импорт библиотек
import telebot  # библиотека для создания Telegram-бота
from telebot import types  # для создания кнопок и других элементов интерфейса

from datetime import datetime, timezone  # для работы с датой и временем

import requests  # для HTTP-запросов (например, к API погоды и валют)
from dotenv import load_dotenv  # для загрузки переменных окружения из .env-файла

import os  # для работы с переменными окружения
from timezonefinder import (
    TimezoneFinder,
)  # для определения часового пояса по координатам
import ephem  # для астрономических вычислений (фаза луны, восход/закат)
import pytz  # для работы с часовыми поясами

# Загрузка переменных окружения из .env
load_dotenv()

# Инициализация бота с токеном
bot = telebot.TeleBot(os.getenv("TELEGRAM_BOT_TOKEN"))
api = os.getenv("API")  # API-ключ для погоды
api_convert = os.getenv("API_CONVERT")  # API-ключ для конвертации валют
amount = 0  # Сумма для конвертации

lat = 0  # Широта
lon = 0  # Долгота
city = None


# Обработчик команды /start и /help — выводит главное меню


@bot.message_handler(commands=["start"])
def get_location(message):
    if message.location:
        global lat, lon
        lat, lon = message.location.latitude, message.location.longitude
        bot.send_message(
            message.chat.id,
            "Геолокация была загружена успешна.\n Теперь введите название вашего города",
        )
        bot.register_next_step_handler(message, get_city)
        print(lat, lon)
    else:
        bot.send_message(message.chat.id, "Пожалуйста, отправьте свою геолокацию.")
        bot.register_next_step_handler(message, get_location)


def get_city(message):
    global city
    city = message.text.strip().lower()
    help_menu(message)


@bot.message_handler(commands=["help"])
def help_menu(message):
    markup = types.InlineKeyboardMarkup(row_width=2)  # создаем кнопки в 2 столбца
    btn_weather = types.InlineKeyboardButton("🌤 Узнать погоду", callback_data="weather")
    btn_convert = types.InlineKeyboardButton(
        "💱 Конвертация валют", callback_data="convert"
    )
    btn_astro = types.InlineKeyboardButton("🌌 Астраномия", callback_data="astra")
    markup.add(btn_weather, btn_convert, btn_astro)
    # Приветствие пользователя и показ меню
    bot.send_message(
        message.chat.id,
        f"{message.from_user.first_name}! 👋\nЧто тебя интересует?",
        reply_markup=markup,
    )


# Обработка выбора из главного меню
@bot.callback_query_handler(
    func=lambda call: call.data in ["weather", "convert", "astra"]
)
def handle_main_menu(call):
    bot.answer_callback_query(call.id)
    if call.data == "weather":
        get_weather(call.message)
    elif call.data == "convert":
        bot.send_message(call.message.chat.id, "💰 Введите сумму для конвертации:")
        bot.register_next_step_handler(call.message, summa)
    elif call.data == "astra":
        astro_menu(call.message)


# Получение геолокации пользователя и отображение астрономического меню
def astro_menu(message):
    markup_astro = types.InlineKeyboardMarkup(row_width=2)
    bth_moon_phase = types.InlineKeyboardButton(
        "Узнать фазу луны", callback_data="phase_moon"
    )
    bth_sunrise_time = types.InlineKeyboardButton(
        "Время восхода и заката Солнца", callback_data="sunrise"
    )

    markup_astro.add(bth_moon_phase, bth_sunrise_time)
    bot.send_message(message.chat.id, "Выберите действие: ", reply_markup=markup_astro)


# Обработка выбора в астрономическом меню
@bot.callback_query_handler(func=lambda call: call.data in ["phase_moon", "sunrise"])
def handle_astro_menu(call):
    bot.answer_callback_query(call.id)
    if call.data == "phase_moon":
        phase = get_moon_phase(lat, lon)
        bot.send_message(
            call.message.chat.id, f"Фаза Луны для вашего местоположения: {phase}"
        )
    elif call.data == "sunrise":
        sunrise, sunset = calculate_sun_times(lat, lon)
        bot.send_message(
            call.message.chat.id, f"🌅 Восход: {sunrise} | 🌇 Закат: {sunset}"
        )


# Функции (не используются напрямую, возможно остались отладки)
def get_phase_moon(message):
    phase = get_moon_phase(lat, lon)
    bot.send_message(message.chat.id, f"Фаза Луны для вашего местоположения:\n {phase}")


def get_sunrise_time(message):
    sunrise_time = sunrise_time(lat, lon)
    bot.send_message(
        message.chat.id, f"Восход: {sunrise_time[0]}, Закат: {sunrise_time[1]}"
    )


# Функция определения фазы луны по координатам
def get_moon_phase(lat, lon):
    global observer
    observer = ephem.Observer()
    observer.lat = str(lat)
    observer.lon = str(lon)
    moon = ephem.Moon(observer)
    phase = moon.phase  # значение от 0 до 100

    # Преобразуем числовую фазу в текстовое описание
    if phase < 1:
        return "🌑 Новолуние"
    elif 1 <= phase < 50:
        return "🌒 Растущий полумесяц"
    elif phase == 50:
        return "🌕 Полнолуние"
    elif 50 < phase < 99:
        return "🌖 Убывающая Луна"
    elif phase >= 99:
        return "🌘 Последний полумесяц"


# Расчёт времени восхода и заката солнца с учётом местного времени
def calculate_sun_times(lat, lon):
    tf = TimezoneFinder()
    tz_name = tf.timezone_at(lng=lon, lat=lat)
    if not tz_name:
        tz_name = "UTC"

    local_tz = pytz.timezone(tz_name)

    observer = ephem.Observer()
    observer.lat = str(lat)
    observer.lon = str(lon)
    observer.date = datetime.utcnow()

    sunrise_utc = (
        observer.next_rising(ephem.Sun()).datetime().replace(tzinfo=timezone.utc)
    )
    sunset_utc = (
        observer.next_setting(ephem.Sun()).datetime().replace(tzinfo=timezone.utc)
    )

    sunrise_local = sunrise_utc.astimezone(local_tz)
    sunset_local = sunset_utc.astimezone(local_tz)

    return sunrise_local.strftime("%H:%M"), sunset_local.strftime("%H:%M")


# Получение погоды по названию города
def get_weather(message):
    res = requests.get(
        f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api}&units=metric&lang=ru"
    )
    if res.status_code == 200:
        data = res.json()
        temp = data["main"]["temp"]
        feels = data["main"]["feels_like"]
        description = data["weather"][0]["description"].capitalize()
        icon_code = data["weather"][0]["icon"]  # для отображения эмодзи

        # Соответствие иконок погодным эмодзи
        emoji_map = {
            "01d": "☀️",
            "01n": "🌙",
            "02d": "🌤",
            "02n": "🌤",
            "03d": "☁️",
            "03n": "☁️",
            "04d": "☁️",
            "04n": "☁️",
            "09d": "🌧",
            "09n": "🌧",
            "10d": "🌦",
            "10n": "🌧",
            "11d": "🌩",
            "11n": "🌩",
            "13d": "❄️",
            "13n": "❄️",
            "50d": "🌫",
            "50n": "🌫",
        }

        emoji = emoji_map.get(icon_code)
        time = datetime.now().strftime("%H:%M")

        bot.send_message(
            message.chat.id,
            f"{emoji} Погода в {city.title()}:\n"
            f" {description}\n"
            f"🌡 Температура: {temp}°C (ощущается как {feels}°C)\n"
            f"🕒 Время: {time}",
        )
    else:
        bot.send_message(message.chat.id, "⚠️ Город не найден. Попробуй ещё раз.")


# Получение суммы для конвертации и выбор валютной пары
def summa(message):
    global amount
    try:
        amount = float(message.text.strip())
    except ValueError:
        bot.send_message(message.chat.id, "❌ Введите корректную сумму.")
        bot.register_next_step_handler(message, summa)
        return

    if amount > 0:
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("USD → EUR", callback_data="USD/EUR"),
            types.InlineKeyboardButton("EUR → USD", callback_data="EUR/USD"),
            types.InlineKeyboardButton("USD → RUB", callback_data="USD/RUB"),
            types.InlineKeyboardButton("EUR → RUB", callback_data="EUR/RUB"),
        )
        bot.send_message(
            message.chat.id, "💱 Выберите валютную пару:", reply_markup=markup
        )
    else:
        bot.send_message(message.chat.id, "❌ Сумма должна быть положительной.")
        bot.register_next_step_handler(message, summa)


# Выполнение запроса к API для конвертации валют
@bot.callback_query_handler(func=lambda call: "/" in call.data)
def callback_convert(call):
    base, target = call.data.split("/")
    url = f"https://v6.exchangerate-api.com/v6/{api_convert}/pair/{base}/{target}/{amount}"
    response = requests.get(url)
    data = response.json()

    if data["result"] == "success":
        result = round(data["conversion_result"], 2)
        bot.send_message(
            call.message.chat.id, f"💸 {amount} {base} = {result} {target}"
        )
    else:
        bot.send_message(call.message.chat.id, "⚠️ Не удалось получить курс валют.")


# Запуск бота в режиме ожидания сообщений
bot.polling(none_stop=True)
