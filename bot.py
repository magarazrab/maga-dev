import asyncio
import logging
import os
from pathlib import Path

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message,
    CallbackQuery,
    FSInputFile,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ChatMemberStatus
from dotenv import load_dotenv

import database as db

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
# Legacy single channel from .env (will be seeded into DB on first run)
LEGACY_CHANNEL_ID = os.getenv("CHANNEL_ID", "")
LEGACY_CHANNEL_LINK = os.getenv("CHANNEL_LINK", "")
YOUTUBE_CHANNEL = os.getenv("YOUTUBE_CHANNEL", "https://youtube.com")
SUPPORT_TELEGRAM = os.getenv("SUPPORT_TELEGRAM", "")
SUPPORT_INSTAGRAM = os.getenv("SUPPORT_INSTAGRAM", "")
SUPPORT_VK = os.getenv("SUPPORT_VK", "")

MATERIALS_DIR = Path(__file__).parent / "materials"

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
admin_router = Router()


# ==================== STATES ====================
class AdminStates(StatesGroup):
    waiting_lesson_day = State()
    waiting_lesson_title = State()
    waiting_lesson_url = State()
    waiting_broadcast = State()
    waiting_channel_id = State()
    waiting_channel_link = State()
    waiting_channel_title = State()


# ==================== KEYBOARDS ====================
async def sub_keyboard() -> InlineKeyboardMarkup:
    channels = await db.get_all_channels(active_only=True)
    buttons = []
    for ch in channels:
        title = ch.get("title") or "Канал"
        buttons.append([InlineKeyboardButton(text=f"📢 {title}", url=ch["channel_link"])])
    buttons.append([InlineKeyboardButton(text="✅ Я подписался", callback_data="check_sub")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def watch_keyboard(youtube_url: str, day: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Смотреть урок на YouTube", url=youtube_url)],
        [InlineKeyboardButton(text="✅ Готово — я посмотрел", callback_data=f"done_{day}")],
    ])


def social_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    if SUPPORT_TELEGRAM:
        buttons.append([InlineKeyboardButton(text="💬 Telegram", url=SUPPORT_TELEGRAM)])
    if SUPPORT_INSTAGRAM:
        buttons.append([InlineKeyboardButton(text="📸 Instagram", url=SUPPORT_INSTAGRAM)])
    if SUPPORT_VK:
        buttons.append([InlineKeyboardButton(text="🔵 VK", url=SUPPORT_VK)])
    if YOUTUBE_CHANNEL:
        buttons.append([InlineKeyboardButton(text="🎬 YouTube канал", url=YOUTUBE_CHANNEL)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📚 Список уроков"), KeyboardButton(text="➕ Добавить/Обновить урок")],
            [KeyboardButton(text="📢 Рассылка"), KeyboardButton(text="📊 Статистика")],
            [KeyboardButton(text="🔐 Управление ОП"), KeyboardButton(text="⚙️ Настройки")],
            [KeyboardButton(text="🔙 Выйти из админки")],
        ],
        resize_keyboard=True,
    )


def op_manage_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Список каналов", callback_data="op_list")],
        [InlineKeyboardButton(text="➕ Добавить канал", callback_data="op_add")],
        [InlineKeyboardButton(text="🗑 Удалить канал", callback_data="op_del")],
    ])


# ==================== HELPERS ====================
def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def check_subscription(user_id: int) -> bool:
    """Админы всегда проходят. Остальные должны быть подписаны на ВСЕ активные каналы."""
    if is_admin(user_id):
        return True

    channels = await db.get_all_channels(active_only=True)
    if not channels:
        return True  # нет каналов — ОП выключена

    for ch in channels:
        try:
            member = await bot.get_chat_member(ch["channel_id"], user_id)
            if member.status not in (
                ChatMemberStatus.MEMBER,
                ChatMemberStatus.ADMINISTRATOR,
                ChatMemberStatus.CREATOR,
            ):
                return False
        except Exception as e:
            logger.error(f"Sub check error for {ch['channel_id']}: {e}")
            return False
    return True


