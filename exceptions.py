class ResponseCodeException(Exception):
    pass


def response_code_check(response):
    if response.status_code != 200:
        raise ResponseCodeException
