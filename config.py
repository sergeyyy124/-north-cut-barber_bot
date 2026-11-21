from dataclasses import dataclass


@dataclass(frozen=True)
class Service:
    """Описание одной услуги барбершопа."""
    id: str
    title: str
    price: int
    duration_min: int


# Токен бота (для теста подставлен ваш токен; при публикации в открытый репозиторий лучше вынести в окружение)
BOT_TOKEN: str = "9249592284:AAHJwyscpyezsAxW7_4wjgrOaSyC37xNtDQ"

# Telegram ID мастера (число), которому будут приходить уведомления о новых записях
MASTER_CHAT_ID: int = 0

# Имя файла локальной базы данных SQLite
DB_PATH: str = "barber_bookings.db"

# Контактная информация барбершопа для раздела «Контакты»
SHOP_CONTACTS: str = (
    "💈 <b>Барбершоп «NORTH CUT»</b>\n"
    "📍 Адрес: ул. Центральная, 14\n"
    "🕒 График работы: ежедневно с 10:00 до 20:00\n"
    "📞 Телефон: +7 (999) 123-45-67\n"
    "💬 Администратор: @northcut_admin"
)

# Список из 4 услуг с ценами и длительностью
SERVICES: list[Service] = [
    Service(id="haircut", title="Мужская стрижка", price=1800, duration_min=60),
    Service(id="beard", title="Оформление бороды", price=1200, duration_min=30),
    Service(id="combo", title="Стрижка + борода", price=2700, duration_min=90),
    Service(id="kids", title="Детская стрижка", price=1400, duration_min=45),
]

# Базовые слоты времени на день
TIME_SLOTS: list[str] = [
    "10:00",
    "11:00",
    "12:00",
    "13:00",
    "14:00",
    "15:00",
    "16:00",
    "17:00",
    "18:00",
    "19:00",
]

# Словарь быстрого доступа к услуге по её id
SERVICES_BY_ID: dict[str, Service] = {service.id: service for service in SERVICES}
