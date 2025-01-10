import telebot
from utils import read_token_from_file


token = read_token_from_file('token.ini')
bot = telebot.TeleBot(token)
towns = ['Екатеринбург','Тюмень','Москва','Омск','Сургут','Курган','Новосибирск']
