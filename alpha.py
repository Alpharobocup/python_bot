import os
import telebot
from flask import Flask, request
from datetime import datetime, timedelta

API_TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL") 
WEBHOOK_PATH = f"/bot{API_TOKEN}"

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

# آی‌دی مستر
MASTER_ID = 1656900957  

# تابع چک ادمین
def is_admin(chat_id, user_id):
    if user_id == MASTER_ID:
        return True
    try:
        member = bot.get_chat_member(chat_id, user_id)
        return member.status in ["administrator", "creator"]
    except:
        return False


# ----------------- دستورات ----------------- #

# پاکسازی گروه
@bot.message_handler(commands=['پاکسازی'])
def clear_chat(message):
    if not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "⛔ فقط ادمین‌ها می‌تونن این دستور رو بزنن.")
        return

    deleted = 0
    for msg_id in range(message.message_id, message.message_id - 300, -1):
        try:
            bot.delete_message(message.chat.id, msg_id)
            deleted += 1
        except:
            pass
    bot.send_message(message.chat.id, f"✅ {deleted} پیام پاک شد (تا حد دسترسی ربات).")


# سکوت کاربر
@bot.message_handler(func=lambda m: m.text and m.text.startswith("سکوت"))
def mute_user(message):
    if not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "⛔ فقط ادمین‌ها می‌تونن این دستور رو بزنن.")
        return

    args = message.text.split()
    duration = 1
    unit = "minute"

    if len(args) >= 2:
        try:
            duration = int(args[1])
        except:
            duration = 1
        if len(args) == 3 and args[2].lower() in ["ساعت", "hour", "hours"]:
            unit = "hour"

    seconds = duration * 60 if unit == "minute" else duration * 3600
    until = datetime.now() + timedelta(seconds=seconds)

    target = message.reply_to_message.from_user.id if message.reply_to_message else None

    if target:
        try:
            bot.restrict_chat_member(
                message.chat.id,
                target,
                until_date=until,
                can_send_messages=False
            )
            bot.reply_to(message, f"🔇 کاربر برای {duration} {unit}(s) سکوت شد.")
        except Exception as e:
            bot.reply_to(message, f"⚠️ خطا در سکوت کاربر: {e}")
    else:
        bot.reply_to(message, "⚠️ باید روی پیام طرف ریپلای کنید.")


@bot.message_handler(func=lambda message: message.text and message.text.startswith("حذف"))
def delete_user(message):
    chat_id = message.chat.id
    args = message.text.split()

    # حالت ۱: ریپلای به پیام
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        try:
            bot.kick_chat_member(chat_id, user_id)
            bot.reply_to(message, f"کاربر {message.reply_to_message.from_user.first_name} حذف شد ✅")
        except Exception as e:
            bot.reply_to(message, f"خطا در حذف: {e}")

    # حالت ۲: حذف با یوزرنیم
    elif len(args) > 1 and args[1].startswith("@"):
        username = args[1]
        try:
            user = bot.get_chat(username)  # تبدیل یوزرنیم → آی‌دی
            bot.kick_chat_member(chat_id, user.id)
            bot.reply_to(message, f"کاربر {username} حذف شد ✅")
        except Exception as e:
            bot.reply_to(message, f"خطا در حذف {username}: {e}")

    # حالت ۳: حذف با user_id عددی
    elif len(args) > 1 and args[1].isdigit():
        user_id = int(args[1])
        try:
            bot.kick_chat_member(chat_id, user_id)
            bot.reply_to(message, f"کاربر {user_id} حذف شد ✅")
        except Exception as e:
            bot.reply_to(message, f"خطا در حذف: {e}")

    else:
        bot.reply_to(message, "❌ لطفاً دستور رو به‌درستی وارد کنید.\nمثال: \n- ریپلای روی پیام و نوشتن «حذف»\n- حذف @username\n- حذف 123456789")



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
