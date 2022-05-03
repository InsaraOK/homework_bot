P = None
T = None
TE = None


def check_tokens():
    tokens = ('P', 'T', 'TE',)
    result = True
    message = 'Переменная окружения {name} не доступна.'
    missing_tokens = [name for name in tokens if globals()[
        name] is None]
    if missing_tokens != []:
        print(message.format(name=missing_tokens))
        result = False
    return print(result)


check_tokens()
