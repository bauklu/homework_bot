import logging
import sys
import os
import requests
import time

from http import HTTPStatus
from telebot import TeleBot
from telebot.apihelper import ApiException
from dotenv import load_dotenv

from exceptions import (VariableMissingException, RequestErrorException,
                        RequestException)

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')


RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

TIMEDELTA = 60 * 24 * 60 * 60


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяет доступность переменных окружения."""
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        logging.info(
            'Все переменные окружения на месте, создаем запрос!')
    else:
        if not PRACTICUM_TOKEN:
            logging.critical(
                'Отсутствует обязательная переменная: "PRACTICUM_TOKEN"')
        elif not TELEGRAM_TOKEN:
            logging.critical(
                'Отсутствует обязательная переменная:"TELEGRAM_TOKEN"'
            )
        else:
            logging.critical(
                'Отсутствует обязательная переменная:"TELEGRAM_CHAT_ID"'
            )
        raise VariableMissingException('Переменная окружения отсутствует')


def send_message(bot, message):
    """Отправляет сообщение в Telegram-чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug('Сообщение отправлено')
    except ApiException:
        logging.error('Ошибка отправки сообщения')


def get_api_answer(timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса.
    В качестве параметра в функцию передаётся временная метка.
    """
    payload = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
    except requests.RequestException:
        raise RequestException('Ошибка запроса')
    if response.status_code == HTTPStatus.OK:
        response = response.json()
        return response
    else:
        raise RequestErrorException('Код не 200')


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    if not isinstance(response, dict):
        raise TypeError(
            'Структура полученных данных не соответствует документации'
        )
    elif 'homeworks' in response:
        if isinstance(response['homeworks'], list):
            return response['homeworks']
        raise TypeError(
            'Под ключом "homeworks" данные не в виде списка'
        )
    raise KeyError('Нет ключа "homeworks"')


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе её статус."""
    if 'homework_name' not in homework:
        raise KeyError('Нет ключа "homework_name"')
    elif 'status' not in homework:
        raise KeyError('Нет статуса домашнй работы')
    elif homework['status'] not in HOMEWORK_VERDICTS:
        raise ValueError('неизвестный статус')
    homework_status = homework['status']
    homework_name = homework['homework_name']
    verdict = HOMEWORK_VERDICTS.get(homework_status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    logging.basicConfig(
        format='%(asctime)s - %(levelname)s - %(message)s',
        level=logging.DEBUG,
        stream=sys.stdout
    )
    logger = logging.getLogger(__name__)

    check_tokens()
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    failure_counter = ''

    while True:
        try:
            response = get_api_answer(timestamp)
            logger.debug('Запрос выполнен успешно!')
            homeworks = check_response(response)
            if homeworks:
                for homework in homeworks:
                    message = parse_status(homework)
                    logger.info('Изменился статус проверки работы')
                    send_message(bot, message)
            else:
                logger.error('Изменений нет')
                message = 'Список домашних работ пуст'
                send_message(bot, message)
            timestamp = response['current_date']
        except Exception as error:
            if not failure_counter:
                message = f'Сбой в работе программы: {error}'
                send_message(bot, message)
            else:
                logger.error('Все еще сбой соединения')
            failure_counter = error
            logger.error({error})
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