async def send_lesson(user_id: int, day: int):
    lesson = await db.get_lesson(day)
    if not lesson:
        await bot.send_message(user_id, f"❌ Урок {day} ещё не добавлен.")
        return

    if not lesson.get("is_active") or not lesson.get("youtube_url"):
        await bot.send_message(
            user_id,
            f"⏳ Урок {day} пока не опубликован.\nКак только админ добавит видео — ты сразу получишь уведомление!",
        )
        return

    title = lesson["title"]
    youtube_url = lesson["youtube_url"]
    material = lesson.get("material_file")

    if day == 1 and YOUTUBE_CHANNEL:
        await bot.send_message(
            user_id,
            f"🎬 <b>Наш YouTube канал:</b>\n{YOUTUBE_CHANNEL}\n\n"
            f"Подпишись, чтобы не пропустить новые уроки!",
            parse_mode="HTML",
        )

    if material:
        file_path = MATERIALS_DIR / material
        if file_path.exists() and file_path.stat().st_size > 0:
            await bot.send_document(
                user_id,
                FSInputFile(file_path),
                caption=f"📄 Материалы к уроку {day}: <b>{title}</b>",
                parse_mode="HTML",
            )
        elif file_path.exists():
            await bot.send_message(
                user_id,
                f"📄 Материалы к уроку {day}: <b>{title}</b>\n\n(файл пустой — материалы будут в видео)",
                parse_mode="HTML",
            )

    text = (
        f"🟢 <b>Урок {day}</b>\n"
        f"<b>{title}</b>\n\n"
        f"Нажми «Посмотреть урок», посмотри видео до конца,\n"
        f"затем вернись и нажми «Готово»."
    )
    await bot.send_message(
        user_id,
        text,
        reply_markup=watch_keyboard(youtube_url, day),
        parse_mode="HTML",
    )


async def notify_new_lesson(day: int):
    lesson = await db.get_lesson(day)
    if not lesson or not lesson.get("youtube_url"):
        return

    users = await db.get_all_users()
    text = (
        f"🚀 <b>Урок {day} начался!</b>\n\n"
        f"<b>{lesson['title']}</b>\n\n"
        f"Смотри видео и отмечай «Готово» после просмотра."
    )
    kb = watch_keyboard(lesson["youtube_url"], day)

    success = 0
    for u in users:
        if u["current_lesson"] >= day - 1 and (u["is_subscribed"] or is_admin(u["user_id"])):
            try:
                material = lesson.get("material_file")
                if material:
                    file_path = MATERIALS_DIR / material
                    if file_path.exists() and file_path.stat().st_size > 0:
                        await bot.send_document(
                            u["user_id"],
                            FSInputFile(file_path),
                            caption=f"📄 Материалы к уроку {day}",
                        )
                await bot.send_message(u["user_id"], text, reply_markup=kb, parse_mode="HTML")
                success += 1
                await asyncio.sleep(0.05)
            except Exception as e:
                logger.warning(f"Notify fail {u['user_id']}: {e}")
    logger.info(f"Notified {success} users about lesson {day}")


