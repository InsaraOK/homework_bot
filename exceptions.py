import os

from dotenv import load_dotenv


load_dotenv()

TOKENS = [
    os.getenv('YP_TOKEN'),
    os.getenv('T_TOKEN'),
    os.getenv('T_CHAT_ID'),
]
HOMEWORK_STATUSES = [
    'approved',
    'reviewing',
    'rejected',
]


class TokenExistsException(Exception):
    pass


def token_exists_chek(token):
    for token in TOKENS:
        if token is None:
            raise TokenExistsException(
                'Токен не существует или его значение не верное.')
