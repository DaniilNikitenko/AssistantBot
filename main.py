import telebot
from telebot import types
import requests
import json
from currency_converter import CurrencyConverter
from dotenv import load_dotenv
import os

load_dotenv()

bot = telebot.TeleBot(os.getenv("TELEGRAM_BOT_TOKEN"))
api = os.getenv("API")
currency = CurrencyConverter()

amount = 0


@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(message.chat.id, "Привет выбери действие: ")
    markup = types.ReplyKeyboardMarkup()
    bth1 = types.KeyboardButton("Узнать погоду")
    markup.row(bth1)
    bth2 = types.KeyboardButton("Конвертация валют")
    markup.row(bth2)
    bot.send_message(message.chat.id, "Привет выбери действие: ", reply_markup=markup)


@bot.message_handler(func=lambda message: message.text == "Узнать погоду")
def ask_city(message):
    bot.send_message(message.chat.id, "Введите название города:")
    bot.register_next_step_handler(message, get_weather)


def get_weather(message):
    city = message.text.strip().lower()
    res = requests.get(
        f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api}&units=metric&lang=ru"
    )
    if res.status_code == 200:
        data = json.loads(res.text)
        temp = data["main"]["temp"]
        temp_feels_like = data["main"]["feels_like"]
        weather = data["weather"][0]["description"]
        icon_code = data["weather"][0]["icon"]
        icon_url = f"https://openweathermap.org/img/wn/{icon_code}@2x.png"
        bot.reply_to(
            message,
            f"Сейчас на улице {weather.capitalize()}\n Температура {temp}, ощущается как {temp_feels_like}",
        )
        bot.send_photo(message.chat.id, icon_url, caption="Пасмурно")
    else:
        bot.reply_to(message, "Введите корректное название города")


@bot.message_handler(func=lambda message: message.text == "Конвертация валют")
def ask_sum(message):
    bot.send_message(message.chat.id, "Введите сумму")
    bot.register_next_step_handler(message, summa)


def summa(message):
    global amount
    try:
        amount = int(message.text.strip())
    except ValueError:
        bot.send_message(message.chat.id, "Введите корректную сумму")
        bot.register_next_step_handler(message, summa)
        return
    if amount > 0:
        text_markup = types.InlineKeyboardMarkup(row_width=2)
        bth1 = types.InlineKeyboardButton("USD/EUR", callback_data="USD/EUR")
        bth2 = types.InlineKeyboardButton("EUR/USD", callback_data="EUR/USD")
        bth3 = types.InlineKeyboardButton("USD/BTH", callback_data="USD/BTH")
        bth4 = types.InlineKeyboardButton("GBR/USD", callback_data="GBR/USD")
        bth5 = types.InlineKeyboardButton("Другое значения", callback_data="else")
        text_markup.add(bth1, bth2, bth3, bth4, bth5)
    else:
        bot.send_message(message.chat.id, "Введите корректное число")
        bot.register_next_step_handler(message, summa)
    bot.reply_to(message, "Укажите пару валют", reply_markup=text_markup)


@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    values = call.data.split("/")
    res = currency.convert(amount, values[0], values[1])
    bot.send_message(
        call.message.chat.id, f"{amount} {values[0]} это {round(res,3)} {values[1]}"
    )


bot.polling(none_stop=True)
