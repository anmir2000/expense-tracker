import streamlit as st
import pandas as pd
from datetime import date
from supabase import create_client, Client
from streamlit_cookies_manager_ext import EncryptedCookieManager

# ==========================================
# Настройка страницы
# ==========================================

st.set_page_config(
    page_title="Учёт расходов",
    page_icon="💰",
    layout="centered"
)
APP_URL = (
    "https://expense-tracker-8eujmioxux8vqcfwiuddwq.streamlit.app/"
)
cookies = EncryptedCookieManager(
    prefix="expense_tracker/",
    password=st.secrets["cookies"]["password"]
)

if not cookies.ready():
    st.stop()


# ==========================================
# Подключение к Supabase
# ==========================================

supabase: Client = create_client(
    st.secrets["supabase"]["url"],
    st.secrets["supabase"]["key"]
)


# ==========================================
# Начальные значения session_state
# ==========================================

session_defaults = {
    "user_id": None,
    "user_email": None,
    "access_token": None,
    "refresh_token": None,
    "auth_error": None,
    "auth_success": None,
    "current_page":"main",
}

for key, default_value in session_defaults.items():
    if key not in st.session_state:
        st.session_state[key] = default_value


def clear_auth_messages():
    """Удаляет старые сообщения входа и регистрации."""

    st.session_state.auth_error = None
    st.session_state.auth_success = None


def clear_user_state():
    """Удаляет данные авторизации пользователя."""

    st.session_state.user_id = None
    st.session_state.user_email = None
    st.session_state.access_token = None
    st.session_state.refresh_token = None

    # Удаляем значения интерфейса предыдущего пользователя
    widget_keys = [
        "budget_period_money",
        "budget_days",
        "use_savings",
        "saving_percent",
        "selected_date",
    ]

    for key in widget_keys:
        st.session_state.pop(key, None)


def save_auth_session(response):
    """Сохраняет пользователя и токены после входа."""

    if response.user is None or response.session is None:
        return False

    st.session_state.user_id = response.user.id
    st.session_state.user_email = response.user.email

    st.session_state.access_token = (
        response.session.access_token
    )

    st.session_state.refresh_token = (
        response.session.refresh_token
    )
    cookies["refresh_token"] = (
        response.session.refresh_token
    )
    cookies.save()

    return True


# ==========================================
# Восстановление сессии Supabase
# ==========================================
if st.session_state.user_id is None:
    saved_refresh_token = cookies.get("refresh_token")

    if saved_refresh_token:
        try:
            response = supabase.auth.refresh_session(
                saved_refresh_token
            )

            save_auth_session(response)

        except Exception:
            try:
                del cookies["refresh_token"]
                cookies.save()
            except KeyError:
                pass
if (
    st.session_state.access_token
    and st.session_state.refresh_token
):
    try:
        session_response = supabase.auth.set_session(
            st.session_state.access_token,
            st.session_state.refresh_token
        )

        # Supabase мог обновить токены
        if session_response.session is not None:
            st.session_state.access_token = (
                session_response.session.access_token
            )

            st.session_state.refresh_token = (
                session_response.session.refresh_token
            )

        user_response = supabase.auth.get_user()

        if user_response.user is not None:
            st.session_state.user_id = (
                user_response.user.id
            )

            st.session_state.user_email = (
                user_response.user.email
            )

    except Exception:
        clear_user_state()


# ==========================================
# Обработка понятных сообщений об ошибках
# ==========================================

def get_readable_auth_error(error):
    error_text = str(error)
    error_lower = error_text.lower()

    if "email rate limit exceeded" in error_lower:
        return (
            "Превышен лимит отправки писем. "
            "Попробуйте позже."
        )

    if "email not confirmed" in error_lower:
        return (
            "Почта ещё не подтверждена. "
            "Проверьте письмо от Supabase."
        )

    if "invalid login credentials" in error_lower:
        return "Неверный email или пароль."

    if "user already registered" in error_lower:
        return "Пользователь с таким email уже зарегистрирован."

    if "password should be at least" in error_lower:
        return "Пароль слишком короткий."

    return error_text


# ==========================================
# Вход и регистрация
# ==========================================

