import pickle
from google_auth_oauthlib.flow import Flow
from bot_instance import bot


CREDENTIALS_FILE = 'client_secret.json'
AUTHORIZED_USERS_FILE = 'authorized_users.pkl'
AUTHORIZED_DOMAIN = '@gmail.com'
#AUTHORIZED_DOMAIN = '@brusnika.ru'


# Декоратор для проверки авторизации
def authorized_only(handler):
    def wrapper(message):
        user_id = message.chat.id
        if not is_user_authorized(user_id):
            bot.send_message(user_id, "Эта команда доступна только для авторизованных пользователей.")
            return
        return handler(message)
    return wrapper


def is_authorized_user(email):
    """
    Проверяет, является ли email пользователя допустимым для авторизации.
    """
    return email.endswith(AUTHORIZED_DOMAIN)


def get_auth_url():
    """
    Создает ссылку для авторизации пользователя через Google OAuth 2.0.
    """
    flow = Flow.from_client_secrets_file(CREDENTIALS_FILE, scopes=["openid", "https://www.googleapis.com/auth/userinfo.email"])
    flow.redirect_uri = "urn:ietf:wg:oauth:2.0:oob"
    auth_url, _ = flow.authorization_url(prompt='consent')
    return auth_url


def exchange_code_for_credentials(auth_code):
    """
    Обменивает код авторизации на учетные данные.
    """
    flow = Flow.from_client_secrets_file(CREDENTIALS_FILE, scopes=["openid", "https://www.googleapis.com/auth/userinfo.email"])
    flow.redirect_uri = "urn:ietf:wg:oauth:2.0:oob"
    try:
        flow.fetch_token(code=auth_code)
        return flow.credentials
    except Exception as e:
        print("Ошибка при обмене кода:", e)
        return None


def save_user_as_authorized(user_id):
    """
    Сохраняет идентификатор пользователя как авторизованный.
    """
    try:
        with open(AUTHORIZED_USERS_FILE, 'rb') as f:
            authorized_users = pickle.load(f)
    except FileNotFoundError:
        authorized_users = set()

    authorized_users.add(user_id)

    with open(AUTHORIZED_USERS_FILE, 'wb') as f:
        pickle.dump(authorized_users, f)


def is_user_authorized(user_id):
    """
    Проверяет, является ли пользователь авторизованным.
    """
    try:
        with open(AUTHORIZED_USERS_FILE, 'rb') as f:
            authorized_users = pickle.load(f)
            return user_id in authorized_users
    except FileNotFoundError:
        return False


def remove_user_from_authorized_list(user_id):
    """
    Удаляет пользователя из списка авторизованных.
    """
    try:
        with open(AUTHORIZED_USERS_FILE, 'rb') as f:
            authorized_users = pickle.load(f)
    except FileNotFoundError:
        authorized_users = set()

    if user_id in authorized_users:
        authorized_users.remove(user_id)

    with open(AUTHORIZED_USERS_FILE, 'wb') as f:
        pickle.dump(authorized_users, f)


def save_user_info(user_id, username):
    username = username if username is not None else "Unknown"
    with open('user_data.txt', 'a') as f:
        f.write(f"{user_id}, {username}\n")


def check_user_info(message):
    user_id = message.from_user.id
    username = message.from_user.username
    with open('user_data.txt', 'r') as f:
        users = f.read().splitlines()
    user_info = f"{user_id}, {username}"
    if user_info not in users:
        save_user_info(user_id, username)
