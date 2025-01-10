import os
import pickle
import json
import telebot
import google.auth
import re
import io
import pandas as pd
from threading import Thread
from bot_instance import bot
from notifications import *
from auth import *
from context import *
from telebot import types
from pathlib import Path
from autodeadline import add_deadlines_to_dataframe_by_index
from utils import *
from complex_data import *
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import time



context={}


def start_deadline_checking(df, bot, user_id):
    check_deadlines_and_notify(df, bot, user_id)
    deadline_check_thread = Thread(target=schedule_deadline_check, args=(df, bot, user_id))
    deadline_check_thread.start()


# Декоратор для обработки команды /status
def change_status_decorator(func):
    def wrapper(message):
        user_id = message.chat.id
        # Проверяем, загрузил ли пользователь файл
        if user_id not in context or "df" not in context[user_id]:
            bot.send_message(user_id, "Пожалуйста, сначала загрузите таблицу.")
            return
        # Сохраняем текущую команду в контексте
        context[user_id]["current_command"] = "status"
        func(message)
    return wrapper


@bot.message_handler(commands=['status'])
@change_status_decorator
def handle_status_command(message):
    bot.send_message(message.chat.id, "Напишите номер заявки:")
    # Сохраняем, что ожидаем номер заявки
    context[message.chat.id]["awaiting_request_id"] = True


@bot.message_handler(func=lambda message: context.get(message.chat.id, {}).get("awaiting_request_id", False))
def handle_request_id(message):
    user_id = message.chat.id
    request_id = message.text.strip()
    # Проверяем, существует ли номер заявки в таблице
    df = context[user_id]["df"]
    if request_id not in df.iloc[:, 0].values:  # Столбец с номерами заявок
        bot.send_message(user_id, "Номер заявки не найден. Проверьте данные и попробуйте снова.")
        return
    # Сохраняем номер заявки в контексте
    context[user_id]["current_request_id"] = request_id
    context[user_id]["awaiting_request_id"] = False
    # Создаем кнопки для выбора статуса
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("В работе", "Исполнено")
    bot.send_message(user_id, "Выберите новый статус:", reply_markup=markup)


@bot.message_handler(func=lambda message: message.text in ["В работе", "Исполнено"])
def update_status(message):
    user_id = message.chat.id
    new_status = message.text
    request_id = context[user_id].get("current_request_id")
    if not request_id:
        bot.send_message(user_id, "Ошибка: Номер заявки не найден в контексте.")
        return
    try:
        # Обновляем статус в таблице
        df = context[user_id]["df"]
        row_index = df[df.iloc[:, 0] == request_id].index[0]  # Находим строку по номеру заявки
        df.iloc[row_index, 23] = new_status  # Обновляем статус в столбце 23
        # Сохраняем обновленную таблицу в контексте
        context[user_id]["df"] = df
        # Генерируем файл с обновленной таблицей для отправки
        output_bytes = io.BytesIO()
        with pd.ExcelWriter(output_bytes, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, header=True)  # Сохраняем без заголовков
        output_bytes.seek(0)
        # Отправляем измененную таблицу
        bot.send_document(
            user_id,
            output_bytes,
            caption=f"Статус для заявки {request_id} обновлен на '{new_status}'.",
            visible_file_name="updated_table_with_status.xlsx"
        )
    except Exception as e:
        bot.send_message(user_id, f"Ошибка при обновлении статуса: {e}")


# Запуск процесса авторизации
@bot.message_handler(commands=['start'])
def start(message):
    check_user_info(message)
    user_id = message.chat.id
    if not is_user_authorized(user_id):
        bot.send_message(user_id, "Для работы с ботом необходима авторизация через корпоративный Google аккаунт. Пожалуйста, перейдите по ссылке ниже и авторизуйтесь.")
        auth_url = get_auth_url()
        short_message = f"[Ссылка]({auth_url}) для авторизации"
        bot.send_message(message.chat.id, short_message, parse_mode="Markdown")
    else:
        bot.send_message(user_id, "Добро пожаловать! Вы авторизованы и можете использовать бота.")
        bot.send_message(user_id, "Пожалуйста, отправьте файл Excel для загрузки данных.")


