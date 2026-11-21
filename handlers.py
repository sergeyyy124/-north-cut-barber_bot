from aiogram import Bot, F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from config import DB_PATH, MASTER_CHAT_ID, SERVICES, SERVICES_BY_ID, SHOP_CONTACTS, TIME_SLOTS
from database import cancel_booking, create_booking, get_booked_times, get_user_bookings
from keyboards import (
    back_to_menu_keyboard,
    confirm_booking_keyboard,
    dates_keyboard,
    main_menu_keyboard,
    my_bookings_keyboard,
    services_keyboard,
    time_slots_keyboard,
)

router = Router()


class BookingStates(StatesGroup):
    """Шаги пошагового сценария записи клиента."""
    choosing_service = State()
    choosing_date = State()
    choosing_time = State()
    entering_name = State()
    confirming = State()


def _welcome_text(user_name: str | None) -> str:
    """Формирует текст приветствия и главного меню."""
    name = user_name or "друг"
    return (
        f"Привет, <b>{name}</b>! Добро пожаловать в <b>NORTH CUT</b>.\n"
        "Помогу подобрать услугу, выбрать свободное время и оформить запись.\n\n"
        "Выберите раздел в меню:"
    )


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    """Сбрасывает текущее состояние оформления и открывает главное меню."""
    await state.clear()
    full_name = message.from_user.full_name if message.from_user else None
    await message.answer(
        _welcome_text(full_name),
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(),
    )


@router.callback_query(F.data == "menu:home")
async def cb_home(callback: CallbackQuery, state: FSMContext) -> None:
    """Возвращает в главное меню и очищает незавершённую запись."""
    await state.clear()
    await callback.answer()
    full_name = callback.from_user.full_name if callback.from_user else None
    await callback.message.answer(
        _welcome_text(full_name),
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(),
    )


@router.callback_query(F.data == "menu:services")
async def cb_services(callback: CallbackQuery) -> None:
    """Показывает прайс-лист из 4 услуг с ценами и длительностью."""
    await callback.answer()
    lines = ["💈 <b>Услуги и цены в NORTH CUT:</b>\n"]
    for srv in SERVICES:
        lines.append(f"• <b>{srv.title}</b> — {srv.price} ₽ <i>({srv.duration_min} мин)</i>")
    lines.append("\nНажмите на услугу, чтобы сразу перейти к записи:")

    await callback.message.answer(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=services_keyboard(SERVICES, for_booking=False),
    )


@router.callback_query(F.data.startswith("info_srv:"))
async def cb_service_quick_book(callback: CallbackQuery, state: FSMContext) -> None:
    """Запускает выбор даты сразу для услуги, выбранной из прайс-листа."""
    service_id = callback.data.split(":", 1)[1]
    service = SERVICES_BY_ID.get(service_id)
    if not service:
        await callback.answer("Услуга не найдена", show_alert=True)
        return

    await state.update_data(service_id=service.id)
    await state.set_state(BookingStates.choosing_date)
    await callback.answer()
    await callback.message.answer(
        f"Выбрана услуга: <b>{service.title}</b> ({service.price} ₽)\n"
        "Шаг 2 из 4: выберите удобный день (ближайшие 7 дней):",
        parse_mode="HTML",
        reply_markup=dates_keyboard(days_ahead=7),
    )


@router.callback_query(F.data == "menu:contacts")
async def cb_contacts(callback: CallbackQuery) -> None:
    """Показывает контакты, адрес и график работы барбершопа."""
    await callback.answer()
    await callback.message.answer(
        SHOP_CONTACTS,
        parse_mode="HTML",
        reply_markup=back_to_menu_keyboard(),
    )


@router.callback_query(F.data == "menu:book")
async def cb_start_booking(callback: CallbackQuery, state: FSMContext) -> None:
    """Шаг 1: переводит в состояние выбора услуги."""
    await state.clear()
    await state.set_state(BookingStates.choosing_service)
    await callback.answer()
    await callback.message.answer(
        "✂️ <b>Запись в барбершоп</b>\n\n"
        "Шаг 1 из 4: выберите услугу:",
        parse_mode="HTML",
        reply_markup=services_keyboard(SERVICES, for_booking=True),
    )


