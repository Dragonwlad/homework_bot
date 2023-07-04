from contextlib import suppress
from http import HTTPStatus
import logging
import os
import sys
import time


from dotenv import load_dotenv
import requests
import telegram

from exception import TokensNotAvailable, UnexpectedResponseStatus

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter(
    '%(asctime)s, %(lineno)d, %(levelname)s, %(message)s, %(funcName)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


logger.debug('programma start')

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
    missing_tokens = []
    missing_tokens = [token for token in tokens if not globals()[token]]
    if missing_tokens:
        message = (f'{",".join(missing_tokens)} is not available,'
                   'programm stoped')
        logger.critical(message)
        raise TokensNotAvailable(message)
    logger.debug('Global variables are available')


def send_message(bot, message):
    """Send message about change status in HW."""
    logger.info('try sent message about change status in HW.')
    bot.send_message(TELEGRAM_CHAT_ID, message)
    logger.debug('message sent successfully')


def get_api_answer(timestamp):
    """Request to api YP for the status of work."""
    logger.info('start request to api YP for the status of work')
    payload = {'from_date': timestamp}
    try:
        api_answer = requests.get(ENDPOINT,
                                  headers=HEADERS,
                                  params=payload)
    except requests.RequestException as error:
        raise ConnectionError('Response from YP not received, '
                              f'{error}') from error
    # Добавил, но не увидел разницу в терминале что с что без выводит
    # одинаковые ошибки с ссылкой на 141 строчку

    if api_answer.status_code != HTTPStatus.OK:
        raise UnexpectedResponseStatus('Unexpected response status'
                                       f'code from the server: {api_answer}'
                                       f', url:{HEADERS}, payload:{payload}')
    logger.debug(f'Answer received:{api_answer}')
    return api_answer.json()


def check_response(response):
    """Checking variables from answer YP."""
    logger.info('start check_response ')
    if not isinstance(response, dict):
        raise TypeError('uncorrect answer from server')
    if 'homeworks' not in response:
        raise KeyError('no key homeworks')
    if not isinstance(response['homeworks'], list):
        raise TypeError('uncorrect answer from server')
    logger.debug('check_response done')
    return response['homeworks']


def parse_status(homework):
    """Check change HW."""
    logger.info('start parse_status ')

    for key in ('homework_name', 'status'):
        if key not in homework.keys():
            raise KeyError(f'{key} not found in {homework.keys()}')

    hw_status = homework['status']
    if hw_status not in HOMEWORK_VERDICTS.keys():
        raise ValueError(f'{hw_status} not found'
                         f'in {HOMEWORK_VERDICTS.keys()}')

    logger.info('parse_status done')
    return (f'Изменился статус проверки работы "{homework["homework_name"]}".'
            f' {HOMEWORK_VERDICTS[hw_status]}')


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    logger.debug(f'HW bot started, timestamp = {timestamp}')
    last_status = ''
    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            if not homework:
                logger.info('HW status has not change')
                continue
            message = parse_status(homework[0])
            if message != last_status:
                send_message(bot=bot, message=message)
                last_status = message
                timestamp = response.get('current_date', int(time.time()))
            else:
                logger.info('HW status has not change')
            # получается логируем тут и в 130 строке, как будто
            # что-то из этого избыточно
        except telegram.error.TelegramError as error:
            logger.error(f'Failed to send message TG : {error}')
        except Exception as error:
            message = f'Critical error : {error}'
            logger.error(message)
            if message != last_status:
                with suppress(telegram.error.TelegramError):
                    send_message(bot=bot, message=message)
                last_status = message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