@bot.message_handler(content_types=['document'])
def handle_document(message):
    global complex_streets
    user_id = message.chat.id
    # Проверяем авторизацию
    if not is_user_authorized(user_id):
        bot.send_message(user_id, "Вы не авторизованы. Пожалуйста, сначала пройдите авторизацию.")
        return
    file_id = message.document.file_id
    file_info = bot.get_file(file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    # Сохраняем файл и читаем его
    try:
        file_bytes = io.BytesIO(downloaded_file)
        df = load_excel_file(file_bytes)  # Загружаем файл без заголовков
        if df is None:
            raise ValueError("Не удалось загрузить данные из файла.")
        # Преобразуем дату подачи
        df.iloc[:, 2] = pd.to_datetime(df.iloc[:, 2], errors='coerce', dayfirst=True)  # Дата подачи в формате dd.mm.yyyy
        bot.send_message(user_id, "Файл успешно загружен! Обрабатываем данные...")
        # Пересчитываем дедлайны
        df_with_deadlines = add_deadlines_to_dataframe_by_index(df)
        # Сохраняем изменённую таблицу в контексте
        context[user_id] = {"df": df_with_deadlines}
        # Генерируем файл для отправки
        output_bytes = io.BytesIO()
        with pd.ExcelWriter(output_bytes, engine='openpyxl') as writer:
            df_with_deadlines.to_excel(writer, index=False, header=True)  # Сохраняем без заголовков
        output_bytes.seek(0)
        bot.send_document(user_id, output_bytes, caption="Обновленная таблица с дедлайнами.", visible_file_name="updated_table.xlsx")
        # Отображаем меню городов
        show_city_menu(message)
        start_deadline_checking(df, bot, user_id)
    except Exception as e:
        bot.send_message(user_id, f"Ошибка при обработке файла: {e}")


# Кнопки комплексов
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    if call.data.startswith('city_'):
        city = call.data.split('_')[1]
        markup = types.InlineKeyboardMarkup()
        for complex_name in city_complexes[city]:
            button = types.InlineKeyboardButton(text=complex_name, callback_data=f'complex_{complex_name}')
            markup.add(button)
        bot.send_message(call.message.chat.id, 'Выберите комплекс:', reply_markup=markup)
    elif call.data.startswith('complex_'):
        complex_name = call.data.split('_')[1]
        # Проверяем, загружен ли файл пользователем
        user_id = call.message.chat.id
        if user_id not in context or "df" not in context[user_id]:
            bot.send_message(user_id, "Пожалуйста, сначала загрузите файл Excel.")
            return
        # Берём изменённый DataFrame из контекста
        df = context[user_id]["df"]
        # Используем обновлённый DataFrame для выгрузки данных
        unload(complex_streets, complex_name, bot, call.message, df)


# Обработка кода авторизации
@bot.message_handler(func=lambda message: not message.text.startswith('/'))
def handle_auth_code(message):
    auth_code = message.text.strip()
    user_id = message.chat.id
    # Пробуем обменять код на учетные данные
    credentials = exchange_code_for_credentials(auth_code)
    if credentials and credentials.valid:
        user_info_service = build('oauth2', 'v2', credentials=credentials)
        user_info = user_info_service.userinfo().get().execute()
        email = user_info['email']
        if is_authorized_user(email):
            save_user_as_authorized(user_id)
            bot.send_message(user_id, "Вы успешно авторизованы!")
            bot.send_message(user_id, "Пожалуйста, отправьте файл Excel для загрузки данных.")
        else:
            bot.send_message(user_id, "Извините, доступ разрешен только для сотрудников компании.")
    else:
        bot.send_message(user_id, "Код авторизации неверен или истек. Попробуйте снова.")


@bot.message_handler(commands=['logout'])
def logout(message):
    user_id = message.from_user.id
    remove_user_from_authorized_list(user_id)
    bot.send_message(user_id, "Вы вышли из системы и больше не авторизованы.")


@bot.message_handler(commands=['stop'])
@authorized_only
def return_to_start(message):
    bot.send_message(message.chat.id, 'Вы вернулись к началу')
    bot.send_message(message.chat.id, 'Чем я могу еще вам помочь?')

#Кнопки городов
def show_city_menu(message):
    markup = types.InlineKeyboardMarkup()
    for city in city_complexes.keys():
        button = types.InlineKeyboardButton(text=city, callback_data=f'city_{city}')
        markup.add(button)
    bot.send_message(message.chat.id, 'Выберите город:', reply_markup=markup)

while True:
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        print(f"Ошибка при polling: {e}")
        time.sleep(5)  # Подождать 5 секунд перед перезапуском
