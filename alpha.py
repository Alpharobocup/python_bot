import os
import datetime
import jdatetime
from hijri_converter import convert
import requests
from flask import Flask, request
import telebot
import pytz



# ===== دریافت توکن و پورت از محیط رندر =====
TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")  # مثلا: https://your-app.onrender.com
PORT = int(os.environ.get("PORT", 5000))

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# ===== حالت‌ها =====
repeat_mode = False
mute_users = {}

# ===== توابع =====
def set_repeat_on(message):
    global repeat_mode
    repeat_mode = True
    bot.reply_to(message, "حالت تکرار روشن شد ✅")

def set_repeat_off(message):
    global repeat_mode
    repeat_mode = False
    bot.reply_to(message, "حالت تکرار خاموش شد ❌")



# مسیر عکس‌ها
PICTURE_FOLDER = "pictures"  # پوشه‌ای که 12 عکس ماه‌ها اینجاست
MONTH_IMAGES = {
    1: "farvardin.png",
    2: "ordibehesht.png",
    3: "khordad.png",
    4: "tir.png",
    5: "mordad.png",
    6: "shahrivar.png",
    7: "mehr.png",
    8: "aban.png",
    9: "azar.png",
    10: "dey.png",
    11: "bahman.png",
    12: "esfand.png"
}


# 📌 تابع محاسبه تقویم
def get_calendar_info():
    tz = pytz.timezone("Asia/Tehran")
    now = datetime.datetime.now(tz)
    gregorian_date = now.strftime("%Y-%m-%d")
    persian_date_obj = jdatetime.date.fromgregorian(date=now)
    persian_date_text = persian_date_obj.strftime("%-d %B %Y")
    hijri_date = convert.Gregorian(now.year, now.month, now.day).to_hijri()
    hijri_str = f"{hijri_date.day}-{hijri_date.month}-{hijri_date.year}"
    time_now = now.strftime("%H:%M:%S")
    start_year = jdatetime.date(persian_date_obj.year, 1, 1).togregorian()
    end_year = jdatetime.date(persian_date_obj.year + 1, 1, 1).togregorian()
    total_days = (end_year - start_year).days
    passed_days = (now.date() - start_year).days
    left_days = total_days - passed_days
    percent_passed = round((passed_days / total_days) * 100, 2)

    info = f"📅 تقویم امروز\n\n"
    info += f"🌞 شمسی: {persian_date_text}\n"
    info += f"🌍 میلادی: {gregorian_date}\n"
    info += f"🌙 قمری: {hijri_str}\n\n"
    info += f"⏰ ساعت (تهران): {time_now}\n\n"
    info += f"📊 گذشته از سال شمسی: {passed_days} روز ({percent_passed}%)\n"
    info += f"📊 مانده تا پایان سال: {left_days} روز\n"

    return info

# 📌 هندلر تقویم (دستی)
def handle_calendar_manual(message):
    info = get_calendar_info()
    bot.send_message(message.chat.id, info)

# 📌 ارسال عکس ماه روزانه
def send_month_picture(chat_id):
    tz = pytz.timezone("Asia/Tehran")
    now = datetime.datetime.now(tz)
    persian_date_obj = jdatetime.date.fromgregorian(date=now)
    month_number = persian_date_obj.month
    month_image_file = MONTH_IMAGES.get(month_number)

    if month_image_file:
        photo_path = os.path.join(PICTURE_FOLDER, month_image_file)
        caption = get_calendar_info()  # کپشن همان تقویم امروز
        if os.path.exists(photo_path):
            with open(photo_path, "rb") as photo:
                bot.send_photo(chat_id, photo, caption=caption)
        else:
            bot.send_message(chat_id, f"⚠️ عکس ماه {month_number} موجود نیست.")
    else:
        bot.send_message(chat_id, "⚠️ ماه نامشخص!")

# مثال: برای استفاده روزانه
# send_month_picture(CHAT_ID)  # اینجا CHAT_ID کانال یا گروه شماست

# ===== سکوت و مدیریت =====
def mute_user(message, minutes):
    user_id = message.reply_to_message.from_user.id if message.reply_to_message else None
    if user_id:
        mute_users[user_id] = datetime.datetime.now() + datetime.timedelta(minutes=minutes)
        bot.reply_to(message, f"کاربر سکوت شد برای {minutes} دقیقه 🔇")

def unmute_user(message):
    user_id = message.reply_to_message.from_user.id if message.reply_to_message else None
    if user_id and user_id in mute_users:
        del mute_users[user_id]
        bot.reply_to(message, "سکوت کاربر برداشته شد 🔊")

def delete_message(message):
    if message.reply_to_message:
        bot.delete_message(message.chat.id, message.reply_to_message.message_id)
        bot.reply_to(message, "پیام حذف شد 🗑️")

def set_group_photo(message):
    if "قرار بده" in message.text:  # هر دستوری که بخوای میتونی تغییر بدی
        try:
            # گرفتن فایل عکس
            file_id = message.reply_to_message.photo[-1].file_id
            file_info = bot.get_file(file_id)
            downloaded_file = bot.download_file(file_info.file_path)

            # ذخیره موقت عکس
            with open("group_photo.jpg", "wb") as new_file:
                new_file.write(downloaded_file)

            # تغییر عکس گروه
            with open("group_photo.jpg", "rb") as photo:
                bot.set_chat_photo(chat_id=message.chat.id, photo=photo)

            bot.reply_to(message, "📸 عکس گروه با موفقیت تغییر کرد ✅")

        except Exception as e:
            bot.reply_to(message, f"❌ خطا در تغییر عکس گروه: {e}")









# ===== هندل پیام‌ها =====
@bot.message_handler(func=lambda m: True)
def handle_text(message):
    global repeat_mode

    user_id = message.from_user.id
    now = datetime.datetime.now()

    # بررسی سکوت
    if user_id in mute_users and mute_users[user_id] > now:
        bot.delete_message(message.chat.id, message.message_id)
        return

    text = message.text.strip()
    if "تکرار روشن" in text:
        set_repeat_on(message)
    elif "تکرار خاموش" in text:
        set_repeat_off(message)
    if "تقویم" in text:
        handle_calendar_manual(message)
    if text.startswith("سکو"):
        parts = text.split()
        if len(parts) > 1 and parts[1].isdigit():
            mute_user(message, int(parts[1]))
        else:
            mute_user(message, 1)
    if text.startswith("رف"):
        unmute_user(message)
    if "دل" in text:
        delete_message(message)
    # ریپلای روی عکس → قرار دادن عکس در گروه
    if message.reply_to_message and message.reply_to_message.content_type == "photo" and text =="قرار بده":
        set_group_photo(message)

    if repeat_mode:
        bot.reply_to(message, text)

# ===== وب هوک =====
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    json_str = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "!", 200

@app.route("/")
def index():
    return "Bot is running!", 200

# ===== ست کردن وب هوک =====
bot.remove_webhook()
bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}")

# ===== اجرای Flask =====
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
