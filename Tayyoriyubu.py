import logging
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from asyncio import sleep

# Token va admin ID
API_TOKEN = "7881605660:AAFJI5MG1Yyb0s3LFR-mUyUgUNADn4Vglig"
ADMIN_ID = 7888045216  # O'zingizning Telegram ID'ingizni yozing

# Logger sozlamalari
logging.basicConfig(level=logging.INFO)

# Global lug'at: foydalanuvchi tilini saqlash uchun
user_languages = {}

# Bot va Dispatcher
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# Foydalanuvchi holati uchun State
class ChatState(StatesGroup):
    language = State()
    waiting_for_message = State()

# Til menyusi
language_keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
language_keyboard.add(KeyboardButton("🇺🇿 O‘zbek"), KeyboardButton("🇷🇺 Русский"), KeyboardButton("🇬🇧 English"))

# Start buyrug'i (hamma holatda ishlash uchun state="*")
@dp.message_handler(commands=['start'], state="*")
async def start(message: types.Message, state: FSMContext):
    await state.finish()
    text = ("Assalom Aleykum!\n"
            "🧑‍💻Siz anketa kanal admini bilan aloqa botidasiz.\n"
            "Marhamat, pastdagi menulardan muloqot tilini tanlang:")

    text_ru = ("Здравствуйте!\n"
               "🧑‍💻Вы находитесь в боте связи с администратором канала анкет.\n"
               "Пожалуйста, выберите язык общения из меню ниже:")

    text_en = ("Hello!\n"
               "🧑‍💻You are in the questionnaire channel admin contact bot.\n"
               "Please select a communication language from the menu below:")

    await message.answer(f"{text}\n\n{text_ru}\n\n{text_en}", reply_markup=language_keyboard)
    await ChatState.language.set()

# Tilni noto‘g‘ri tanlash
@dp.message_handler(lambda message: message.text not in ["🇺🇿 O‘zbek", "🇷🇺 Русский", "🇬🇧 English"], state=ChatState.language)
async def invalid_language(message: types.Message):
    await message.answer("Iltimos, muloqot qiladigan tilingizni menudan tanlang:", reply_markup=language_keyboard)

# Til tanlaganda
@dp.message_handler(lambda message: message.text in ["🇺🇿 O‘zbek", "🇷🇺 Русский", "🇬🇧 English"], state=ChatState.language)
async def choose_language(message: types.Message, state: FSMContext):
    user_language = message.text
    await state.update_data(language=user_language)
    user_languages[message.from_user.id] = user_language  # Foydalanuvchi tilini saqlaymiz

    if user_language == "🇺🇿 O‘zbek":
        text = "Marhamat, kanal yoki anketalar bo‘yicha savol va taklifingizni yozishingiz mumkin:"
    elif user_language == "🇷🇺 Русский":
        text = "Пожалуйста, напишите ваш вопрос или предложение по каналу и анкетам:"
    else:
        text = "Please write your question or suggestion about the channel and questionnaires:"

    await message.answer(text, reply_markup=ReplyKeyboardRemove())
    await ChatState.waiting_for_message.set()

    # Agar foydalanuvchi 10 daqiqa ichida xabar yubormasa, bot qayta boshlaydi
    async def reset_if_no_message():
        await sleep(600)
        current_state = await state.get_state()
        if current_state == ChatState.waiting_for_message.state:
            await start(message, state)

    dp.loop.create_task(reset_if_no_message())

# Foydalanuvchi xabar yuborsa, adminga yetkazish
@dp.message_handler(content_types=types.ContentTypes.ANY, state=ChatState.waiting_for_message)
async def send_to_admin(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    username = f"@{message.from_user.username}" if message.from_user.username else f"[Profilga o‘tish](tg://user?id={user_id})"

    # "Javob berish" tugmasi
    reply_button = InlineKeyboardMarkup().add(
        InlineKeyboardButton("✍️ Javob berish", callback_data=f"reply_{message.message_id}_{user_id}")
    )

    caption = f"📩 *Yangi xabar:*\n\n{message.text or '📎 Media fayl'}\n\n👤 {username} ({user_id})"

    if message.text:
        msg = await bot.send_message(ADMIN_ID, caption, parse_mode="Markdown", reply_markup=reply_button)
    elif message.photo:
        msg = await bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=caption, parse_mode="Markdown", reply_markup=reply_button)
    elif message.video:
        msg = await bot.send_video(ADMIN_ID, message.video.file_id, caption=caption, parse_mode="Markdown", reply_markup=reply_button)
    elif message.voice:
        msg = await bot.send_voice(ADMIN_ID, message.voice.file_id, caption=caption, parse_mode="Markdown", reply_markup=reply_button)
    elif message.document:
        msg = await bot.send_document(ADMIN_ID, message.document.file_id, caption=caption, parse_mode="Markdown", reply_markup=reply_button)

    # Xabarni xotirada saqlash
    await state.update_data({f"msg_{msg.message_id}": message.message_id})
    
    # Foydalanuvchiga tiliga mos tasdiq xabari yuborish
    data = await state.get_data()
    user_lang = data.get("language", "🇺🇿 O‘zbek")
    if user_lang == "🇺🇿 O‘zbek":
        conf_text = "Sizning habaringiz adminga yuborildi"
    elif user_lang == "🇷🇺 Русский":
        conf_text = "Ваше сообщение отправлено администратору"
    elif user_lang == "🇬🇧 English":
        conf_text = "Your message has been sent to the admin"
    else:
        conf_text = "Sizning habaringiz adminga yuborildi"
    await message.answer(conf_text)