def show_authentication():
    st.title("Учёт расходов")

    auth_mode = st.radio(
        "Выберите действие",
        ["Вход", "Регистрация"],
        horizontal=True,
        label_visibility="collapsed",
        key="auth_mode",
        on_change=clear_auth_messages
    )

    # --------------------------------------
    # Вход
    # --------------------------------------

    if auth_mode == "Вход":
        st.subheader("Вход")

        with st.form(
            "login_form",
            clear_on_submit=False
        ):
            login_email = st.text_input(
                "Email",
                key="login_email"
            )

            login_password = st.text_input(
                "Пароль",
                type="password",
                key="login_password"
            )

            login_button = st.form_submit_button(
                "Войти",
                use_container_width=True
            )

        if login_button:
            clear_auth_messages()

            if not login_email or not login_password:
                st.session_state.auth_error = (
                    "Заполните email и пароль."
                )

            else:
                try:
                    response = (
                        supabase.auth.sign_in_with_password(
                            {
                                "email": login_email,
                                "password": login_password,
                            }
                        )
                    )

                    if save_auth_session(response):
                        st.rerun()

                    else:
                        st.session_state.auth_error = (
                            "Не удалось создать сессию."
                        )

                except Exception as error:
                    st.session_state.auth_error = (
                        get_readable_auth_error(error)
                    )

    # --------------------------------------
    # Регистрация
    # --------------------------------------

    else:
        st.subheader("Регистрация")

        with st.form(
            "register_form",
            clear_on_submit=False
        ):
            register_email = st.text_input(
                "Email",
                key="register_email"
            )

            register_password = st.text_input(
                "Пароль",
                type="password",
                key="register_password"
            )

            repeat_password = st.text_input(
                "Повторите пароль",
                type="password",
                key="repeat_password"
            )

            register_button = st.form_submit_button(
                "Создать аккаунт",
                use_container_width=True
            )

            resend_button = st.form_submit_button(
                "Отправить письмо повторно",
                use_container_width=True
            )

        if register_button:
            clear_auth_messages()

            if (
                not register_email
                or not register_password
                or not repeat_password
            ):
                st.session_state.auth_error = (
                    "Заполните все поля."
                )

            elif register_password != repeat_password:
                st.session_state.auth_error = (
                    "Пароли не совпадают."
                )

            elif len(register_password) < 6:
                st.session_state.auth_error = (
                    "Пароль должен содержать минимум 6 символов."
                )

            else:
                try:
                    response = supabase.auth.sign_up(
                        {
                            "email": register_email,
                            "password": register_password,
                            "options": {
                                "email_redirect_to": APP_URL
                            },
                        }
                    )

                    # Если подтверждение email выключено,
                    # Supabase сразу возвращает сессию
                    if save_auth_session(response):
                        st.rerun()

                    else:
                        st.session_state.auth_success = (
                            "Аккаунт создан. "
                            "Проверьте письмо для подтверждения почты."
                        )

                except Exception as error:
                    st.session_state.auth_error = (
                        get_readable_auth_error(error)
                    )

        if resend_button:
            clear_auth_messages()

            if not register_email:
                st.session_state.auth_error = (
                    "Введите email."
                )

            else:
                try:
                    supabase.auth.resend(
                        {
                            "type": "signup",
                            "email": register_email,
                            "options": {
                                "email_redirect_to": APP_URL
                            },
                        }
                    )

                    st.session_state.auth_success = (
                        "Новое письмо подтверждения отправлено."
                    )

                except Exception as error:
                    st.session_state.auth_error = (
                        get_readable_auth_error(error)
                    )

    # --------------------------------------
    # Сообщения
    # --------------------------------------

    if st.session_state.auth_error:
        st.error(st.session_state.auth_error)

    if st.session_state.auth_success:
        st.success(st.session_state.auth_success)


# Пока пользователь не вошёл,
# код приложения ниже не выполняется
if st.session_state.user_id is None:
    show_authentication()
    st.stop()


# ==========================================
# Боковая панель и выход
# ==========================================

st.sidebar.write(
    f"Вы вошли как:\n\n{st.session_state.user_email}"
)
if st.sidebar.button(
    "Настройка бюджета",
    use_container_width=True
):
    st.session_state.current_page="budget"
    st.rerun()
if st.sidebar.button(
    "История",
    use_container_width=True
):
    st.session_state.current_page="history"
    st.rerun()
    
if st.sidebar.button(
    "Выйти",
    use_container_width=True
):
    try:
        supabase.auth.sign_out()

    except Exception:
        pass
    try:
        del cookies["refresh_token"]
        cookies.save()
    except KeyError:
        pass
    clear_user_state()
    clear_auth_messages()
    st.session_state.current_page = "main"
    st.rerun()

