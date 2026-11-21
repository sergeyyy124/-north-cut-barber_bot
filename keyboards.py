from datetime import date, timedelta
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from config import Service

# Краткие названия дней недели для кнопок выбора даты
WEEKDAYS_RU: dict[int, str] = {
    0: "Пн",
    1: "Вт",
    2: "Ср",
    3: "Чт",
    4: "Пт",
    5: "Сб",
    6: "Вс",
}


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню бота: Записаться, Услуги и цены, Контакты, Мои записи."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✂️ Записаться", callback_data="menu:book")],
            [InlineKeyboardButton(text="💈 Услуги и цены", callback_data="menu:services")],
            [InlineKeyboardButton(text="📅 Мои записи", callback_data="menu:my_bookings")],
            [InlineKeyboardButton(text="📍 Контакты", callback_data="menu:contacts")],
        ]
    )


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    """Кнопка возврата в главное меню."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏠 В главное меню", callback_data="menu:home")]
        ]
    )


def services_keyboard(services: list[Service], for_booking: bool = False) -> InlineKeyboardMarkup:
    """
    Клавиатура со списком услуг.
    При for_booking=True сразу ведёт к выбору даты под выбранную услугу.
    При for_booking=False (раздел «Услуги и цены») позволяет быстро записаться на выбранную услугу.
    """
    rows: list[list[InlineKeyboardButton]] = []
    for srv in services:
        label = f"{srv.title} — {srv.price} ₽ ({srv.duration_min} мин)"
        cb_data = f"pick_srv:{srv.id}" if for_booking else f"info_srv:{srv.id}"
        rows.append([InlineKeyboardButton(text=label, callback_data=cb_data)])

    if not for_booking:
        rows.append([InlineKeyboardButton(text="✂️ Перейти к записи", callback_data="menu:book")])
    rows.append([InlineKeyboardButton(text="🏠 В главное меню", callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def dates_keyboard(days_ahead: int = 7) -> InlineKeyboardMarkup:
    """Генерирует кнопки дат на ближайшие 7 дней (от сегодняшнего дня)."""
    today = date.today()
    rows: list[list[InlineKeyboardButton]] = []

    for offset in range(days_ahead):
        target_date = today + timedelta(days=offset)
        iso_date = target_date.isoformat()  # Формат YYYY-MM-DD удобен для БД и сортировки
        weekday = WEEKDAYS_RU[target_date.weekday()]
        human_date = target_date.strftime("%d.%m")
        prefix = "Сегодня" if offset == 0 else ("Завтра" if offset == 1 else weekday)
        btn_text = f"{prefix}, {human_date}"
        rows.append([InlineKeyboardButton(text=btn_text, callback_data=f"pick_date:{iso_date}")])

    rows.append([InlineKeyboardButton(text="⬅️ Назад к услугам", callback_data="menu:book")])
    rows.append([InlineKeyboardButton(text="🏠 В главное меню", callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def time_slots_keyboard(all_slots: list[str], booked_slots: set[str], iso_date: str) -> InlineKeyboardMarkup:
    """Строит кнопки только для ещё не занятых слотов времени на выбранную дату."""
    free_slots = [slot for slot in all_slots if slot not in booked_slots]
    rows: list[list[InlineKeyboardButton]] = []

    # Раскладываем кнопки по две в ряд для компактного вида
    for i in range(0, len(free_slots), 2):
        row = [
            InlineKeyboardButton(text=f"🕒 {slot}", callback_data=f"pick_time:{iso_date}:{slot}")
            for slot in free_slots[i : i + 2]
        ]
        rows.append(row)

    rows.append([InlineKeyboardButton(text="⬅️ Выбрать другую дату", callback_data="back:dates")])
    rows.append([InlineKeyboardButton(text="🏠 В главное меню", callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_booking_keyboard() -> InlineKeyboardMarkup:
    """Кнопки подтверждения или отмены оформления записи."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить запись", callback_data="confirm:yes")],
            [InlineKeyboardButton(text="❌ Отменить оформление", callback_data="menu:home")],
        ]
    )


def my_bookings_keyboard(bookings: list[dict]) -> InlineKeyboardMarkup:
    """Формирует кнопки отмены для каждой активной записи клиента."""
    rows: list[list[InlineKeyboardButton]] = []
    for item in bookings:
        btn_text = f"🗑 Отменить #{item['id']} ({item['booking_date']} {item['booking_time']})"
        rows.append([InlineKeyboardButton(text=btn_text, callback_data=f"cancel_bk:{item['id']}")])

    rows.append([InlineKeyboardButton(text="✂️ Новая запись", callback_data="menu:book")])
    rows.append([InlineKeyboardButton(text="🏠 В главное меню", callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
