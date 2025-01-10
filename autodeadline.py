import pandas as pd
from datetime import timedelta
from deadlines_data import category_deadlines


def add_deadlines_to_dataframe_by_index(df):
    """
    Добавляет дедлайны в DataFrame на основе кодов категорий и времени на исправление.
    Аргументы:
    - df: DataFrame, содержащий данные заявки.
    Возвращает:
    - Обновленный DataFrame с добавленным/обновленным столбцом дедлайнов.
    """
    # Определяем индексы столбцов в исходной таблице
    CREATION_DATE_COLUMN_INDEX = 2  # Индекс столбца с датой создания обращения
    CATEGORY_CODE_COLUMN_INDEX = 3  # Индекс столбца с кодом темы обращения
    DEADLINE_COLUMN_INDEX = 29  # Индекс столбца для дедлайнов в новой таблице

    def extract_main_category(code):
        """Извлекает основную категорию из кода темы обращения."""
        try:
            return str(code).split('.')[0]
        except AttributeError:
            return None
    # Проверяем наличие необходимых индексов столбцов
    if CREATION_DATE_COLUMN_INDEX >= len(df.columns) or CATEGORY_CODE_COLUMN_INDEX >= len(df.columns):
        raise ValueError("Исходная таблица не содержит ожидаемых данных в указанных столбцах.")
    # Обновляем столбец "Дата окончания срока обращения"
    deadlines = []
    for _, row in df.iterrows():
        creation_date = row.iloc[CREATION_DATE_COLUMN_INDEX]
        category_code = row.iloc[CATEGORY_CODE_COLUMN_INDEX]
        # Извлекаем основную категорию
        main_category = extract_main_category(category_code)
        # Получаем время на исправление
        days_to_fix = category_deadlines.get(main_category, None)
        # Рассчитываем дедлайн
        if days_to_fix is not None and not pd.isna(creation_date):
            try:
                deadline = pd.to_datetime(creation_date) + timedelta(days=days_to_fix)
            except Exception:
                deadline = None
        else:
            deadline = None
        deadlines.append(deadline)
    # Добавляем или обновляем столбец для дедлайнов
    if DEADLINE_COLUMN_INDEX >= len(df.columns):
        # Если столбца еще нет, добавляем его
        df.insert(DEADLINE_COLUMN_INDEX, "Unnamed: 29", deadlines)
    else:
        # Если столбец существует, обновляем его
        df.iloc[:, DEADLINE_COLUMN_INDEX] = deadlines
    return df

