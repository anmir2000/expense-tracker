import streamlit as st #нужен для создания интерфейса
import pandas as pd
from datetime import date #автоматически получать сегодняшнюю дату
from supabase import create_client, Client


supabase: Client = create_client(
    st.secrets["supabase"]["url"],
    st.secrets["supabase"]["key"]
)
if "user" not in st.session_state:
    st.session_state.user = None


def show_authentication():
    st.title("Учёт расходов")

    auth_mode = st.radio(
        "Выберите действие",
        ["Вход", "Регистрация"],
        horizontal=True,
        label_visibility="collapsed"
    )

    if auth_mode == "Вход":
        st.subheader("Вход")

        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input(
                "Пароль",
                type="password"
            )

            login_button = st.form_submit_button(
                "Войти",
                use_container_width=True
            )

        if login_button:
            if not email or not password:
                st.error("Заполните email и пароль")

            else:
                try:
                    response = supabase.auth.sign_in_with_password(
                        {
                            "email": email,
                            "password": password
                        }
                    )

                    st.session_state.user = response.user
                    st.rerun()

                except Exception as error:
                    st.error(f"Ошибка входа: {error}")

    else:
        st.subheader("Регистрация")

        with st.form("register_form"):
            email = st.text_input(
                "Email",
                key="register_email"
            )

            password = st.text_input(
                "Пароль",
                type="password",
                key="register_password"
            )

            repeat_password = st.text_input(
                "Повторите пароль",
                type="password"
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
            if not email or not password or not repeat_password:
                st.error("Заполните все поля")
    
            elif password != repeat_password:
                st.error("Пароли не совпадают")
    
            elif len(password) < 6:
                st.error(
                    "Пароль должен содержать минимум 6 символов"
                )
    
            else:
                try:
                    supabase.auth.sign_up(
                        {
                            "email": email,
                            "password": password,
                            "options": {
                                "email_redirect_to":
                                "https://expense-tracker-8eujmioxux8vqcfwiuddwq.streamlit.app/"
                            }
                        }
                    )
    
                    st.success(
                        "Аккаунт создан. Проверьте почту."
                    )
    
                except Exception as error:
                    st.error(
                        f"Ошибка регистрации: {error}"
                    )
    
        if resend_button:
            if not email:
                st.error("Введите email")
    
            else:
                try:
                    supabase.auth.resend(
                        {
                            "type": "signup",
                            "email": email,
                            "options": {
                                "email_redirect_to":
                                "https://expense-tracker-8eujmioxux8vqcfwiuddwq.streamlit.app/"
                            }
                        }
                    )
    
                    st.success(
                        "Новое письмо подтверждения отправлено"
                    )
    
                except Exception as error:
                    st.error(
                        f"Ошибка отправки письма: {error}"
                    )
if st.session_state.user is None:
    show_authentication()
    st.stop()
st.sidebar.write(
    f"Вы вошли как: {st.session_state.user.email}"
)

#Настройка страницы
st.set_page_config( #Это настройки вкладки браузера
    page_title="Учёт расходов",#Название вкладки.
    page_icon="💰"#Иконка вкладки.
)

st.title("Учёт расходов")


# Создаём хранилище расходов
if "expenses" not in st.session_state:#Если в хранилище ещё нет переменной expenses
    st.session_state.expenses = []#Тогда создаём её


# Проверяем, был ли уже рассчитан бюджет
if "budget_ready" not in st.session_state:
    st.session_state.budget_ready = False


def calculate_daily_limit(period_money, days, saving_percent):
    savings = period_money * saving_percent / 100
    money_for_expenses = period_money - savings
    daily_limit = money_for_expenses / days

    return savings, money_for_expenses, daily_limit


st.header("1. Настройка бюджета")


period_money = st.number_input(
    "Количество денег на период",
    min_value=0.0,
    step=100.0
)

days = st.number_input(
    "Количество дней",
    min_value=1,
    step=1
)

use_savings = st.checkbox("Отложить часть денег на сбережения")

saving_percent = st.number_input(
    "Процент сбережений",
    min_value=0.0,
    max_value=100.0,
    value=0.0,
    step=1.0,
    disabled=not use_savings
)

calculate_button = st.button("Рассчитать бюджет")


if calculate_button:
    if not use_savings:
        saving_percent = 0

    savings, money_for_expenses, daily_limit = calculate_daily_limit(
        period_money,
        days,
        saving_percent
    )

    st.session_state.savings = savings
    st.session_state.money_for_expenses = money_for_expenses
    st.session_state.daily_limit = daily_limit
    st.session_state.budget_ready = True


if st.session_state.budget_ready:
    st.subheader("Ваш бюджет")

    column1, column2, column3 = st.columns(3)

    column1.metric(
        "Сбережения",
        round(st.session_state.savings, 2)
    )

    column2.metric(
        "На расходы",
        round(st.session_state.money_for_expenses, 2)
    )

    column3.metric(
        "Лимит в день",
        round(st.session_state.daily_limit, 2)
    )

    st.header("2. Добавление траты")

    with st.form("expense_form", clear_on_submit=True):
        expense_date = st.date_input(
            "Дата траты",
            value=date.today()
        )

        name = st.text_input("Название траты")

        amount = st.number_input(
            "Сумма",
            min_value=0.0,
            step=0.1
        )

        add_button = st.form_submit_button("Добавить трату")

    if add_button:
        if name == "":
            st.error("Введите название траты")

        elif amount <= 0:
            st.error("Сумма должна быть больше нуля")

        else:
            expense = {
                "date": str(expense_date),
                "name": name,
                "amount": amount
            }

            st.session_state.expenses.append(expense)
            st.success("Трата добавлена")


    # Выбираем день для просмотра расходов
    selected_date = st.date_input(
        "Посмотреть расходы за день",
        value=date.today(),
        key="selected_date"
    )

    day_total = 0

    for expense in st.session_state.expenses:
        if expense["date"] == str(selected_date):
            day_total += expense["amount"]

    remaining = st.session_state.daily_limit - day_total

    st.header("3. Результат за день")

    st.metric(
        "Потрачено",
        round(day_total, 2)
    )

    if remaining >= 0:
        st.success(
            f"Вы вписываетесь в бюджет. "
            f"Можно потратить ещё: {round(remaining, 2)}"
        )
    else:
        st.error(
            f"Дневной бюджет превышен на: "
            f"{round(abs(remaining), 2)}"
        )

    if st.session_state.expenses:
        st.header("Все траты")

        expenses_table = pd.DataFrame(
            st.session_state.expenses
        )

        st.dataframe(
            expenses_table,
            use_container_width=True
        )
