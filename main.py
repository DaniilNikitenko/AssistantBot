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

from deep_translator import GoogleTranslator
from database import create_db, save_user_data, get_user_city, get_user_coordinates

create_db()  # создаём БД при запуске
user_temp_data = {}  # временное хранилище

# Загрузка переменных окружения из .env
load_dotenv()

# Инициализация бота с токеном
bot = telebot.TeleBot(os.getenv("TELEGRAM_BOT_TOKEN"))
api = os.getenv("API")  # API-ключ для погоды
api_convert = os.getenv("API_CONVERT")  # API-ключ для конвертации валют
api_nasa = os.getenv("NASA_API")
amount = 0  # Сумма для конвертации


# Обработчик команды /start и /help — выводит главное меню


@bot.message_handler(commands=["start"])
def handle_location(message):
    if message.location:
        user_id = message.from_user.id
        latitude = message.location.latitude
        longitude = message.location.longitude
        user_temp_data[user_id] = {"latitude": latitude, "longitude": longitude}
        bot.send_message(
            message.chat.id,
            "📍 Геолокация была загружена успешна.\n Теперь введите название вашего города",
        )
        bot.register_next_step_handler(message, get_city)
    else:
        bot.send_message(message.chat.id, "📍 Пожалуйста, отправьте свою геолокацию.")
        bot.register_next_step_handler(message, handle_location)


def get_city(message):
    user_id = message.from_user.id
    city_name = message.text.strip()

    if user_id in user_temp_data:
        latitude = user_temp_data[user_id]["latitude"]
        longitude = user_temp_data[user_id]["longitude"]

        save_user_data(user_id, latitude, longitude, city_name)

        bot.send_message(
            message.chat.id,
            f"✅ Данные сохранены:\nГород: {city_name}\nШирота: {latitude}\nДолгота: {longitude}\n Для того чтобы открыть меня введи\n /help",
        )
        user_temp_data.pop(user_id)
    else:
        bot.send_message(message.chat.id, "Ошибка: не найдена информация о геолокации.")


@bot.message_handler(commands=["settings"])
def setting_menu(message):
    markup_settings = types.InlineKeyboardMarkup(row_width=2)
    btn_city_change = types.InlineKeyboardButton(
        "Изменить город", callback_data="change_city"
    )
    btn_geo_change = types.InlineKeyboardButton(
        "Изменить геолокацию", callback_data="change_geo"
    )
    markup_settings.add(btn_city_change, btn_geo_change)

    bot.send_message(message.chat.id, "Настройки:", reply_markup=markup_settings)


@bot.callback_query_handler(
    func=lambda call: call.data in ["change_city", "change_geo"]
)
def handle_settings_change(call):
    if call.data == "change_city":
        bot.send_message(call.message.chat.id, "Введите новый город")
        bot.register_next_step_handler(call.message, change_city_handler)
    elif call.data == "change_geo":
        bot.send_message(call.message.chat.id, "📍 Отправьте новую геолокацию:")
        bot.register_next_step_handler(call.message, update_location_only)


def update_location_only(message):
    if message.location:
        user_id = message.from_user.id
        latitude = message.location.latitude
        longitude = message.location.longitude

        update_user_location(user_id, latitude, longitude)

        bot.send_message(message.chat.id, "✅ Геолокация обновлена.")
    else:
        bot.send_message(
            message.chat.id, "❗ Пожалуйста, отправьте корректную геолокацию."
        )
        bot.register_next_step_handler(message, update_location_only)


def change_city_handler(message):
    user_id = message.from_user.id
    city = message.text.strip()

    # Сначала получаем текущие координаты из БД
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT latitude, longitude FROM users WHERE user_id = ?", (user_id,)
    )
    result = cursor.fetchone()
    conn.close()

    if result:
        latitude, longitude = result
        save_user_data(user_id, latitude, longitude, city)
        bot.send_message(message.chat.id, f"✅ Город обновлён на: {city}")
    else:
        bot.send_message(
            message.chat.id, "⚠️ Сначала отправьте геолокацию через /start."
        )