# ==================== USER HANDLERS ====================
@router.message(CommandStart())
async def cmd_start(message: Message):
    user = message.from_user
    await db.create_user(user.id, user.username, user.full_name)
    await db.update_user_activity(user.id)

    # Админы пропускают ОП
    if is_admin(user.id):
        await db.set_user_subscribed(user.id, True)
        u = await db.get_user(user.id)
        if u["current_lesson"] == 0:
            await message.answer(
                "👑 <b>Режим администратора</b>\n\n"
                "ОП для тебя отключена. Добро пожаловать на курс!",
                parse_mode="HTML",
            )
            await send_lesson(user.id, 1)
        else:
            current = u["current_lesson"]
            if current >= 6:
                await message.answer(
                    "🏆 Ты уже прошёл весь курс!\n\nПоддержи нас 👇",
                    reply_markup=social_keyboard(),
                )
            else:
                next_day = current + 1
                lesson = await db.get_lesson(next_day)
                if lesson and lesson.get("is_active") and lesson.get("youtube_url"):
                    await message.answer(f"С возвращением! Вот урок {next_day}:")
                    await send_lesson(user.id, next_day)
                else:
                    await message.answer(
                        f"Ты на уроке {current}.\n"
                        f"Следующий урок ({next_day}) ещё не опубликован."
                    )
        return

    # Обычные пользователи — проверка ОП
    subscribed = await check_subscription(user.id)
    if not subscribed:
        channels = await db.get_all_channels(active_only=True)
        if channels:
            await message.answer(
                "👋 Привет!\n\n"
                "Чтобы начать курс по программированию, "
                "обязательно подпишись на канал(ы) 👇",
                reply_markup=await sub_keyboard(),
            )
        else:
            # Нет каналов — сразу пускаем
            await db.set_user_subscribed(user.id, True)
            await message.answer("🎉 Добро пожаловать на курс!")
            await send_lesson(user.id, 1)
        return

    await db.set_user_subscribed(user.id, True)
    u = await db.get_user(user.id)

    if u["current_lesson"] == 0:
        await message.answer(
            "🎉 Отлично! Ты подписан.\n\n"
            "Добро пожаловать на <b>мини-курс по AI-разработке</b>!\n"
            "Курс длится 6 дней. Каждый день — новый урок.\n\n"
            "Сейчас начнём с первого урока 👇",
            parse_mode="HTML",
        )
        await send_lesson(user.id, 1)
    else:
        current = u["current_lesson"]
        if current >= 6:
            await message.answer(
                "🏆 Ты уже прошёл весь курс!\n\n"
                "Поддержи нас — подпишись на соцсети 👇",
                reply_markup=social_keyboard(),
            )
        else:
            next_day = current + 1
            lesson = await db.get_lesson(next_day)
            if lesson and lesson.get("is_active") and lesson.get("youtube_url"):
                await message.answer(f"С возвращением! Вот урок {next_day}:")
                await send_lesson(user.id, next_day)
            else:
                await message.answer(
                    f"Ты на уроке {current}.\n"
                    f"Следующий урок ({next_day}) ещё не опубликован.\n"
                    f"Как только админ добавит — ты получишь уведомление 🔔"
                )


@router.callback_query(F.data == "check_sub")
async def check_sub_callback(callback: CallbackQuery):
    user_id = callback.from_user.id

    if is_admin(user_id):
        await db.set_user_subscribed(user_id, True)
        await callback.message.edit_text("✅ Админ — проверка пропущена.")
        await callback.answer()
        await send_lesson(user_id, 1)
        return

    subscribed = await check_subscription(user_id)
    if not subscribed:
        await callback.answer(
            "❌ Ты ещё не подписан на все каналы. Подпишись и нажми снова!",
            show_alert=True,
        )
        return

    await db.set_user_subscribed(user_id, True)
    await callback.message.edit_text("✅ Подписка подтверждена!")
    await callback.answer()

    u = await db.get_user(user_id)
    if not u or u["current_lesson"] == 0:
        await bot.send_message(
            user_id,
            "🎉 Отлично! Добро пожаловать на курс.\n\nНачинаем первый урок 👇",
        )
        await send_lesson(user_id, 1)
    else:
        await bot.send_message(user_id, "С возвращением! Используй /start")


@router.callback_query(F.data.startswith("watch_"))
async def watch_lesson(callback: CallbackQuery):
    day = int(callback.data.split("_")[1])
    lesson = await db.get_lesson(day)
    if not lesson or not lesson.get("youtube_url"):
        await callback.answer("Ссылка на урок ещё не добавлена", show_alert=True)
        return
    await callback.answer()


@router.callback_query(F.data.startswith("done_"))
async def done_lesson(callback: CallbackQuery):
    user_id = callback.from_user.id
    day = int(callback.data.split("_")[1])
    u = await db.get_user(user_id)
    if not u:
        await callback.answer("Сначала нажми /start", show_alert=True)
        return

    if day > u["current_lesson"] + 1:
        await callback.answer("Сначала пройди предыдущие уроки!", show_alert=True)
        return

    await db.set_user_lesson(user_id, day)
    await callback.answer("✅ Отлично!")

    if day >= 6:
        await callback.message.edit_text(
            "🎉🎉🎉 <b>Поздравляю!</b>\n\n"
            "Ты прошёл весь 6-дневный курс по AI-разработке!\n\n"
            "Теперь у тебя есть реальный проект и понимание, "
            "как создавать приложения с помощью ИИ.\n\n"
            "Поддержи нас — подпишись на наши соцсети 👇",
            parse_mode="HTML",
            reply_markup=social_keyboard(),
        )
    else:
        await callback.message.edit_text(
            f"✅ <b>Урок {day} пройден!</b>\n\n"
            f"Хорошо, завтра ждём тебя на <b>{day + 1}</b> уроке.\n\n"
            f"🔁 <b>Обязательно повтори материал тщательно</b> "
            f"для большего результата!\n\n"
            f"Как только следующий урок будет опубликован — "
            f"ты получишь уведомление прямо сюда 🔔",
            parse_mode="HTML",
        )


