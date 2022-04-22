from dotenv import load_dotenv
import logging
import os
import requests
import sys
import time


import telegram

from exceptions import TokenExistsException
load_dotenv()


PRACTICUM_TOKEN = os.getenv('YP_TOKEN')
TELEGRAM_TOKEN = os.getenv('T_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('T_CHAT_ID')
BOT = telegram.Bot(token=TELEGRAM_TOKEN)

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s %(levelname)s %(name)s %(message)s'
)
handler.setFormatter(formatter)


def send_message(bot, message):
    """Отправка сообщения в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(
            f'Бот успешно отправил сообщение - "{message}"'
            f' в чат {TELEGRAM_CHAT_ID}')
    except Exception as error:
        logger.error(
            f'Отправка сообщения не удалась по причине {error}', exc_info=True)


def get_api_answer(current_timestamp):
    """Запрос к API-сервису."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code != 200:
        raise Exception('API-сервис не доступен')
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except Exception as error:
        logger.error(
            f'Запрос к API-сервису не удалася по причине {error}',
            exc_info=True)
    else:
        return response.json()


def check_response(response):
    """Проверка ответа API на корректность."""
    if type(response) != dict:
        message = 'Ответ от API не содержит словарь'
        logger.error(message)
        raise TypeError
    if type(response) == dict:
        if len(response) == 0:
            message = 'Ответ от API содержит пустой словарь'
            logger.error(message)
            raise ValueError
    try:
        homeworks = response.get('homeworks')
        if type(homeworks) != list:
            raise TypeError
    except KeyError as error:
        logger.error(error, exc_info=True)
        BOT.send_message(TELEGRAM_CHAT_ID, error)
    else:
        return homeworks


def parse_status(homework):
    """Извлечение имени и статуса о конкретной домашней работе."""
    homework_name = homework.get('homework_name')
    if 'homework_name' not in homework:
        raise KeyError
    try:
        homework_status = homework.get('status')
        if 'status' not in homework:
            raise KeyError
    except KeyError as error:
        logger.error(error, exc_info=True)
        BOT.send_message(TELEGRAM_CHAT_ID, error)
        raise KeyError
    else:
        if homework_status not in HOMEWORK_STATUSES:
            message = ('Недокументированный статус'
                       ' домашней работы',
                       ' обнаружен в ответе.')
            logger.error(message)
            BOT.send_message(TELEGRAM_CHAT_ID, message)
            raise ValueError(message)
        else:
            verdict = HOMEWORK_STATUSES[homework_status]
            return (f'Изменился статус проверки работы '
                    f'"{homework_name}". {verdict}')


def check_tokens():
    """Проверка доступности переменных окружения."""
    if (PRACTICUM_TOKEN is None
        or TELEGRAM_TOKEN is None
            or TELEGRAM_CHAT_ID is None):
        return False
    else:
        return True


def main():
    """Основная логика работы бота."""
    try:
        check_tokens() is True
    except TokenExistsException as error:
        logger.critical(error, exc_info=True)
        exit()
    current_timestamp = int(time.time())
    check_tokens()
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if len(homeworks) != 0:
                for hw in homeworks:
                    message = parse_status(hw)
                    send_message(BOT, message)
            else:
                raise ValueError
            time.sleep(RETRY_TIME)
        except ValueError as error:
            message = 'Список домашних работ пуст'
            logger.debug(error, exc_info=True)
            send_message(BOT, message)
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(BOT, message)
            time.sleep(RETRY_TIME)
        else:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            for hw in homeworks:
                message = parse_status(hw)
                send_message(BOT, message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
