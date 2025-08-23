import os
import telebot
from flask import Flask, request
from datetime import timedelta

API_TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL") 
WEBHOOK_PATH = f"/bot{API_TOKEN}"

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

# یک آی‌دی خاص که همیشه دسترسی ویژه داره
MASTER_ID = 123456789  # اینجا آی‌دی خودت رو بذار

# تابع بررسی ادمین بودن
def is_admin(chat_id, user_id):
    if user_id == MASTER_ID:
        return True
    try:
        member = bot.get_chat_member(chat_id, user_id)
        return member.status in ["administrator", "creator"]
    except:
        return False


# ----------------- دستورات ----------------- #

# 1) پاکسازی گروه
@bot.message_handler(commands=['پاکسازی'])
def clear_chat(message):
    if not is_admin(message.chat.id, message.from_user.id):
        return bot.reply_to(message, "⛔ فقط ادمین‌ها می‌تونن این دستور رو بزنن.")

    try:
        # گرفتن لیست پیام‌ها و پاک کردن تا حد امکان
        for msg_id in range(message.message_id, message.message_id - 100, -1):
            try:
                bot.delete_message(message.chat.id, msg_id)
            except:
                pass
        bot.send_message(message.chat.id, "✅ گروه پاکسازی شد (تا حد دسترسی ربات).")
    except Exception as e:
        bot.reply_to(message, f"⚠️ خطا: {e}")


# 2) سکوت کاربر
@bot.message_handler(func=lambda m: m.text and m.text.startswith("سکوت"))
def mute_user(message):
    if not is_admin(message.chat.id, message.from_user.id):
        return bot.reply_to(message, "⛔ فقط ادمین‌ها می‌تونن این دستور رو بزنن.")

    args = message.text.split()
    duration = 1  # دیفالت ۱ دقیقه
    unit = "minute"

    if len(args) >= 2:
        try:
            duration = int(args[1])
        except:
            duration = 1
        if len(args) == 3 and args[2].lower() in ["ساعت", "hour", "hours"]:
            unit = "hour"

    seconds = duration * 60 if unit == "minute" else duration * 3600

    target = None
    if message.reply_to_message:  # سکوت روی ریپلای
        target = message.reply_to_message.from_user.id

    if target:
        try:
            bot.restrict_chat_member(
                message.chat.id,
                target,
                until_date=timedelta(seconds=seconds),
                can_send_messages=False
            )
            bot.reply_to(message, f"🔇 کاربر برای {duration} {unit}(s) سکوت شد.")
        except Exception as e:
            bot.reply_to(message, f"⚠️ خطا در سکوت کاربر: {e}")
    else:
        bot.reply_to(message, "⚠️ باید روی پیام طرف ریپلای کنید تا سکوت بشه.")


# 3) حذف کاربر
@bot.message_handler(func=lambda m: m.text and "حذف" in m.text)
def kick_user(message):
    if not is_admin(message.chat.id, message.from_user.id):
        return bot.reply_to(message, "⛔ فقط ادمین‌ها می‌تونن این دستور رو بزنن.")

    target = None
    if message.reply_to_message:  # حالت ریپلای
        target = message.reply_to_message.from_user.id
    else:
        parts = message.text.split()
        if len(parts) == 2 and parts[1].startswith("@"):
            try:
                user = bot.get_chat_member(message.chat.id, parts[1])
                target = user.user.id
            except:
                pass

    if target:
        try:
            bot.kick_chat_member(message.chat.id, target)
            bot.reply_to(message, "🚷 کاربر حذف شد.")
        except Exception as e:
            bot.reply_to(message, f"⚠️ خطا در حذف کاربر: {e}")
    else:
        bot.reply_to(message, "⚠️ باید روی پیام ریپلای کنید یا یوزرنیم وارد کنید.")


# ----------------- وبهوک ----------------- #

@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    json_str = request.stream.read().decode("UTF-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "ok", 200

@app.route("/")
def home():
    return "ربات فعال است ✅"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL + WEBHOOK_PATH)
    app.run(host="0.0.0.0", port=port)