# Admin "Javob berish" tugmasini bosganda
@dp.callback_query_handler(lambda call: call.data.startswith("reply_"))
async def reply_to_user(call: types.CallbackQuery, state: FSMContext):
    _, msg_id, user_id = call.data.split("_")
    await state.update_data(replying_to=(msg_id, user_id))
    await call.message.answer("✍️ Javobingizni yozing:")
    await call.answer()

# Admin javob yozganda
@dp.message_handler(content_types=types.ContentTypes.ANY, user_id=ADMIN_ID)
async def send_reply_to_user(message: types.Message, state: FSMContext):
    data = await state.get_data()
    reply_info = data.get("replying_to")

    if reply_info:
        msg_id, user_id = reply_info
        
        # Foydalanuvchining tanlagan tilini aniqlaymiz
        lang = user_languages.get(int(user_id), "🇺🇿 O‘zbek")
        if lang == "🇺🇿 O‘zbek":
            finish_text = "Suhbatni yakunlash"
        elif lang == "🇷🇺 Русский":
            finish_text = "Завершить чат"
        elif lang == "🇬🇧 English":
            finish_text = "End conversation"
        else:
            finish_text = "Suhbatni yakunlash"
            
        end_kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton(finish_text, callback_data="end_conversation")
        )

        if message.text:
            await bot.send_message(user_id, f"👨‍💻 *Admin javobi:*\n\n{message.text}", 
                                   parse_mode="Markdown", reply_to_message_id=int(msg_id), reply_markup=end_kb)
        elif message.photo:
            await bot.send_photo(user_id, message.photo[-1].file_id, caption="👨‍💻 *Admin javobi*",
                                 parse_mode="Markdown", reply_to_message_id=int(msg_id), reply_markup=end_kb)
        elif message.video:
            await bot.send_video(user_id, message.video.file_id, caption="👨‍💻 *Admin javobi*",
                                 parse_mode="Markdown", reply_to_message_id=int(msg_id), reply_markup=end_kb)
        elif message.voice:
            await bot.send_voice(user_id, message.voice.file_id, caption="👨‍💻 *Admin javobi*",
                                 parse_mode="Markdown", reply_to_message_id=int(msg_id), reply_markup=end_kb)
        elif message.document:
            await bot.send_document(user_id, message.document.file_id, caption="👨‍💻 *Admin javobi*",
                                    parse_mode="Markdown", reply_to_message_id=int(msg_id), reply_markup=end_kb)

        await state.update_data(replying_to=None)
        await message.answer("Sizning habaringiz yuborildi")
    else:
        await message.answer("❌ Javob berish uchun xabar tanlanmadi!")

# Callback query handler: "Suhbatni yakunlash" tugmasi bosilganda
@dp.callback_query_handler(lambda call: call.data == "end_conversation")
async def end_conversation_handler(call: types.CallbackQuery, state: FSMContext):
    logging.info("End conversation callback triggered for user: %s", call.from_user.id)
    try:
        # Darhol callbackga javob qaytarish
        await call.answer("Suhbat tugatildi", show_alert=False)
    except Exception as e:
        logging.error("Error in call.answer: %s", e)
    # Inline klaviaturani olib tashlash uchun ikki usulni sinab ko'ramiz:
    try:
        # 1-usul: call.message.edit_reply_markup
        await call.message.edit_reply_markup(reply_markup=None)
        logging.info("Inline keyboard removed using call.message.edit_reply_markup")
    except Exception as e:
        logging.error("Error in call.message.edit_reply_markup: %s", e)
        try:
            # 2-usul: bot.edit_message_reply_markup
            await bot.edit_message_reply_markup(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=None
            )
            logging.info("Inline keyboard removed using bot.edit_message_reply_markup")
        except Exception as e:
            logging.error("Error in bot.edit_message_reply_markup: %s", e)
    try:
        # Foydalanuvchi holatini tozalash
        await state.finish()
    except Exception as e:
        logging.error("Error finishing state: %s", e)
    try:
        # Adminga "Suhbat yakunlandi" habar yuborish
        await bot.send_message(ADMIN_ID, "Suhbat yakunlandi")
    except Exception as e:
        logging.error("Error sending admin message: %s", e)
    # Boshlang'ich menyuni qayta yuborish
    text = ("Assalom Aleykum!\n"
            "🧑‍💻Siz anketa kanal admini bilan aloqa botidasiz.\n"
            "Marhamat, pastdagi menulardan muloqot tilini tanlang:")
    text_ru = ("Здравствуйте!\n"
               "🧑‍💻Вы находитесь в боте связи с администратором канала анкет.\n"
               "Пожалуйста, выберите язык общения из меню ниже:")
    text_en = ("Hello!\n"
               "🧑‍💻You are in the questionnaire channel admin contact bot.\n"
               "Please select a communication language from the menu below:")
    try:
        await bot.send_message(call.message.chat.id, f"{text}\n\n{text_ru}\n\n{text_en}", reply_markup=language_keyboard)
        await ChatState.language.set()
    except Exception as e:
        logging.error("Error sending start message: %s", e)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)