# ==================== ADMIN ====================
@admin_router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        "🛠 <b>Админ-панель</b>\n\nВыбери действие:",
        reply_markup=admin_keyboard(),
        parse_mode="HTML",
    )


@admin_router.message(F.text == "🔙 Выйти из админки")
async def admin_exit(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("Вышел из админки.", reply_markup=ReplyKeyboardRemove())


@admin_router.message(F.text == "📚 Список уроков")
async def admin_list_lessons(message: Message):
    if not is_admin(message.from_user.id):
        return
    lessons = await db.get_all_lessons()
    text = "📚 <b>Уроки курса:</b>\n\n"
    for les in lessons:
        status = "✅ Активен" if les["is_active"] and les["youtube_url"] else "⏳ Не опубликован"
        url = les["youtube_url"] or "—"
        text += (
            f"<b>День {les['day']}</b>: {les['title']}\n"
            f"   {status}\n"
            f"   🔗 {url}\n"
            f"   📄 {les['material_file']}\n\n"
        )
    await message.answer(text, parse_mode="HTML", disable_web_page_preview=True)


@admin_router.message(F.text == "➕ Добавить/Обновить урок")
async def admin_add_lesson_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        "Введи номер дня (1-6), который хочешь обновить/активировать:\n\n"
        "Пример: <code>2</code>",
        parse_mode="HTML",
    )
    await state.set_state(AdminStates.waiting_lesson_day)


@admin_router.message(AdminStates.waiting_lesson_day)
async def admin_lesson_day(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        day = int(message.text.strip())
        if day < 1 or day > 6:
            raise ValueError
    except ValueError:
        await message.answer("Введи число от 1 до 6")
        return

    await state.update_data(day=day)
    lesson = await db.get_lesson(day)
    current_title = lesson["title"] if lesson else ""
    await message.answer(
        f"День {day}. Текущее название: <b>{current_title}</b>\n\n"
        f"Введи новое название урока (или отправь «-» чтобы оставить):\n"
        f"Пример: <code>Урок 2 — Добавляем жизнь</code>",
        parse_mode="HTML",
    )
    await state.set_state(AdminStates.waiting_lesson_title)


@admin_router.message(AdminStates.waiting_lesson_title)
async def admin_lesson_title(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    title = message.text.strip()
    if title == "-":
        title = None
    await state.update_data(title=title)
    await message.answer(
        "Теперь отправь <b>ссылку на YouTube видео</b> этого урока:\n\n"
        "Пример: <code>https://youtu.be/xxxxx</code>\n\n"
        "Или «-» чтобы не менять ссылку.",
        parse_mode="HTML",
    )
    await state.set_state(AdminStates.waiting_lesson_url)


@admin_router.message(AdminStates.waiting_lesson_url)
async def admin_lesson_url(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    day = data["day"]
    title = data.get("title")
    url = message.text.strip()
    if url == "-":
        url = None

    is_active = 1 if (url and url.startswith("http")) else None
    if url and not url.startswith("http"):
        await message.answer("Ссылка должна начинаться с http. Попробуй снова или «-»")
        return

    await db.update_lesson(day, title=title, youtube_url=url, is_active=is_active)
    await state.clear()

    lesson = await db.get_lesson(day)
    await message.answer(
        f"✅ Урок {day} обновлён!\n\n"
        f"<b>{lesson['title']}</b>\n"
        f"🔗 {lesson['youtube_url'] or 'нет'}\n"
        f"Статус: {'✅ Активен' if lesson['is_active'] else '⏳ Неактивен'}\n\n"
        f"Отправить уведомление всем пользователям?",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📢 Да, уведомить всех", callback_data=f"notify_{day}"),
                InlineKeyboardButton(text="Нет", callback_data="notify_no"),
            ]
        ]),
    )


