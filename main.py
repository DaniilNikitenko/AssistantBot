import telebot
from telebot import types
from datetime import datetime
import requests
import json
from dotenv import load_dotenv
import os

load_dotenv()

bot = telebot.TeleBot(os.getenv("TELEGRAM_BOT_TOKEN"))
api = os.getenv("API")
api_convert = os.getenv("API_CONVERT")
amount = 0


@bot.message_handler(commands=["start"])
def start(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_weather = types.InlineKeyboardButton("🌤 Узнать погоду", callback_data="weather")
    btn_convert = types.InlineKeyboardButton(
        "💱 Конвертация валют", callback_data="convert"
    )
    markup.add(btn_weather, btn_convert)
    bot.send_message(
        message.chat.id,
        f"Привет, {message.from_user.first_name}! 👋\nЧто тебя интересует?",
        reply_markup=markup,
    )


@bot.callback_query_handler(func=lambda call: call.data in ["weather", "convert"])
def handle_main_menu(call):
    if call.data == "weather":
        bot.send_message(call.message.chat.id, "🌆 Введите название города:")
        bot.register_next_step_handler(call.message, get_weather)
    elif call.data == "convert":
        bot.send_message(call.message.chat.id, "💰 Введите сумму для конвертации:")
        bot.register_next_step_handler(call.message, summa)


def get_weather(message):
    city = message.text.strip().lower()
    res = requests.get(
        f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api}&units=metric&lang=ru"
    )
    if res.status_code == 200:
        data = res.json()
        temp = data["main"]["temp"]
        feels = data["main"]["feels_like"]
        weather = data["weather"][0]["description"].capitalize()
        icon_code = data["weather"][0]["icon"]
        icon_url = f"https://openweathermap.org/img/wn/{icon_code}@2x.png"
        time = datetime.now().strftime("%H:%M")

        bot.send_message(
            message.chat.id,
            f"📍 Погода в {city.title()}:\n"
            f"🌡 {weather}\n"
            f"Температура: {temp}°C (ощущается как {feels}°C)\n"
            f"🕒 Время: {time}",
        )
        bot.send_photo(message.chat.id, icon_url)
    else:
        bot.send_message(message.chat.id, "⚠️ Город не найден. Попробуй ещё раз.")


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


bot.polling(none_stop=True)
