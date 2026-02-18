import logging
import json
import sqlite3
import base64
import io

from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
    WebAppInfo, InputFile
)

from config import BOT_TOKEN, ADMIN_ID, WEBAPP_URL

# ===== SETUP =====
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# ===== DATABASE =====
db = sqlite3.connect("greenpay.db")
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS trees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    user_name TEXT,
    tree TEXT,
    latitude REAL,
    longitude REAL,
    status TEXT
)
""")
db.commit()

# ===== KEYBOARD =====
main_kb = ReplyKeyboardMarkup(resize_keyboard=True)
main_kb.add(
    KeyboardButton(
        "🌱 Daraxt ekish",
        web_app=WebAppInfo(url=WEBAPP_URL)
    ),
    KeyboardButton("💰 Balans")
)

# ===== START =====
@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    await msg.answer(
        "🌳 GreenPay ga xush kelibsiz!\n\n"
        "Daraxt eking, tasdiqlang va mukofot oling.",
        reply_markup=main_kb
    )

# ===== BALANS =====
@dp.message_handler(lambda m: m.text == "💰 Balans")
async def balance(msg: types.Message):
    await msg.answer("💰 Balans: 0 so‘m (test rejim)")

# ===== MINI APP DATA =====
@dp.message_handler(content_types=types.ContentType.WEB_APP_DATA)
async def web_app_data(msg: types.Message):
    data = json.loads(msg.web_app_data.data)

    # Rasmni decode qilish
    photo_data = data["photo"].split(",")[1]
    photo_bytes = base64.b64decode(photo_data)
    photo_file = InputFile(io.BytesIO(photo_bytes), filename="tree.jpg")

    # DB saqlash
    cursor.execute("""
    INSERT INTO trees (user_id, user_name, tree, latitude, longitude, status)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (
        msg.from_user.id,
        msg.from_user.full_name,
        data["tree"],
        data["latitude"],
        data["longitude"],
        "pending"
    ))
    db.commit()

    tree_id = cursor.lastrowid

    # Admin tugmalari
    admin_kb = InlineKeyboardMarkup()
    admin_kb.add(
        InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"approve_{tree_id}"),
        InlineKeyboardButton("❌ Rad etish", callback_data=f"reject_{tree_id}")
    )

    await bot.send_photo(
        ADMIN_ID,
        photo=photo_file,
        caption=(
            f"🌳 *Yangi daraxt*\n"
            f"👤 {msg.from_user.full_name}\n"
            f"🌳 {data['tree']}\n"
            f"📍 {data['latitude']}, {data['longitude']}\n"
            f"🆔 ID: {tree_id}"
        ),
        reply_markup=admin_kb,
        parse_mode="Markdown"
    )

    await msg.answer("✅ Ma’lumot yuborildi. Tekshiruvda.")

# ===== ADMIN =====
@dp.callback_query_handler(lambda c: c.data.startswith("approve_"))
async def approve(call: types.CallbackQuery):
    tree_id = call.data.split("_")[1]

    cursor.execute("UPDATE trees SET status='approved' WHERE id=?", (tree_id,))
    db.commit()

    cursor.execute("SELECT user_id FROM trees WHERE id=?", (tree_id,))
    user_id = cursor.fetchone()[0]

    await bot.send_message(user_id, "🎉 Daraxtingiz tasdiqlandi!")
    await call.message.edit_caption(call.message.caption + "\n\n✅ Tasdiqlandi")

@dp.callback_query_handler(lambda c: c.data.startswith("reject_"))
async def reject(call: types.CallbackQuery):
    tree_id = call.data.split("_")[1]

    cursor.execute("UPDATE trees SET status='rejected' WHERE id=?", (tree_id,))
    db.commit()

    cursor.execute("SELECT user_id FROM trees WHERE id=?", (tree_id,))
    user_id = cursor.fetchone()[0]

    await bot.send_message(user_id, "❌ Daraxtingiz rad etildi.")
    await call.message.edit_caption(call.message.caption + "\n\n❌ Rad etildi")

# ===== RUN =====
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