# 👇 Если нужно только обновить координаты, без изменения города
def update_user_location(user_id, latitude, longitude):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE users
        SET latitude = ?, longitude = ?
        WHERE user_id = ?
    """,
        (latitude, longitude, user_id),
    )
    conn.commit()
    conn.close()


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
        f"{message.from_user.first_name}! 👋\nЧто тебя интересует?\n Для открытие настроек введи /settings",
        reply_markup=markup,
    )


# Обработка выбора из главного меню
@bot.callback_query_handler(
    func=lambda call: call.data in ["weather", "convert", "astra"]
)
def handle_main_menu(call):
    bot.answer_callback_query(call.id)
    if call.data == "weather":
        get_weather(call)
    elif call.data == "convert":
        bot.send_message(call.message.chat.id, "💰 Введите сумму для конвертации:")
        bot.register_next_step_handler(call.message, summa)
    elif call.data == "astra":
        astro_menu(call.message)


# Получение геолокации пользователя и отображение астрономического меню
def astro_menu(message):
    markup_astro = types.InlineKeyboardMarkup(row_width=1)
    bth_moon_phase = types.InlineKeyboardButton(
        "🌑 Узнать фазу луны", callback_data="phase_moon"
    )
    bth_sunrise_time = types.InlineKeyboardButton(
        "🌝 🌛 Время восхода и заката Солнца", callback_data="sunrise"
    )
    bth_astra_picture = types.InlineKeyboardButton(
        "🌄 Астрономическая картинка дня", callback_data="astra_picture"
    )
    bth_position_planet = types.InlineKeyboardButton(
        "🌎 Какие планеты видно сегодня", callback_data="astra_position_planet"
    )

    markup_astro.add(
        bth_moon_phase, bth_sunrise_time, bth_astra_picture, bth_position_planet
    )
    bot.send_message(message.chat.id, "Выберите действие: ", reply_markup=markup_astro)


# Обработка выбора в астрономическом меню
@bot.callback_query_handler(
    func=lambda call: call.data
    in ["phase_moon", "sunrise", "astra_picture", "astra_position_planet"]
)
def handle_astro_menu(call):
    user_id = call.message.chat.id
    lat, lon = get_user_coordinates(user_id)
    bot.answer_callback_query(call.id)
    if call.data == "phase_moon":
        print(lat, lon)
        phase = get_moon_phase(lat, lon)
        print(phase)
        bot.send_message(
            call.message.chat.id, f"Фаза Луны для вашего местоположения: {phase}"
        )
    elif call.data == "sunrise":
        sunrise, sunset = calculate_sun_times(lat, lon)
        bot.send_message(
            call.message.chat.id, f"🌅 Восход: {sunrise} | 🌇 Закат: {sunset}"
        )
    elif call.data == "astra_picture":
        send_apod(call.message)
    elif call.data == "astra_position_planet":
        bot.send_message(call.message.chat.id, get_visible_planets(lat, lon))


# Функции (не используются напрямую, возможно остались отладки)


# Функция определения фазы луны по координатам
def get_moon_phase(lat, lon):
    observer = ephem.Observer()
    observer.lat = str(lat)
    observer.lon = str(lon)
    observer.date = ephem.now()

    moon = ephem.Moon(observer)
    phase = moon.phase

    # Вычисляем возраст Луны в днях
    prev_new_moon = ephem.previous_new_moon(observer.date)
    age = observer.date - prev_new_moon  # Возраст Луны в днях

    # Определяем фазу по возрасту
    if age < 1.5:
        return "🌑 Новолуние"
    elif age < 6.5:
        return "🌒 Растущий серп"
    elif age < 13.5:
        return "🌓 Первая четверть"
    elif age < 15.5:
        return "🌔 Почти полнолуние"
    elif age < 21:
        return "🌖 Убывающая Луна"
    elif age < 27:
        return "🌘 Последняя четверть"
    else:
        return "🌑 Новолуние"


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


import ephem
from datetime import datetime


def get_visible_planets(lat, lon):
    observer = ephem.Observer()
    observer.lat = str(lat)
    observer.lon = str(lon)
    observer.date = datetime.now(timezone.utc)

    planets = {
        "Меркурий": ephem.Mercury(observer),
        "Венера": ephem.Venus(observer),
        "Марс": ephem.Mars(observer),
        "Юпитер": ephem.Jupiter(observer),
        "Сатурн": ephem.Saturn(observer),
        "Уран": ephem.Uranus(observer),
        "Нептун": ephem.Neptune(observer),
    }

    visible = []
    for name, planet in planets.items():
        planet.compute(observer)
        alt_deg = planet.alt * 180 / ephem.pi  # перевод в градусы
        if alt_deg > 0:
            visible.append(f"{name} (высота: {alt_deg:.1f}°)")

    if visible:
        msg = "🔭 Сейчас можно наблюдать следующие планеты:\n"
        msg += "\n".join(f"• {p}" for p in visible)
    else:
        msg = "❌ Сейчас ни одна планета не видна над горизонтом."

    return msg


def send_apod(message):
    response = requests.get(f"https://api.nasa.gov/planetary/apod?api_key={api_nasa}")
    MAX_CAPTION_LENGTH = 1024
    if response.status_code == 200:
        data = response.json()
        title = data.get("title", "Без названия")
        explanation = data.get("explanation", "Нет описания.")
        translate_explanation = translate_to_russian(explanation)
        caption_text = f"🔭 {title}\n\n{translate_explanation}"
        media_url = data.get("url", "")
        media_type = data.get("media_type", "image")

        if media_type == "image" and len(caption_text) <= MAX_CAPTION_LENGTH:
            bot.send_photo(message.chat.id, media_url, caption=f"🔭 {caption_text}")
        else:
            bot.send_message(
                message.chat.id,
                f"{title}\n\n{translate_explanation}\n📺 Видео: {media_url}",
            )
    else:
        bot.send_message(message.chat.id, "🚫 Не удалось получить изображение от NASA.")


def translate_to_russian(text):
    new_text = GoogleTranslator(source="auto", target="ru").translate(text)
    return new_text


# Получение погоды по названию города
def get_weather(call):
    user_id = call.message.chat.id
    print(user_id)
    city = get_user_city(user_id)
    print(city)
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
            call.message.chat.id,
            f"{emoji} Погода в {city.title()}:\n"
            f" {description}\n"
            f"🌡 Температура: {temp}°C (ощущается как {feels}°C)\n"
            f"🕒 Время: {time}",
        )
    else:
        bot.send_message(call.message.chat.id, "⚠️ Город не найден. Попробуй ещё раз.")


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


import sqlite3


@bot.message_handler(commands=["show_users"])
def show_users(message):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    cursor.execute("SELECT user_id, city, latitude, longitude FROM users")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        bot.send_message(message.chat.id, "📭 В базе данных нет пользователей.")
        return

    text = "👤 Пользователи в базе данных:\n\n"
    for row in rows:
        uid, city, lat, lon = row
        text += f"ID: {uid}\nГород: {city}\nШирота: {lat}\nДолгота: {lon}\n\n"

    # Если слишком длинный текст, разбей его на части
    for i in range(0, len(text), 4000):  # телега ограничивает ~4096 символов
        bot.send_message(message.chat.id, text[i : i + 4000])


# Запуск бота в режиме ожидания сообщений
bot.polling(non_stop=True)
