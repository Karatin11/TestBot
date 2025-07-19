from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import aiohttp
import html
from aiogram.types import Message

API_BASE = "http://localhost:8000/api"

router = Router()

class RegisterForm(StatesGroup):
    username = State()
    password = State()

class LoginState(StatesGroup):
    username = State()
    password = State()

class TestPassing(StatesGroup):
    subject_id = State()
    questions = State()
    current_index = State()
    answers = State()

async def send_long_message(bot, chat_id, text, max_length=4000):
    while text:
        chunk = html.escape(text[:max_length])
        text = text[max_length:]
        await bot.send_message(chat_id, chunk, parse_mode="HTML")

@router.message(Command("register"))
async def register_start(message: types.Message, state: FSMContext):
    await message.answer("Введите имя пользователя:")
    await state.set_state(RegisterForm.username)

@router.message(RegisterForm.username)
async def register_username(message: types.Message, state: FSMContext):
    await state.update_data(username=message.text)
    await message.answer("Введите пароль:")
    await state.set_state(RegisterForm.password)

@router.message(RegisterForm.password)
async def register_password(message: types.Message, state: FSMContext):
    data = await state.get_data()
    username = data["username"]
    password = message.text

    async with aiohttp.ClientSession() as session:
        async with session.post(f"{API_BASE}/register/", json={"username": username, "password": password}) as resp:
            if resp.status == 201:
                await message.answer("✅ Вы успешно зарегистрированы! Теперь войдите через /login.")
                await state.clear()  # Чистим состояние после регистрации

            else:
                # Ошибка регистрации — не чистим, чтобы пользователь мог повторить ввод
                text = await resp.text()
                await send_long_message(message.bot, message.chat.id, f"Ошибка регистрации: {text}")


@router.message(Command("login"))
async def login_start(message: types.Message, state: FSMContext):
    await message.answer("Введите имя пользователя:")
    await state.set_state(LoginState.username)

@router.message(LoginState.username)
async def login_username(message: types.Message, state: FSMContext):
    await state.update_data(username=message.text)
    await message.answer("Введите пароль:")
    await state.set_state(LoginState.password)

@router.message(LoginState.password)
async def login_password(message: Message, state: FSMContext):
    data = await state.get_data()
    username = data["username"]
    password = message.text
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{API_BASE}/token/", json={"username": username, "password": password}) as resp:
            if resp.status == 200:
                result = await resp.json()
                access_token = result.get("access")
                refresh_token = result.get("refresh")
                if access_token:
                    await state.clear()
                    await state.update_data(access_token=access_token, refresh_token=refresh_token)
                    await message.answer("✅ Авторизация прошла успешно!")
                else:
                    await message.answer("⚠️ Ошибка: токен не получен.")
            else:
                text = await resp.text()
                await message.answer(f"❌ Неверные данные: {text}")
                await state.clear()

@router.message(Command("subjects"))
async def get_subjects(message: types.Message, state: FSMContext):
    data = await state.get_data()
    access_token = data.get("access_token")
    print(access_token)
    headers = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"


    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_BASE}/subjects/", headers=headers) as resp:
            if resp.status != 200:
                await message.answer("Ошибка при получении предметов. Попробуйте войти заново /login.")
                return
            subjects = await resp.json()
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text=sub["name"], callback_data=f"subject_{sub['id']}")]
                    for sub in subjects
                ]
            )
            await message.answer("Выберите предмет:", reply_markup=keyboard)

