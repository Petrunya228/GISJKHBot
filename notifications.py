import pandas as pd
from datetime import datetime
from utils import escape_markdown
import time
import schedule


def send_custom_sticker(bot,user_id):
    sticker_id ='CAACAgIAAxkBAAELEUFnZVbDgJQqofUSb5OD-gsWr5VCXgACoxAAAvF3qEh-OxgSw5fVQTYE'
    bot.send_sticker(chat_id=user_id, sticker=sticker_id)


# Проверка на приближающийся дедлайн и отправка уведомлений
def check_deadlines_and_notify(df, bot, user_id):
    # Текущая дата (сбрасываем время)
    today = datetime.now().date()
    # Перебираем все дедлайны и отправляем уведомления, если до дедлайна остается 1 день
    for _, row in df.iterrows():
        status = row.iloc[23]  # Столбец с статусом (Unnamed: 23)
        if status != "В работе":
            continue  # Пропускаем задачи, которые уже выполнены
        deadline_str = row.iloc[29]  # Столбец с дедлайнами (Unnamed: 29)
        # Если дедлайн уже в формате даты (Timestamp), преобразуем его в строку
        if isinstance(deadline_str, pd.Timestamp):
            deadline_str = deadline_str.strftime('%d.%m.%Y')
        # Преобразуем строку в дату
        try:
            deadline = datetime.strptime(deadline_str, '%d.%m.%Y').date()
        except ValueError:
            continue  # Если дата некорректна, пропускаем
        # Вычисляем разницу между текущей датой и дедлайном
        days_left = (deadline - today).days
        # Если до дедлайна остается 1 или меньше дня, отправляем уведомление
        if 0 < days_left <= 3:
            send_custom_sticker(bot,user_id)
            if days_left == 1:
                day = 'день'
            elif 2 <= days_left <= 4:
                day = 'дня'
            elif days_left >= 5 or days_left == 0:
                day = 'дней'
            else:
                day = 'день'  # Для отрицательных чисел (когда дедлайн прошел)
            # Формирование сообщения для уведомления
            comm = '*Комментарий*:'
            sms = f"{escape_markdown('🚨Внимание🚨')}\n"
            sms += f"{escape_markdown('Приближается дедлайн для задачи с номером')}\n"
            sms += f"{escape_markdown(f'{row.iloc[0]}')} \n"
            sms += f"{escape_markdown(f'Осталось времени: {days_left} {day}.')}\n\n"
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
            # Отправляем сообщение пользователю
            try:
                bot.send_message(user_id, sms, parse_mode="MarkdownV2")
            except Exception as e:
                print(f"Ошибка при отправке сообщения: {e}")

"""
# Функция для планирования проверки дедлайнов каждые 10 секунд
def schedule_deadline_check(df, bot, user_id):
    while True:
        check_deadlines_and_notify(df, bot, user_id)  # Проверка дедлайнов
        time.sleep(100)
"""

# Функция для планирования проверки дедлайнов
def schedule_deadline_check(df, bot, user_id):
    # Проверка дедлайнов будет выполняться ежедневно
    schedule.every().day.at("09:30").do(check_deadlines_and_notify, df=df, bot=bot, user_id=user_id)
    while True:
        schedule.run_pending()  # Выполняет все запланированные задачи
        time.sleep(60)  # Проверка будет выполняться каждую минуту

