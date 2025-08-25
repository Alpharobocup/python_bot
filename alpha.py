
import os
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

def mute_user(message, minutes):
    user_id = message.reply_to_message.from_user.id if message.reply_to_message else None
    if user_id:
        mute_users[user_id] = minutes
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
    text = message.text.strip()
    
    if "حالت تکرار روشن" in text:
        set_repeat_on(message)
    elif "حالت تکرار خاموش" in text:
        set_repeat_off(message)
    elif text.startswith("سکو"):
        parts = text.split()
        if len(parts) > 1 and parts[1].isdigit():
            mute_user(message, int(parts[1]))
        else:
            mute_user(message, 0)
    elif text.startswith("رف"):
        unmute_user(message)
    elif "حذف" in text:
        delete_message(message)
    elif repeat_mode:
        bot.reply_to(message, text)

# ===== بررسی سکوت کاربران =====
@bot.message_handler(func=lambda m: True)
def check_mute(message):
    user_id = message.from_user.id
    if user_id in mute_users:
        bot.delete_message(message.chat.id, message.message_id)

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

