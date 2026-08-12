# Telegram-бот курса по программированию (6 дней)

Бот для мини-курса AI-разработки.

## Что умеет

1. **Обязательная подписка** на канал (ОП)
2. После подписки — старт 1-го урока:
   - ссылка на YouTube-канал
   - файл «Старт»
   - кнопка «Посмотреть урок» → твоё видео
   - кнопка «Готово»
3. После «Готово»:
   > Хорошо, завтра ждём тебя на втором уроке.  
   > Обязательно повтори материал тщательно для большего результата!
4. Когда админ через админку добавляет новый урок и ссылку — **всем подходящим пользователям** приходит уведомление + кнопка с видео.
5. Так 6 дней.
6. После 6-го урока — поздравление + кнопки соцсетей.
7. Полная админ-панель.

## Быстрый старт локально

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Отредактируй .env
python bot.py
```

## Переменные окружения (.env)

```env
BOT_TOKEN=123456:ABC-DEF...
ADMIN_IDS=123456789
CHANNEL_ID=@your_channel          # или -100xxxxxxxxxx
CHANNEL_LINK=https://t.me/your_channel
YOUTUBE_CHANNEL=https://www.youtube.com/@yourchannel
SUPPORT_TELEGRAM=https://t.me/your
SUPPORT_INSTAGRAM=https://instagram.com/your
SUPPORT_VK=https://vk.com/your
```

## Как пользоваться админкой

1. Напиши боту `/admin`
2. **Список уроков** — посмотреть статусы
3. **Добавить/Обновить урок**:
   - введи номер дня (1–6)
   - название (или `-`)
   - ссылку на YouTube
   - подтверди рассылку уведомлений
4. **Рассылка** — произвольное сообщение всем
5. **Статистика** — сколько людей на каком уроке

## Деплой на Railway (24/7)

### 1. GitHub

```bash
cd telegram_course_bot
git init
git add .
git commit -m "Initial bot"
# Создай репозиторий на GitHub и:
git remote add origin https://github.com/ТВОЙ_ЮЗЕР/telegram-course-bot.git
git branch -M main
git push -u origin main
```

### 2. Railway

1. Зайди на [railway.app](https://railway.app) → New Project → Deploy from GitHub
2. Выбери репозиторий
3. Railway сам определит Python
4. Добавь **Variables** (те же, что в `.env`):
   - `BOT_TOKEN`
   - `ADMIN_IDS`
   - `CHANNEL_ID`
   - `CHANNEL_LINK`
   - `YOUTUBE_CHANNEL`
   - `SUPPORT_TELEGRAM` / `SUPPORT_INSTAGRAM` / `SUPPORT_VK`
5. (Опционально) Добавь Volume на `/app/data` чтобы база не терялась при редеплое
6. Deploy

### 3. Важно для бота

- В BotFather выключи Privacy Mode **или** добавь бота админом в канал (чтобы проверять подписку)
- Бот должен быть **админом** канала (для проверки ОП)

## Структура материалов

Файлы в папке `materials/`:

| День | Файл          | Содержание          |
|------|---------------|---------------------|
| 1    | Старт.txt     | (пока пустой)       |
| 2    | урок2.txt     | Урок 2              |
| 3    | урок3.txt     | Урок 3              |
| 4    | урок4.txt     | Урок 4              |
| 5    | Финал.txt     | Урок 5              |
| 6    | урок5.txt     | Урок 6 (финал)      |

Можешь заменить содержимое файлов — бот будет отправлять актуальные версии.

## Команды бота

- `/start` — начать / продолжить курс
- `/admin` — админ-панель (только для ADMIN_IDS)
EOF