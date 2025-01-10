import pandas as pd
from complex_data import *
from utils import *


def load_excel_file(file_bytes):
    try:
        # Попытка считать с заголовком на первой строке
        df = pd.read_excel(file_bytes, header=0)
        if df.empty:
            raise ValueError("Не удалось загрузить данные с заголовком на первой строке.")
        # Проверяем, есть ли столбец "Адрес дома/территория" в первой строке
        if 'Адрес дома/территория' in df.columns:
            print("Столбец 'Адрес дома/территория' найден в первой строке.")
        else:
            raise ValueError("Столбец 'Адрес дома/территория' не найден в первой строке.")
    except Exception as e:
        print(f"Ошибка при загрузке с заголовком на первой строке: {e}")
        try:
            # Попытка загрузить с заголовком на второй строке
            print("Попытка загрузки с заголовком на второй строке...")
            df = pd.read_excel(file_bytes, header=1)
            if df.empty:
                raise ValueError("Не удалось загрузить данные с заголовком на второй строке.")
            # Проверяем, есть ли столбец "Адрес дома/территория" во второй строке
            if 'Адрес дома/территория' in df.columns:
                print("Столбец 'Адрес дома/территория' найден во второй строке.")
            else:
                raise ValueError("Столбец 'Адрес дома/территория' не найден во второй строке.")
        except Exception as e:
            print(f"Ошибка при загрузке с заголовком на второй строке: {e}")
            return None  # Возвращаем None, если не удалось загрузить файл
    # Если загрузка успешна
    return df


def unload(compex_streets, complex_name, bot, message, df):
    if 'Адрес дома/территория' not in df.columns:
        bot.send_message(message.chat.id, "Столбец 'Адрес дома/территория' не найден.")
        return
    street_list = complex_streets.get(complex_name, [])
    if not street_list:
        bot.send_message(message.chat.id, f"Не найдены улицы для комплекса {complex_name}.")
        return
    # Фильтрация строк по столбцу 'Адрес дома/территория'
    filtered_df = df[
        (df['Адрес дома/территория'].apply(
            lambda x: any(
                street.strip() in [address.strip() for address in x.split(',')]
                for street in ','.join(street_list).split(',')  # разделяем все улицы в street_list
            ) if isinstance(x, str) else False) &
        (df['Unnamed: 23'] == "В работе")
    )]
    # Отправка сообщений
    comm = '*Комментарий*:'
    cnt = 0
    for i, row in filtered_df.iterrows():
        sms = f"№{cnt+1}\n"
        sms += f"*Жилищный комплекс*: {complex_name}\n"
        sms += f"*Номер заявки*: {escape_markdown(str(row['Unnamed: 0']))}\n"  # Номер заявки
        sms += f"*Время подачи*: {escape_markdown(str(row['Unnamed: 2']))}\n"  # Время подачи
        sms += f"*Дата дедлайна*: {escape_markdown(str(row['Unnamed: 29']))}\n"  # Дедлайн
        sms += f"*Адрес*: {escape_markdown(str(row['Адрес дома/территория']))}, {escape_markdown(str('Кв.'))} {escape_markdown(str(row['Номер помещения']))}\n"
        sms += f"*ФИО*: {escape_markdown(str(row['Фамилия (для ФЛ)']))} {escape_markdown(str(row['Имя (для ФЛ)']))} {escape_markdown(str(row['Отчество (для ФЛ)']))}\n"
        sms += f"*Номер телефона*: {escape_markdown('+' + str(row['Номер телефона']).replace(' ', ''))}\n"
        sms += f"*Почта*: {escape_markdown(str(row['E-mail']))}\n"
        sms += f"*Категория запроса*: {escape_markdown(str(row['Unnamed: 4']))}\n"
        sms += "*Категории*: {0}\n".format(escape_markdown(str(row['Unnamed: 24']).split('\n')[0]))  # Категории
        sms += f"{comm}\n"
        try:
            sms += "{0}\n".format(escape_markdown(str(row['Unnamed: 24']).split('\n')[2]))
        except IndexError:
            pass
        sms += f"*Статус*: {row['Unnamed: 23']}\n"  # Выполнено/в работе
        sms += '\n'
        cnt += 1
        try:
            bot.send_message(message.chat.id, sms, parse_mode="MarkdownV2")
        except Exception as e:
            print(f"Ошибка при отправке сообщения: {e}")