@router.callback_query(BookingStates.choosing_service, F.data.startswith("pick_srv:"))
async def cb_pick_service(callback: CallbackQuery, state: FSMContext) -> None:
    """Сохраняет услугу в памяти FSM и открывает выбор даты."""
    service_id = callback.data.split(":", 1)[1]
    service = SERVICES_BY_ID.get(service_id)
    if not service:
        await callback.answer("Услуга не найдена", show_alert=True)
        return

    await state.update_data(service_id=service.id)
    await state.set_state(BookingStates.choosing_date)
    await callback.answer()
    await callback.message.answer(
        f"Услуга: <b>{service.title}</b> ({service.price} ₽)\n\n"
        "Шаг 2 из 4: выберите дату (ближайшие 7 дней):",
        parse_mode="HTML",
        reply_markup=dates_keyboard(days_ahead=7),
    )


@router.callback_query(F.data == "back:dates")
async def cb_back_to_dates(callback: CallbackQuery, state: FSMContext) -> None:
    """Возвращает к выбору даты."""
    await state.set_state(BookingStates.choosing_date)
    await callback.answer()
    await callback.message.answer(
        "Шаг 2 из 4: выберите дату:",
        parse_mode="HTML",
        reply_markup=dates_keyboard(days_ahead=7),
    )


@router.callback_query(BookingStates.choosing_date, F.data.startswith("pick_date:"))
async def cb_pick_date(callback: CallbackQuery, state: FSMContext) -> None:
    """Проверяет занятые слоты в SQLite и показывает только свободное время."""
    iso_date = callback.data.split(":", 1)[1]
    booked_slots = get_booked_times(DB_PATH, iso_date)
    free_slots = [slot for slot in TIME_SLOTS if slot not in booked_slots]

    await state.update_data(booking_date=iso_date)
    await state.set_state(BookingStates.choosing_time)
    await callback.answer()

    if not free_slots:
        await callback.message.answer(
            f"На дату <b>{iso_date}</b> свободных окон не осталось. Выберите другой день:",
            parse_mode="HTML",
            reply_markup=dates_keyboard(days_ahead=7),
        )
        return

    await callback.message.answer(
        f"Дата: <b>{iso_date}</b>\n\n"
        "Шаг 3 из 4: выберите свободное время:",
        parse_mode="HTML",
        reply_markup=time_slots_keyboard(TIME_SLOTS, booked_slots, iso_date),
    )


@router.callback_query(BookingStates.choosing_time, F.data.startswith("pick_time:"))
async def cb_pick_time(callback: CallbackQuery, state: FSMContext) -> None:
    """Сохраняет выбранное время и запрашивает имя клиента."""
    _, iso_date, slot_time = callback.data.split(":", 2)

    # Дополнительная проверка на случай, если слот заняли пока клиент выбирал
    if slot_time in get_booked_times(DB_PATH, iso_date):
        await callback.answer("Это время уже заняли, выберите другое.", show_alert=True)
        booked_slots = get_booked_times(DB_PATH, iso_date)
        await callback.message.answer(
            f"Обновили свободные окна на <b>{iso_date}</b>:",
            parse_mode="HTML",
            reply_markup=time_slots_keyboard(TIME_SLOTS, booked_slots, iso_date),
        )
        return

    await state.update_data(booking_date=iso_date, booking_time=slot_time)
    await state.set_state(BookingStates.entering_name)
    await callback.answer()
    await callback.message.answer(
        f"Время: <b>{iso_date}</b> в <b>{slot_time}</b>\n\n"
        "Шаг 4 из 4: напишите ваше имя:",
        parse_mode="HTML",
        reply_markup=back_to_menu_keyboard(),
    )


@router.message(BookingStates.entering_name, F.text)
async def msg_enter_name(message: Message, state: FSMContext) -> None:
    """Проверяет имя и выводит сводку для подтверждения записи."""
    client_name = message.text.strip()
    if len(client_name) < 2 or len(client_name) > 60:
        await message.answer("Введите имя длиной от 2 до 60 символов.")
        return

    data = await state.get_data()
    service = SERVICES_BY_ID.get(data.get("service_id", ""))
    if not service:
        await state.clear()
        await message.answer("Сессия сбросилась. Начните запись заново.", reply_markup=main_menu_keyboard())
        return

    await state.update_data(client_name=client_name)
    await state.set_state(BookingStates.confirming)

    summary = (
        "📋 <b>Проверьте данные записи:</b>\n\n"
        f"• <b>Услуга:</b> {service.title} ({service.price} ₽)\n"
        f"• <b>Дата:</b> {data['booking_date']}\n"
        f"• <b>Время:</b> {data['booking_time']}\n"
        f"• <b>Имя:</b> {client_name}\n\n"
        "Подтверждаем запись?"
    )
    await message.answer(summary, parse_mode="HTML", reply_markup=confirm_booking_keyboard())


