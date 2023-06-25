# Концептуально не понимаю ТЗ. Как я понял, программа не должна останавливать
# работу в любом случае, кроме, когда не доступны обязательные токены.
# А тесты требуют выбрасывать исключения которые останавливают работу
# программы. В итоге наворотил непойми что, чтобы их пройти
import logging
import os
import time

import requests
import telegram
from logging import StreamHandler
from http import HTTPStatus


from dotenv import load_dotenv


class TokensNotAvailable(Exception):
    """Mandatort token is missing."""

    pass


class UnexpectedResponseStatus(Exception):
    """Mandatort token is missing."""

    pass


load_dotenv()


logging.basicConfig(
    level=logging.DEBUG,
    filename='hw_bot.log',
    format='%(asctime)s, %(lineno)d, %(levelname)s, %(message)s, %(funcName)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = StreamHandler()
logger.addHandler(handler)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

test_responce = {'current_date': 1684579682,
                 'homeworks': [{
                     'date_updated': '2023-04-23T18:51:30Z',
                     'homework_name': 'Dragonwlad__hw05_final.zip',
                     'id': 792402,
                     'lesson_name': 'Проект спринта: подписки на авторов',
                     'reviewer_comment': 'Принято!',
                     'status': 'approved'
                 }, ]
                 }


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Checking access to global tokens."""
    if not PRACTICUM_TOKEN:
        logging.critical('PRACTICUM_TOKEN is not available,'
                         ' programm stoped')
        raise TokensNotAvailable('PRACTICUM_TOKEN is not available,'
                                 ' programm stoped')
    if not TELEGRAM_TOKEN:
        logging.critical('TELEGRAM_TOKEN is not available,'
                         ' programm stoped')
        raise TokensNotAvailable('TELEGRAM_TOKEN is not available,'
                                 ' programm stoped')
    if not TELEGRAM_CHAT_ID:
        logging.critical('TELEGRAM_CHAT_ID is not available,'
                         ' programm stoped')
        raise TokensNotAvailable('TELEGRAM_CHAT_ID is not available,'
                                 ' programm stoped')
    return True


def send_message(bot, message):
    """Send message about change status in HW."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug('HW status change message sent successfully')
    except Exception as error:
        logging.error(f'Failed to send message, erorr - {error}')


def get_api_answer(timestamp):
    """Request to api YP for the status of work."""
    payload = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(ENDPOINT,
                                         headers=HEADERS,
                                         params=payload)
    except AttributeError:
        logging.error('AttributeError - Unexpected response from the server')

    except Exception as error:
        message = (f'Responce from YP not received, error -{error}')
        logging.error(message)
        return False
    if homework_statuses.status_code != HTTPStatus.OK:
        logging.error(f'Unexpected response status code from the server:'
                      f'{homework_statuses}')
        raise UnexpectedResponseStatus
        # return False
    logging.debug(f'Answer received:'
                  f'{homework_statuses}')
    homework_statuses = homework_statuses.json()
    return homework_statuses


def check_response(response):
    """Checking variables from answer YP."""
    if 'homeworks' not in response or response['homeworks'] is None:
        logging.error('no key homeworks')
        raise TypeError()

    if not isinstance(response, dict):
        logging.error('uncorrect answer from server')
        raise TypeError()

    if not isinstance(response['homeworks'], list):
        logging.error('uncorrect answer from server')
        raise TypeError()
    logging.debug(f'Answer {response}')
    return response['homeworks']


def get_key_or_raise(data, key):
    """Check data from HW status."""
    if not isinstance(data, dict):
        logging.error(f'dict expected, received: {type(data)}')
        raise KeyError(f'dict expected, received: {type(data)}')
    if key not in data:
        logging.error(f'{key} not found in {data.keys()}')
        raise KeyError(f'{key} not found in {data.keys()}')
    return data[key]


def parse_status(homework):
    """Check change HW."""
    # AssertionError: Убедитесь, что функция `parse_status` выбрасывает
    # исключение, когда в ответе API домашки нет ключа `homework_name`.
    # Зачем? Мы же еще в check_response проверили что ключ есть

    homework_name = get_key_or_raise(homework, 'homework_name')
    status = get_key_or_raise(homework, 'status')
    verdict = get_key_or_raise(HOMEWORK_VERDICTS, status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    logging.debug(timestamp)
    error_message = None
    last_status = []
    while True:
        try:
            responce = get_api_answer(timestamp)
            homework = check_response(responce)

            if homework:
                status = parse_status(homework[0])
                if status != last_status:
                    send_message(bot=bot, message=status)
                    last_status = status
                    timestamp = int(time.time())

        except Exception as error:
            message = f'Critical error Сбой в работе программы: {error}'
            logging.critical(message)
            if error_message == error:
                bot.send_message(TELEGRAM_CHAT_ID, message)
            error_message = error
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
