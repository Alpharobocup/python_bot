import os
import telebot
from flask import Flask, request
import re
from datetime import datetime, timedelta

API_TOKEN = os.environ.get("BOT_TOKEN")  # باید توی Render تعریف بشه
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")  # مثل: https://your-app.onrender.com
WEBHOOK_PATH = f"/bot{API_TOKEN}"
OWNER_ID = 1656900957  # آی‌دی خاص که اجازه کامل داره

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

# بررسی دسترسی کاربر
def is_authorized(chat_id, user_id):
    try:
        member = bot.get_chat_member(chat_id, user_id)
        return member.status in ["administrator", "creator"] or user_id == OWNER_ID
    except:
        return False

# /start
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "سلام! ربات روی Render اجرا شد 🚀")

# پاکسازی نامحدود گروه
@bot.message_handler(func=lambda m: m.text == "پاکسازی مستر")
def clean_all(message):
    if not is_admin(message.chat.id, message.from_user.id):
        return
    try:
        # حذف همه پیام‌های قابل مشاهده
        for msg in bot.get_chat_history(message.chat.id, limit=100):  # عدد بزرگ برای پیام‌های زیاد
            try:
                bot.delete_message(message.chat.id, msg.message_id)
            except:
                pass
        bot.send_message(message.chat.id, "پاکسازی انجام شد ✅")
    except Exception as e:
        bot.send_message(message.chat.id, f"خطا در پاکسازی: {e}")

# سکوت دادن
@bot.message_handler(func=lambda m: m.text.startswith("سکوت"))
def mute_user(message):
    if not is_authorized(message.chat.id, message.from_user.id):
        return
    pattern = r"^سکوت(?: (\d+))?(?: (دقیقه|ساعت))?$"
    match = re.match(pattern, message.text)
    if not match:
        return
    amount = int(match.group(1)) if match.group(1) else 1
    unit = match.group(2) if match.group(2) else "دقیقه"
    until = datetime.now() + timedelta(minutes=amount) if unit == "دقیقه" else datetime.now() + timedelta(hours=amount)
    
    target = None
    if message.reply_to_message:
        target = message.reply_to_message.from_user.id
    else:
        bot.reply_to(message, "لطفاً روی پیام کاربر ریپلای کنید.")
        return
    
    try:
        bot.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=target,
            until_date=until,
            can_send_messages=False
        )
        bot.reply_to(message, f"کاربر سکوت شد برای {amount} {unit} ✅")
    except:
        bot.reply_to(message, "خطا در اعمال سکوت ❌")

# رفع سکوت
@bot.message_handler(func=lambda m: m.text == "رفع سکوت")
def unmute_user(message):
    if not is_authorized(message.chat.id, message.from_user.id):
        return
    if not message.reply_to_message:
        bot.reply_to(message, "لطفاً روی پیام کاربر ریپلای کنید.")
        return
    target = message.reply_to_message.from_user.id
    try:
        bot.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=target,
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True
        )
        bot.reply_to(message, "سکوت کاربر برداشته شد ✅")
    except:
        bot.reply_to(message, "خطا در رفع سکوت ❌")

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
            bot.reply_to(message, f"خطا در حذف: ")

    # حالت ۳: حذف با user_id عددی
    elif len(args) > 1 and args[1].isdigit():
        user_id = int(args[1])
        try:
            bot.kick_chat_member(chat_id, user_id)
            bot.reply_to(message, f"کاربر {user_id} حذف شد ✅")
        except Exception as e:
            bot.reply_to(message, f"خطا در حذف")

    else:
        bot.reply_to(message, "❌ لطفاً دستور رو به‌درستی وارد کنید.\nمثال: \n- ریپلای روی پیام و نوشتن «حذف»\n- حذف @username\n- حذف 123456789")

# وبهوک
@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    json_str = request.stream.read().decode("UTF-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "ok", 200

# صفحه اصلی
@app.route("/")
def home():
    return "ربات فعال است ✅"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL + WEBHOOK_PATH)
    app.run(host="0.0.0.0", port=port)
