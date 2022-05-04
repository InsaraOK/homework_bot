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
TOKENS = ('PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID',)
BOT_MESSAGE = ('Бот успешно отправил сообщение - "{message}"'
               f' в чат {TELEGRAM_CHAT_ID}')
BOT_MESSAGE_FAIL = 'Отправка сообщения {message} не удалась по причине {error}'
RESPONSE_EXCEPTION_MESSAGE = (
    'При запросе с параметрами {url}, {headers}, {params}'
    ' произошел сбой сети по причине {error}')
RESPONSE_CODE_EXCEPTION_MESSAGE = (
    'На запрос с параметрами {url}, {headers}, {params}'
    ' получен код ответа {code}')
JSON_ERROR_MESSAGE = (
    'На запрос с параметрами {url}, {headers}, {params}'
    ' от сервера получен отказ от обслуживания по причине {error}.'
    'Информация о причине отказа соотвтетствует ключу {key}.')
WRONG_STATUS_MESSAGE = ('Неожиданный статус {status}'
                        ' домашней работы {name} обнаружен в ответе.')
TRUE_STATUS_MESSAGE = 'Изменился статус проверки работы "{name}". {verdict}'
MAIN_EXCEPTION_MESSAGE = 'Сбой в работе программы: {error}'
CHECK_RESPONSE_TYPE_MESSAGE = ('Тип данных в ответе от API {type}'
                               'не сооответствует ожидаемому')
CHECK_RESPONSE_KEY_MESSAGE = ('Тип данных по ключу "homeworks" {type}',
                              'не сооответствует ожидаемому')
CHECK_TOKENS_MESSAGE = 'Переменная окружения {name} не доступна.'
MAIN_CHECK_TOKENS_MESSAGE = 'Переменные окружения не доступны.'

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
        return True
    except Exception as error:
        logger.exception(BOT_MESSAGE_FAIL.format(message=message, error=error))
        return False


def get_api_answer(current_timestamp):
    """Запрос к API-сервису."""
    params = {'from_date': current_timestamp}
    request_parameters = dict(
        url=ENDPOINT,
        headers=HEADERS,
        params=params,
    )
    try:
        response = requests.get(**request_parameters)
    except requests.RequestException as error:
        raise ConnectionError(RESPONSE_EXCEPTION_MESSAGE.format(
            **request_parameters, error=error))
    if response.status_code != 200:
        raise ResponseCodeException(
            RESPONSE_CODE_EXCEPTION_MESSAGE.format(
                **request_parameters,
                code=response.status_code
            ))
    response = response.json()
    for container in ['code', 'error']:
        if container in response:
            error = response.get(container)
            raise ValueError(
                JSON_ERROR_MESSAGE.format(
                    **request_parameters,
                    error=error,
                    key=container
                ))
    return response


def check_response(response):
    """Проверка ответа API на корректность."""
    if not isinstance(response, dict):
        raise TypeError(
            CHECK_RESPONSE_TYPE_MESSAGE.format(type=type(response)))
    if 'homeworks' not in response:
        raise KeyError('ответ от API не содержит ключ "homeworks"')
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise TypeError(
            CHECK_RESPONSE_KEY_MESSAGE.format(type=type(homeworks)))
    return homeworks


def parse_status(homework):
    """Проверка статуса домашней работы."""
    name = homework['homework_name']
    status = homework['status']
    if status not in VERDICTS:
        raise ValueError(WRONG_STATUS_MESSAGE.format(status=status, name=name))
    return TRUE_STATUS_MESSAGE.format(name=name, verdict=VERDICTS[status])


def check_tokens():
    """Проверка доступности переменных окружения."""
    missing_tokens = [name for name in TOKENS if globals()[name] is None]
    if missing_tokens:
        logger.critical(CHECK_TOKENS_MESSAGE.format(name=missing_tokens))
        return False
    return True


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        raise ValueError(MAIN_CHECK_TOKENS_MESSAGE)
    current_timestamp = int(time.time())
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    exception_message = ''
    while True:
        try:
            response = get_api_answer(current_timestamp)
            if send_message(bot, check_response(response)[0]):
                current_timestamp = response.get(
                    'current_date', current_timestamp)
        except Exception as error:
            message = MAIN_EXCEPTION_MESSAGE.format(error=error)
            logger.exception(message)
            if message != exception_message:
                if send_message(bot, message):
                    exception_message = message
        time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
