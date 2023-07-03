import logging
import sys
import os
import time
from http import HTTPStatus

from contextlib import suppress
from dotenv import load_dotenv
from Exception import TokensNotAvailable
from Exception import UnexpectedResponseStatus
import requests
import telegram


load_dotenv()

# Настроил отдельный логгер. Но не очень понимаю куда теперь логи пишутся.
# Из описания sys.stdout понял что в терминал, но в терминал ничего не приходит
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s, %(lineno)d, %(levelname)s, %(message)s, %(funcName)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


logging.debug('programma start')

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Checking access to global tokens."""
    tokens = ('PRACTICUM_TOKEN',
              'TELEGRAM_TOKEN',
              'TELEGRAM_CHAT_ID',
              )
    missing_tokens = [token for token in tokens if globals()[token] is None]

    if missing_tokens:
        logging.critical(f'{missing_tokens} is not available,'
                         ' programm stoped')
        raise TokensNotAvailable(f'{missing_tokens} is not available,'
                                 ' programm stoped')


def send_message(bot, message):
    """Send message about change status in HW."""
    logging.info('try sent message about change status in HW.')
    bot.send_message(TELEGRAM_CHAT_ID, message)
    logging.debug('HW status change message sent successfully')


def get_api_answer(timestamp):
    """Request to api YP for the status of work."""
    logging.info('start request to api YP for the status of work')
    payload = {'from_date': timestamp}
    try:
        api_answer = requests.get(ENDPOINT,
                                  headers=HEADERS,
                                  params=payload)
    except requests.RequestException as error:
        raise ConnectionError(f'Response from YP not received, {error}')
    if api_answer.status_code != HTTPStatus.OK:
        raise UnexpectedResponseStatus('Unexpected response status'
                                       f'code from the server: {api_answer}')
    logging.debug(f'Answer received:'
                  f'{api_answer}')
    api_answer = api_answer.json()
    return api_answer


def check_response(response):
    """Checking variables from answer YP."""
    logging.info('start check_response ')
    if not isinstance(response, dict):
        raise TypeError('uncorrect answer from server')
    if 'homeworks' not in response:
        raise KeyError('no key homeworks')
    if not isinstance(response['homeworks'], list):
        raise TypeError('uncorrect answer from server')
    logging.debug('check_response done')
    return response['homeworks']


def parse_status(homework):
    """Check change HW."""
    logging.info('start parse_status ')

    for key in ('homework_name', 'status'):
        if key not in homework.keys():
            raise ValueError(f'{key} not found in {homework.keys()}')
    if homework['status'] not in HOMEWORK_VERDICTS.keys():
        raise ValueError(f'{homework["status"]} not found'
                         f'in {HOMEWORK_VERDICTS.keys()}')

    logging.info('parse_status done')
    return (f'Изменился статус проверки работы "{homework["homework_name"]}".'
            f' {HOMEWORK_VERDICTS[homework["status"]]}')


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    logging.debug(f'HW bot started, timestamp = {timestamp}')
    last_status = None
    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            if not homework:
                logging.info('HW status has not change')
                continue
            message = parse_status(homework[0])
            if message != last_status:
                send_message(bot=bot, message=message)
                last_status = message
                timestamp = response.get('current_date', int(time.time()))
        except telegram.error.TelegramError as error:
            message = f'Failed to send message TG : {error}'
            last_status = message
            logging.error(message)
        except Exception as error:
            message = f'Critical error : {error}'
            logging.error(message)
            if message != last_status:
                with suppress(telegram.error.TelegramError):
                    send_message(bot=bot, message=message)
                    last_status = message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
