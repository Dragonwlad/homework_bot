# Описание проекта HomeworkBot

**HomeworkBot** - этот бот парсит статус домашнего задания на курсе Яндекс Практикума и в случае изменения статуса высылает его к вам в телеграм.
Особенности:
* Отправка только изменений, в случае перезапуска бота ничего лишнего не придет;
* Информирование о критических сбоях в работе программы в ваш телеграм;
* Бесперебойная работа;

## Стек
Python, Telegram API

## Разворачивание проекта.
- Клонируйте репозиторий.
- Установите виртуальное окружение.
- Установите зависимости (зависимости находятся в файле requirements.txt)

## Запуск проекта

Укажите необходимые для работы токены:

PRACTICUM_TOKEN = 'string' - укажите токен выданный вам в Яндекс Практикум

TELEGRAM_TOKEN = 'string' - укажите токен вашего TG бота

TELEGRAM_CHAT_ID =  'int' - укажите ID чата куда отправлять сообщения

свой ID можно узнать написав @userinfobot

## Автор:
[Владислав Кузнецов](https://github.com/Dragonwlad)
