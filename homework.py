import logging

import os
import sys
import requests
import time

from telebot import TeleBot
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

TIMEDELTA = 2678400  # 60 дней в секундах


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.DEBUG,
    stream=sys.stdout
)


def check_tokens():
    """Проверяет доступность переменных окружения."""
    if not PRACTICUM_TOKEN:
        logging.critical(
            'Отсутствует обязательная переменная окружения: "PRACTICUM_TOKEN"')
        raise VariableMissingException('PRACTICUM_TOKEN отсутствует')
    if not TELEGRAM_TOKEN:
        logging.critical(
            'Отсутствует обязательная переменная окружения: "TELEGRAM_TOKEN"')
        raise VariableMissingException('TELEGRAM_TOKEN отсутствует')
    if not TELEGRAM_CHAT_ID:
        logging.critical(
            'Отсутствует обязательная переменная окружения:"TELEGRAM_CHAT_ID"'
        )
        raise VariableMissingException('TELEGRAM_CHAT_ID отсутствует')
    logging.info(
        """Все переменные окружения на месте, создаем запрос!"""
    )


def send_message(bot, message):
    """Отправляет сообщение в Telegram-чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug('Сообщение отправлено')
    except Exception as error:
        print(error)
        logging.error('Ошибка отправки сообщения {error}')


def get_api_answer(timestamp):
    """делает запрос к единственному эндпоинту API-сервиса.
    В качестве параметра в функцию передаётся временная метка
    """
    # timestamp = int(timestamp - TIMEDELTA)
    payload = {'from_date': timestamp}

    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
        if response.status_code == 200:
            logging.debug('Запрос выполнен успешно!')
            response = response.json()
            return response
        else:
            raise RequestErrorException('Код не 200')
    except requests.RequestException as e:
        print(e)
        raise RequestException('Ошибка запроса')


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    if not isinstance(response, dict):
        raise TypeError('Это не словарь')
    elif 'homeworks' in response:
        if isinstance(response['homeworks'], list):
            return response['homeworks']
        raise TypeError('Это не список')
    raise KeyError('такого ключа нет')


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
    logging.info(f'Статус проверки работы {homework_name}: {verdict}')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    response = get_api_answer(timestamp)
    homeworks = check_response(response)
    if homeworks:
        for i in range(len(homeworks)):
            homework = homeworks[i]
            message = parse_status(homework)
            send_message(bot, message)
    else:
        logging.error('Структура данных неверная')
        message = 'Ошибка response. Неверная структура данных'
        send_message(bot, message)

    while True:
        try:
            bot.polling()
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(f'Сбой в работе программы: {error}')
            send_message(bot, message)
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