@router.callback_query(F.data.startswith("subject_"))
async def start_test(callback: types.CallbackQuery, state: FSMContext):
    subject_id = int(callback.data.split("_")[1])
    data = await state.get_data()
    access_token = data.get("access_token")
    if not access_token:
        await callback.message.answer("❗ Вы не авторизованы. Сначала войдите через /login.")
        await callback.answer()
        return

    headers = {"Authorization": f"Bearer {access_token}"}

    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_BASE}/subjects/{subject_id}/questions/", headers=headers) as resp:
            if resp.status != 200:
                await callback.message.answer("Ошибка при загрузке вопросов. Попробуйте позже.")
                await callback.answer()
                return

            questions = await resp.json()
            if not questions:
                await callback.message.answer("Вопросов нет для этого предмета.")
                await callback.answer()
                return

            await state.set_state(TestPassing.questions)
            await state.update_data(subject_id=subject_id, questions=questions, current_index=0, answers=[])

            await callback.answer()
            await send_next_question(callback.message, state)

async def send_next_question(message: types.Message, state: FSMContext):
    data = await state.get_data()
    index = data.get("current_index", 0)
    questions = data.get("questions", [])

    if index >= len(questions):
        await finish_test(message, state)
        return

    q = questions[index]
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=ans["text"], callback_data=f"answer_{ans['id']}")]
            for ans in q.get("answers", [])
        ]
    )
    await message.answer(f"❓ {q['text']}", reply_markup=keyboard)

@router.callback_query(F.data.startswith("answer_"))
async def handle_answer(callback: types.CallbackQuery, state: FSMContext):
    answer_id = int(callback.data.split("_")[1])
    data = await state.get_data()
    questions = data.get("questions", [])
    index = data.get("current_index", 0)

    if index >= len(questions):
        await callback.answer("Тест уже завершён.")
        return

    question_id = questions[index]["question_id"]
    answers = data.get("answers", [])
    answers.append({"question_id": question_id, "answer_id": answer_id})

    await state.update_data(current_index=index + 1, answers=answers)
    await callback.answer()
    await send_next_question(callback.message, state)

async def finish_test(message: types.Message, state: FSMContext):
    data = await state.get_data()
    payload = {
        "subject_id": data.get("subject_id"),
        "answers": data.get("answers", [])
    }

    access_token = data.get("access_token")
    refresh_token = data.get("refresh_token")
    if not access_token:
        await message.answer("❗ Вы не авторизованы. Зарегистрируйтесь или войдите через /login.")
        return

    headers = {"Authorization": f"Bearer {access_token}"}
    print(headers)

    async with aiohttp.ClientSession() as session:
        async with session.post(f"{API_BASE}/submit-test/", json=payload, headers=headers) as resp:
            if resp.status == 200:
                result = await resp.json()
                await message.answer(
                    f"✅ Тест завершён!\n"
                    f"Вы набрали {result.get('score')} из {result.get('total')} баллов."
                )
            elif resp.status == 403:
                await message.answer("🚫 Недостаточно прав. Вероятно, истёк токен.")
            else:
                text = await resp.text()
                await message.answer(f"Ошибка при отправке результатов: {text}")

    await state.clear()
    await state.update_data(access_token=access_token, refresh_token=refresh_token)

@router.message(Command("history"))
async def get_history(message: types.Message, state: FSMContext):
    data = await state.get_data()
    access_token = data.get("access_token")
    if not access_token:
        await message.answer("❗ Сначала авторизуйтесь через /login.")
        return

    headers = {"Authorization": f"Bearer {access_token}"}
    print(headers)

    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_BASE}/history/", headers=headers) as resp:
            if resp.status == 200:
                history = await resp.json()
                if not history:
                    await message.answer("📭 История пуста.")
                else:
                    text = "\n".join(f"🧠 {x['subject']}: {x['score']} баллов" for x in history)
                    await message.answer(text)
            else:
                await message.answer("Ошибка при получении истории.")

@router.message(Command("checktoken"))
async def check_token(message: types.Message, state: FSMContext):
    data = await state.get_data()
    token = data.get("access_token")
    if token:
        await message.answer(f"Токен есть: {token[:20]}...")  # показываем начало токена
    else:
        await message.answer("Токен отсутствует!")


@router.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "Привет! Я тест-бот.\n"
        "/register — регистрация\n"
        "/login — вход\n"
        "/subjects — список предметов\n"
        "/history — история прохождений"
    )