@router.callback_query(BookingStates.confirming, F.data == "confirm:yes")
async def cb_confirm_booking(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """Сохраняет запись в SQLite, сбрасывает состояние и уведомляет мастера."""
    data = await state.get_data()
    service = SERVICES_BY_ID.get(data.get("service_id", ""))
    booking_date = data.get("booking_date")
    booking_time = data.get("booking_time")
    client_name = data.get("client_name")
    user = callback.from_user

    if not (service and booking_date and booking_time and client_name and user):
        await state.clear()
        await callback.answer("Не удалось сохранить запись, попробуйте снова.", show_alert=True)
        return

    booking_id = create_booking(
        db_path=DB_PATH,
        user_id=user.id,
        username=user.username,
        client_name=client_name,
        service_id=service.id,
        service_title=service.title,
        price=service.price,
        booking_date=booking_date,
        booking_time=booking_time,
    )

    await state.clear()
    await callback.answer()

    if booking_id is None:
        await callback.message.answer(
            "Этот слот только что заняли. Выберите другой день или время:",
            reply_markup=dates_keyboard(days_ahead=7),
        )
        return

    await callback.message.answer(
        f"✅ <b>Запись #{booking_id} подтверждена!</b>\n\n"
        f"• <b>Услуга:</b> {service.title} ({service.price} ₽)\n"
        f"• <b>Дата и время:</b> {booking_date} в {booking_time}\n"
        f"• <b>Имя:</b> {client_name}\n\n"
        "Ждём вас в NORTH CUT!",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(),
    )

    if MASTER_CHAT_ID:
        tg_nick = f"@{user.username}" if user.username else f"ID {user.id}"
        master_notice = (
            f"🔔 <b>Новая запись #{booking_id}</b>\n\n"
            f"• <b>Клиент:</b> {client_name} ({tg_nick})\n"
            f"• <b>Услуга:</b> {service.title} — {service.price} ₽\n"
            f"• <b>Когда:</b> {booking_date} в {booking_time}"
        )
        try:
            await bot.send_message(chat_id=MASTER_CHAT_ID, text=master_notice, parse_mode="HTML")
        except Exception:
            pass


@router.callback_query(F.data == "menu:my_bookings")
async def cb_my_bookings(callback: CallbackQuery) -> None:
    """Показывает активные записи клиента и кнопки для отмены."""
    user_id = callback.from_user.id
    bookings = get_user_bookings(DB_PATH, user_id)
    await callback.answer()

    if not bookings:
        await callback.message.answer(
            "У вас пока нет активных записей.",
            reply_markup=main_menu_keyboard(),
        )
        return

    lines = ["📅 <b>Ваши активные записи:</b>\n"]
    for item in bookings:
        lines.append(
            f"• <b>#{item['id']}</b> — {item['service_title']} ({item['price']} ₽)\n"
            f"  🗓 {item['booking_date']} в 🕒 {item['booking_time']} (Имя: {item['client_name']})"
        )

    await callback.message.answer(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=my_bookings_keyboard(bookings),
    )


@router.callback_query(F.data.startswith("cancel_bk:"))
async def cb_cancel_booking(callback: CallbackQuery) -> None:
    """Отменяет запись клиента, чтобы освободить слот для других гостей."""
    booking_id_str = callback.data.split(":", 1)[1]
    if not booking_id_str.isdigit():
        await callback.answer("Некорректный ID записи", show_alert=True)
        return

    booking_id = int(booking_id_str)
    user_id = callback.from_user.id
    cancelled = cancel_booking(DB_PATH, booking_id, user_id)

    if not cancelled:
        await callback.answer("Запись уже отменена или не найдена.", show_alert=True)
        return

    await callback.answer("Запись отменена")
    remaining = get_user_bookings(DB_PATH, user_id)
    if not remaining:
        await callback.message.answer(
            f"Запись <b>#{booking_id}</b> отменена. Активных записей больше нет.",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(),
        )
    else:
        await callback.message.answer(
            f"Запись <b>#{booking_id}</b> отменена. Оставшиеся записи:",
            parse_mode="HTML",
            reply_markup=my_bookings_keyboard(remaining),
        )