# ==========================================
# Функции работы с базой данных
# ==========================================

def load_budget(user_id):
    """Загружает бюджет пользователя."""

    response = (
        supabase
        .table("budgets")
        .select("*")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )

    if response.data:
        return response.data[0]

    return None


def save_budget(
    user_id,
    period_money,
    days,
    saving_percent
):
    """Создаёт или обновляет бюджет пользователя."""

    savings = period_money * saving_percent / 100

    money_for_expenses = (
        period_money - savings
    )

    daily_limit = (
        money_for_expenses / days
    )

    budget_data = {
        "user_id": user_id,
        "period_money": period_money,
        "days": days,
        "saving_percent": saving_percent,
        "savings": savings,
        "money_for_expenses": money_for_expenses,
        "daily_limit": daily_limit,
    }

    (
        supabase
        .table("budgets")
        .upsert(budget_data)
        .execute()
    )

    return budget_data


def add_expense_to_database(
    user_id,
    expense_date,
    name,
    amount
):
    """Добавляет трату в Supabase."""

    expense_data = {
        "user_id": user_id,
        "expense_date": str(expense_date),
        "name": name.strip(),
        "amount": amount,
    }

    (
        supabase
        .table("expenses")
        .insert(expense_data)
        .execute()
    )


def load_expenses(user_id):
    """Загружает траты пользователя."""

    response = (
        supabase
        .table("expenses")
        .select(
            "id, expense_date, name, amount, created_at"
        )
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(50)
        .execute()
    )

    return response.data or []
def load_expenses_for_day(user_id, selected_date):
    response=(
        supabase
        .table("expenses")
        .select("id,expense_date,name,amount")
        .eq("user_id",user_id)
        .eq("expense_date",str(selected_date))
        .execute()
    )
    return response.data or[]
    

# =====================
# Основное приложение
# =====================
#стр бюджета
if st.session_state.current_page == "budget":
    st.title("Настройка бюджета")
    if st.button("Вернуться на главную"):
        st.session_state.current_page="main"
        st.rerun()
    budget_period=st.data_input(
        "Выберите период бюджета",
        value=(),
        format="DD.MM.YYYY",
        key="budget_period"
    )
    st.write("Полученное значение:",budget_period)
    st.stop()
        
#стр истории
if st.session_state.current_page == "history":
    st.title("История расходов")

    if st.button("Вернуться на главную"):
        st.session_state.current_page = "main"
        st.rerun()

    selected_date=st.date_input(#selected_date =сохраняет выбранную пользователем дату в переменную.
        #st.date_input(...)st.date_input(...)
        "Выберите день",
        value=date.today(),#по умолчанию выбирает сегодняшний день.
        key="history_date"
    )
    st.write("Вы выбрали:",selected_date)

    st.stop()
st.title("Учёт расходов")

user_id = st.session_state.user_id


# ==========================================
# Загрузка бюджета
# ==========================================

try:
    budget = load_budget(user_id)

except Exception as error:
    st.error(
        f"Не удалось загрузить бюджет: {error}"
    )

    if st.button("Повторить загрузку"):
        st.rerun()

    st.stop()


# ==========================================
# Настройка бюджета
# ==========================================

st.header("1. Настройка бюджета")

if budget is None:
    default_period_money = 0.0
    default_days = 30
    default_saving_percent = 0.0

else:
    default_period_money = float(
        budget["period_money"]
    )

    default_days = int(
        budget["days"]
    )

    default_saving_percent = float(
        budget["saving_percent"]
    )


period_money = st.number_input(
    "Количество средств на период",
    min_value=0.0,
    value=default_period_money,
    step=100.0,
    key="budget_period_money"
)

days = st.number_input(
    "Период(кол-во дней)",
    min_value=1,
    value=default_days,
    step=1,
    key="budget_days"
)

use_savings = st.checkbox(
    "Отложить часть денег на сбережения",
    value=default_saving_percent > 0,
    key="use_savings"
)

saving_percent = st.number_input(
    "Процент сбережений",
    min_value=0.0,
    max_value=100.0,
    value=default_saving_percent,
    step=1.0,
    disabled=not use_savings,
    key="saving_percent"
)

save_budget_button = st.button(
    "Сохранить бюджет",
    use_container_width=True
)


