import os
import datetime
import jdatetime
from hijri_converter import convert
import requests
from flask import Flask, request
import telebot

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

# 📌 تابع محاسبه تقویم
def get_calendar_info():
    now = datetime.datetime.now()

    # تاریخ میلادی
    gregorian_date = now.strftime("%Y-%m-%d")

    # تاریخ شمسی
    persian_date = jdatetime.date.fromgregorian(date=now).strftime("%Y-%m-%d")

    # تاریخ قمری
    hijri_date = convert.Gregorian(now.year, now.month, now.day).to_hijri()
    hijri_str = f"{hijri_date.day}-{hijri_date.month}-{hijri_date.year}"

    # ساعت دقیق
    time_now = now.strftime("%H:%M:%S")

    # درصد سال گذشته و مانده
    start_year = datetime.datetime(now.year, 1, 1)
    end_year = datetime.datetime(now.year + 1, 1, 1)
    total_days = (end_year - start_year).days
    passed_days = (now - start_year).days
    left_days = total_days - passed_days
    percent_passed = round((passed_days / total_days) * 100, 2)

    info = f"📅 تقویم امروز\n\n"
    info += f"🌞 شمسی: {persian_date}\n"
    info += f"🌍 میلادی: {gregorian_date}\n"
    info += f"🌙 قمری: {hijri_str}\n\n"
    info += f"⏰ ساعت: {time_now}\n\n"
    info += f"📊 گذشته از سال: {passed_days} روز ({percent_passed}%)\n"
    info += f"📊 مانده تا پایان سال: {left_days} روز\n"

    return info

# 📌 مناسبت‌ها (از keybit.ir)
def get_events():
    try:
        res = requests.get("https://api.keybit.ir/public/calendar")
        data = res.json()
        events = data.get("events", [])
        if events:
            return "📌 مناسبت‌های امروز:\n" + "\n".join(["- " + e["title"] for e in events])
        else:
            return "📌 امروز مناسبت خاصی نداره."
    except:
        return "⚠️ خطا در دریافت مناسبت‌ها."

# 📌 هندلر تقویم
def handle_calendar(message):
    cal_info = get_calendar_info()
    events_info = get_events()
    bot.send_message(message.chat.id, cal_info + "\n\n" + events_info)

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
    elif "تقویم" in text:
        handle_calendar(message)
    elif text.startswith("سکو"):
        parts = text.split()
        if len(parts) > 1 and parts[1].isdigit():
            mute_user(message, int(parts[1]))
        else:
            mute_user(message, 1)
    elif text.startswith("رف"):
        unmute_user(message)
    elif "دل" in text:
        delete_message(message)
    elif repeat_mode:
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