@admin_router.callback_query(F.data.startswith("notify_"))
async def admin_notify(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    if callback.data == "notify_no":
        await callback.message.edit_text("Ок, уведомление не отправлено.")
        await callback.answer()
        return

    day = int(callback.data.split("_")[1])
    await callback.message.edit_text(f"⏳ Рассылаю уведомление об уроке {day}...")
    await callback.answer()
    await notify_new_lesson(day)
    await callback.message.answer(f"✅ Уведомления об уроке {day} отправлены!")


@admin_router.message(F.text == "📢 Рассылка")
async def admin_broadcast_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await message.answer("Отправь текст рассылки (можно с HTML-разметкой):")
    await state.set_state(AdminStates.waiting_broadcast)


@admin_router.message(AdminStates.waiting_broadcast)
async def admin_broadcast_send(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    text = message.text
    users = await db.get_all_users()
    success = 0
    fail = 0
    await message.answer(f"⏳ Рассылка на {len(users)} пользователей...")
    for u in users:
        try:
            await bot.send_message(u["user_id"], text, parse_mode="HTML")
            success += 1
            await asyncio.sleep(0.05)
        except Exception:
            fail += 1
    await state.clear()
    await message.answer(f"✅ Готово!\nУспешно: {success}\nОшибок: {fail}")


@admin_router.message(F.text == "📊 Статистика")
async def admin_stats(message: Message):
    if not is_admin(message.from_user.id):
        return
    users = await db.get_all_users()
    total = len(users)
    by_lesson = {}
    for u in users:
        les = u["current_lesson"]
        by_lesson[les] = by_lesson.get(les, 0) + 1

    text = f"📊 <b>Статистика</b>\n\nВсего пользователей: <b>{total}</b>\n\n"
    text += "Прогресс:\n"
    for i in range(0, 7):
        cnt = by_lesson.get(i, 0)
        if i == 0:
            text += f"  Не начали: {cnt}\n"
        elif i == 6:
            text += f"  Завершили курс: {cnt}\n"
        else:
            text += f"  После урока {i}: {cnt}\n"
    await message.answer(text, parse_mode="HTML")


@admin_router.message(F.text == "⚙️ Настройки")
async def admin_settings(message: Message):
    if not is_admin(message.from_user.id):
        return
    channels = await db.get_all_channels(active_only=False)
    ch_text = "\n".join(
        f"  • {c['title']} → <code>{c['channel_id']}</code>" for c in channels
    ) or "  (нет каналов)"
    text = (
        "⚙️ <b>Текущие настройки</b>\n\n"
        f"<b>Админы:</b> {ADMIN_IDS}\n\n"
        f"<b>Каналы ОП:</b>\n{ch_text}\n\n"
        f"YouTube: {YOUTUBE_CHANNEL}\n\n"
        "Управление каналами — кнопка «🔐 Управление ОП»"
    )
    await message.answer(text, parse_mode="HTML", disable_web_page_preview=True)


# ==================== ОП MANAGEMENT ====================
@admin_router.message(F.text == "🔐 Управление ОП")
async def admin_op_menu(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        "🔐 <b>Управление обязательной подпиской</b>\n\n"
        "Можно добавить несколько каналов.\n"
        "Пользователь должен быть подписан на <b>все</b> активные каналы.\n"
        "Админы проверку пропускают.",
        reply_markup=op_manage_keyboard(),
        parse_mode="HTML",
    )


@admin_router.callback_query(F.data == "op_list")
async def op_list(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    channels = await db.get_all_channels(active_only=False)
    if not channels:
        await callback.message.edit_text("📋 Каналов пока нет.\nДобавь первый через «➕ Добавить канал».")
        await callback.answer()
        return

    text = "📋 <b>Каналы ОП:</b>\n\n"
    for c in channels:
        status = "✅" if c["is_active"] else "❌"
        text += (
            f"{status} <b>{c['title']}</b>\n"
            f"   ID: <code>{c['channel_id']}</code>\n"
            f"   Ссылка: {c['channel_link']}\n"
            f"   DB id: {c['id']}\n\n"
        )
    await callback.message.edit_text(text, parse_mode="HTML", disable_web_page_preview=True)
    await callback.answer()


@admin_router.callback_query(F.data == "op_add")
async def op_add_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await callback.message.edit_text(
        "➕ <b>Добавление канала</b>\n\n"
        "Отправь <b>ID канала</b> или @username:\n\n"
        "Примеры:\n"
        "• <code>@my_channel</code>\n"
        "• <code>-1001234567890</code>\n\n"
        "⚠️ Бот должен быть <b>админом</b> в этом канале!",
        parse_mode="HTML",
    )
    await state.set_state(AdminStates.waiting_channel_id)
    await callback.answer()


@admin_router.message(AdminStates.waiting_channel_id)
async def op_add_channel_id(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    channel_id = message.text.strip()
    if not channel_id:
        await message.answer("ID не может быть пустым")
        return
    await state.update_data(channel_id=channel_id)
    await message.answer(
        "Теперь отправь <b>ссылку</b> на канал (для кнопки):\n\n"
        "Пример: <code>https://t.me/my_channel</code>",
        parse_mode="HTML",
    )
    await state.set_state(AdminStates.waiting_channel_link)


@admin_router.message(AdminStates.waiting_channel_link)
async def op_add_channel_link(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    link = message.text.strip()
    if not link.startswith("http"):
        await message.answer("Ссылка должна начинаться с https://")
        return
    await state.update_data(channel_link=link)
    await message.answer(
        "Название канала (будет на кнопке):\n\n"
        "Пример: <code>Основной канал</code>\n"
        "Или отправь «-» — возьмём ID",
        parse_mode="HTML",
    )
    await state.set_state(AdminStates.waiting_channel_title)


@admin_router.message(AdminStates.waiting_channel_title)
async def op_add_channel_title(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    title = message.text.strip()
    if title == "-":
        title = data["channel_id"]

    ok = await db.add_channel(
        channel_id=data["channel_id"],
        channel_link=data["channel_link"],
        title=title,
    )
    await state.clear()
    if ok:
        await message.answer(
            f"✅ Канал добавлен!\n\n"
            f"<b>{title}</b>\n"
            f"ID: <code>{data['channel_id']}</code>\n"
            f"Ссылка: {data['channel_link']}",
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
    else:
        await message.answer("❌ Такой channel_id уже есть в базе.")


@admin_router.callback_query(F.data == "op_del")
async def op_del_start(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    channels = await db.get_all_channels(active_only=False)
    if not channels:
        await callback.answer("Нет каналов для удаления", show_alert=True)
        return

    buttons = []
    for c in channels:
        buttons.append([
            InlineKeyboardButton(
                text=f"🗑 {c['title']}",
                callback_data=f"op_del_{c['id']}",
            )
        ])
    buttons.append([InlineKeyboardButton(text="« Назад", callback_data="op_back")])
    await callback.message.edit_text(
        "Выбери канал для удаления:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await callback.answer()


@admin_router.callback_query(F.data.startswith("op_del_"))
async def op_del_confirm(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    db_id = int(callback.data.split("_")[2])
    ch = await db.get_channel_by_id(db_id)
    if not ch:
        await callback.answer("Канал не найден", show_alert=True)
        return
    await db.remove_channel_by_db_id(db_id)
    await callback.message.edit_text(f"✅ Канал <b>{ch['title']}</b> удалён.", parse_mode="HTML")
    await callback.answer()


@admin_router.callback_query(F.data == "op_back")
async def op_back(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    await callback.message.edit_text(
        "🔐 <b>Управление обязательной подпиской</b>",
        reply_markup=op_manage_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


# ==================== FALLBACK ====================
@router.message()
async def fallback(message: Message):
    await message.answer("Нажми /start чтобы начать или продолжить курс.")


# ==================== STARTUP ====================
async def seed_legacy_channel():
    """Если в .env указан CHANNEL_ID — добавить его в базу (один раз)."""
    if not LEGACY_CHANNEL_ID:
        return
    channels = await db.get_all_channels(active_only=False)
    if channels:
        return
    link = LEGACY_CHANNEL_LINK or f"https://t.me/{LEGACY_CHANNEL_ID.lstrip('@')}"
    await db.add_channel(
        channel_id=LEGACY_CHANNEL_ID,
        channel_link=link,
        title="Основной канал",
    )
    logger.info(f"Seeded legacy channel: {LEGACY_CHANNEL_ID}")


async def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN not set!")
    await db.init_db()
    await seed_legacy_channel()
    dp.include_router(admin_router)
    dp.include_router(router)
    logger.info("Bot starting...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
