import json
import logging
import os
import sys
import time

import requests
import telegram
from dotenv import load_dotenv

from exceptions import ResponseCodeException

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
BOT_MESSAGE = ('Бот успешно отправил сообщение - "{message}"'
               f' в чат {TELEGRAM_CHAT_ID}')
BOT_MESSAGE_2 = 'Отправка сообщения {message} не удалась по причине {error}'
RESPONSE_EXCEPTION_MESSAGE = (
    'На запрос с параметрами {endpoint}, {headers}, {params}.'
    ' Получен код ответа {code}')
JSON_ERROR_MESSAGE = (
    'Ответ {response} от сервера не соответствует'
    ' ожидаемому по причине {error}.')
WRONG_STATUS_MESSAGE = ('Недокументированный статус {status}'
                        ' домашней работы {name} обнаружен в ответе.')
TRUE_STATUS_MESSAGE = 'Изменился статус проверки работы "{name}". {verdict}'
MAIN_EXCEPTION_MESSAGE = 'Сбой в работе программы: {error}'
CHECK_RESPONSE_MESSAGE = ('Тип данных в ответе от API {type}'
                          'не сооответствует ожидаемому')
CHECK_RESPONSE_MESSAGE_2 = ('Тип данных по ключу "homeworks" {type}',
                            'не сооответствует ожидаемому')
CHECK_TOKENS_MESSAGE = 'Переменная окружения {name} не доступна.'

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
        logger.info(BOT_MESSAGE.format(message=message))
    except Exception as error:
        logger.exception(BOT_MESSAGE_2.format(message=message, error=error))


def get_api_answer(current_timestamp):
    """Запрос к API-сервису."""
    params = {'from_date': current_timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except requests.RequestException as error:
        raise ConnectionError(error)
    if response.status_code != 200:
        raise ResponseCodeException(
            RESPONSE_EXCEPTION_MESSAGE.format(
                endpoint=ENDPOINT, headers=HEADERS,
                params=params, code=response.status_code
            ))
    response = response.json()
    if 'code' in response:
        error = response.get('code')
        raise json.JSONDecodeError(
            JSON_ERROR_MESSAGE.format(response=response, error=error))
    if 'error' in response:
        error = response.get('error')
        raise json.JSONDecodeError(
            JSON_ERROR_MESSAGE.format(response=response, error=error))
    return response


def check_response(response):
    """Проверка ответа API на корректность."""
    if not isinstance(response, dict):
        raise TypeError(CHECK_RESPONSE_MESSAGE.format(type=type(response)))
    if 'homeworks' not in response:
        raise KeyError('ответ от API не содержит ключ "homeworks"')
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise TypeError(CHECK_RESPONSE_MESSAGE_2.format(type=type(homeworks)))
    return homeworks


def parse_status(homework):
    """Извлечение имени и статуса домашней работы."""
    name = homework['homework_name']
    status = homework['status']
    if status not in VERDICTS:
        raise ValueError(WRONG_STATUS_MESSAGE.format(status=status, name=name))
    return TRUE_STATUS_MESSAGE.format(name=name, verdict=VERDICTS[status])


def check_tokens():
    """Проверка доступности переменных окружения."""
    tokens = ('PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID',)
    result = True
    for name in tokens:
        if globals()[name] is None:
            logger.critical(CHECK_TOKENS_MESSAGE.format(name=name))
            result = False
    return result


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        raise ValueError('Переменные окружения не доступны')
    current_timestamp = int(time.time())
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    exception_message = ''
    while True:
        try:
            response = get_api_answer(current_timestamp)
            current_timestamp = response.get(
                'current_date',
                default=current_timestamp
            )
            homeworks = check_response(response)
            message = parse_status(homeworks[0])
            send_message(bot, message)
        except Exception as error:
            message = MAIN_EXCEPTION_MESSAGE.format(error=error)
            logger.exception(message)
            if message != exception_message:
                send_message(bot, message)
                exception_message = message
        time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
