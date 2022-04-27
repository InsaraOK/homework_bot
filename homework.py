import json
import logging
import os
import sys
import time

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

PRACTICUM_TOKEN = os.getenv('YP_TOKEN')
TELEGRAM_TOKEN = os.getenv('T_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('T_CHAT_ID')


RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}
BOT_MESSAGE = (f'Бот успешно отправил сообщение - "{0}" в чат {1}')
RE_EX_MESSAGE = (
    f'На запрос с параметрами {0}, {1}, {2}. Получен код ответа {3}')
RE_EX_MESSAGE_2 = (
    f'Запрос к API-сервису не удалася по причине {0}.'
    f'Параметры запроса {1}, {2}, {3}.'
)
JS_ER_MESSAGE = (
    f'Ответ {0} от сервера не соответствует ожидаемому по причине {1}.')

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler(sys.stdout)
file_handler = logging.FileHandler(__file__ + '.log')
logger.addHandler(console_handler)
logger.addHandler(file_handler)
formatter = logging.Formatter(
    '%(asctime)s %(levelname)s %(name)s %(funcName)s %(lineno)d %(message)s'
)
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)


def send_message(bot, message):
    """Отправка сообщения в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(BOT_MESSAGE.format(message, TELEGRAM_CHAT_ID))
    except Exception as error:
        logger.exception(f'Отправка сообщения {message} не удалась')
        raise error


def get_api_answer(current_timestamp):
    """Запрос к API-сервису."""
    params = {'from_date': current_timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != 200:
            raise requests.HTTPError(
                RE_EX_MESSAGE.format(
                    ENDPOINT, HEADERS,
                    params, response.status_code
                ))
    except requests.RequestException as error:
        logger.error(
            RE_EX_MESSAGE_2.format(error, ENDPOINT, HEADERS, params),
            exc_info=True)
        raise error
    try:
        re = response.json()
    except json.JSONDecodeError as error:
        logger.exception(JS_ER_MESSAGE.format(re, error))
        raise error
    else:
        return re


def check_response(response):
    """Проверка ответа API на корректность."""
    if isinstance(response, dict) is not True:
        message = (f'Тип данных в ответе от API {type(response)}',
                   'не сооответствует ожидаемому')
        raise TypeError(message)
    if 'homeworks' not in response:
        message = 'ответ от API не содержит ключ "homeworks"'
        raise KeyError(message)
    homeworks = response.get('homeworks')
    if isinstance(homeworks, list) is not True:
        message = (f'Тип данных по ключу "homeworks" {type(homeworks)}',
                   'не сооответствует ожидаемому')
        raise TypeError(message)
    return homeworks


def parse_status(homework):
    """Извлечение имени и статуса домашней работы."""
    if isinstance(homework, dict) is not True:
        message = (f'Тип данных {type(homework)}',
                   'не сооответствует ожидаемому')
        raise TypeError(message)
    if 'status' not in homework:
        message = 'homework не содержит ключ "status"'
        raise KeyError(message)
    if 'homework_name' not in homework:
        message = 'homework не содержит ключ "homework_name"'
        raise KeyError(message)
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status not in VERDICTS:
        message = (f'Недокументированный статус {homework_status}'
                   f' домашней работы {homework_name} обнаружен в ответе.')
        raise ValueError(message)
    else:
        verdict = VERDICTS[homework_status]
        return (f'Изменился статус проверки работы '
                f'"{homework_name}". {verdict}')


def check_tokens():
    """Проверка доступности переменных окружения."""
    tokens = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    for token in tokens:
        if token is None:
            message = f'Переменная окружения {token} не доступна.'
            logger.critical(message)
            return False
        else:
            return True


def main():
    """Основная логика работы бота."""
    if check_tokens() is not True:
        message = 'Переменные окружения не доступны'
        logger.critical(message)
        raise SystemExit(message)
    current_timestamp = int(time.time())
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    while True:
        try:
            response = get_api_answer(current_timestamp)
            current_timestamp = (
                response.get('current_date') or int(time.time()))
            homeworks = check_response(response)
            homework = homeworks[0]
            message = parse_status(homework)
            send_message(bot, message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.exception(message)
            send_message(bot, message)
        time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