if save_budget_button:
    if period_money <= 0:
        st.error(
            "Количество денег должно быть больше нуля."
        )

    else:
        if not use_savings:
            saving_percent = 0.0

        try:
            budget = save_budget(
                user_id=user_id,
                period_money=float(period_money),
                days=int(days),
                saving_percent=float(saving_percent)
            )

            st.success("Бюджет сохранён.")

        except Exception as error:
            st.error(
                f"Не удалось сохранить бюджет: {error}"
            )


# ==========================================
# Бюджет рассчитан
# ==========================================

if budget is not None:
    savings = float(budget["savings"])

    money_for_expenses = float(
        budget["money_for_expenses"]
    )

    daily_limit = float(
        budget["daily_limit"]
    )

    st.subheader("Ваш бюджет")

    column1, column2, column3 = st.columns(3)

    column1.metric(
        "Сбережения",
        f"{savings:.2f}"
    )

    column2.metric(
        "На расходы",
        f"{money_for_expenses:.2f}"
    )

    column3.metric(
        "Лимит в день",
        f"{daily_limit:.2f}"
    )

    st.divider()


    # ======================================
    # Добавление траты
    # ======================================

    st.header("2. Добавление траты")

    with st.form(
        "expense_form",
        clear_on_submit=True
    ):
        expense_date = st.date_input(
            "Дата траты",
            value=date.today()
        )

        expense_name = st.text_input(
            "Название траты"
        )

        expense_amount = st.number_input(
            "Сумма",
            min_value=0.0,
            step=0.1
        )

        add_expense_button = (
            st.form_submit_button(
                "Добавить трату",
                use_container_width=True
            )
        )

    if add_expense_button:
        if not expense_name.strip():
            st.error("Введите название траты.")

        elif expense_amount <= 0:
            st.error(
                "Сумма должна быть больше нуля."
            )

        else:
            try:
                add_expense_to_database(
                    user_id=user_id,
                    expense_date=expense_date,
                    name=expense_name,
                    amount=float(expense_amount)
                )

                st.success("Трата добавлена.")

            except Exception as error:
                st.error(
                    f"Не удалось сохранить трату: {error}"
                )


    # ======================================
    # Загрузка расходов
    # ======================================

    try:
        expenses = load_expenses(user_id)

    except Exception as error:
        st.error(
            f"Не удалось загрузить расходы: {error}"
        )

        expenses = []


    # ======================================
    # Результат за выбранный день
    # ======================================

    st.header("3. Результат за день")

    selected_date = st.date_input(
        "Выберите день",
        value=date.today(),
        key="selected_date"
    )

    day_total = 0.0

    for expense in expenses:
        if expense["expense_date"] == str(selected_date):
            day_total += float(expense["amount"])

    remaining = daily_limit - day_total


    result_column1, result_column2 = st.columns(2)

    result_column1.metric(
        "Потрачено за день",
        f"{day_total:.2f}"
    )

    if remaining >= 0:
        result_column2.metric(
            "Можно потратить ещё",
            f"{remaining:.2f}"
        )

        st.success("Вы вписываетесь в дневной бюджет.")

    else:
        result_column2.metric(
            "Превышение бюджета",
            f"{abs(remaining):.2f}"
        )

        st.error("Дневной бюджет превышен.")


    # ======================================
    # Общая статистика
    # ======================================

    period_total = sum(
        float(expense["amount"])
        for expense in expenses
    )

    period_remaining = (
        money_for_expenses - period_total
    )

    st.subheader("Общий результат")

    total_column1, total_column2 = st.columns(2)

    total_column1.metric(
        "Потрачено всего",
        f"{period_total:.2f}"
    )

    total_column2.metric(
        "Осталось на период",
        f"{period_remaining:.2f}"
    )


    # ======================================
    # Таблица расходов
    # ======================================

    if expenses:
        st.header("Все траты")

        expenses_table = pd.DataFrame(expenses)

        expenses_table["amount"] = pd.to_numeric(
            expenses_table["amount"]
        ).round(2)

        expenses_table = expenses_table[
            [
                "expense_date",
                "name",
                "amount",
            ]
        ]

        expenses_table = expenses_table.rename(
            columns={
                "expense_date": "Дата",
                "name": "Название",
                "amount": "Сумма",
            }
        )

        st.dataframe(
            expenses_table,
            use_container_width=True,
            hide_index=True
        )

    else:
        st.info("Расходов пока нет.")

else:
    st.info(
        "Сначала настройте и сохраните бюджет."
    )
