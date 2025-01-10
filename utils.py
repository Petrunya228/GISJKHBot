import re


def escape_markdown(text):
    if not isinstance(text, str):
        text = str(text)  # Убедимся, что входной текст - это строка
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    # Экранируем все специальные символы
    text = re.sub(f"([{re.escape(escape_chars)}])", r"\\\1", text)
    # Дополнительно экранируем кавычки, если это необходимо
    text = text.replace('"', '\\"').replace("'", "\\'")
    return text


def read_token_from_file(filename):
    with open(filename, 'r') as f:
        return f.read().strip()




