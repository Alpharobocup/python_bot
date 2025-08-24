import os
import telebot
from flask import Flask, request
import random
from datetime import datetime, timedelta

API_TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
WEBHOOK_PATH = f"/bot{API_TOKEN}"

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

# ======= تنظیمات ==========
OWNER_ID = 1656900957  # آی‌دی مشخص
repeater_on = False
mute_timers = {}

welcome_messages = [
    "سلام {name} به گروه {group} خوش اومدی! 🌟",
    "خوش آمدی {name}! گروه {group} منتظرته 😎",
    "به جمع ما خوش اومدی {name}! توی {group} خوش بگذرون 🙂",
]

# ======= هندلر خوشامدگویی =======
@bot.message_handler(content_types=['new_chat_members'])
def welcome(message):
    for member in message.new_chat_members:
        text = random.choice(welcome_messages).format(name=member.first_name, group=message.chat.title)
        try:
            photo = bot.get_chat(message.chat.id).photo  # اگر پروفایل گروه موجود باشد
            if photo:
                bot.send_photo(message.chat.id, photo.file_id, caption=text)
            else:
                bot.send_message(message.chat.id, text)
        except:
            bot.send_message(message.chat.id, text)

# ======= هندلر پیام‌ها =======
@bot.message_handler(func=lambda m: True)
def handle_message(message):
    global repeater_on
    
    user_id = message.from_user.id
    text = message.text or ""
    
    # فقط ادمین‌ها، مالک و OWNER_ID مجاز
    is_admin = (user_id == OWNER_ID) or message.from_user.id in [a.user.id for a in bot.get_chat_administrators(message.chat.id)]
    
    # ======= پاکسازی =======
    if text.strip() == "پاکسازی مستر" and is_admin:
        try:
            for msg in bot.get_chat_history(message.chat.id, limit=100):  # می‌تونی limit رو بالا ببری
                bot.delete_message(message.chat.id, msg.message_id)
        except:
            pass
        return

    # ======= سکوت =======
    if text.startswith("سکوت") and is_admin:
        parts = text.split()
        duration = 1  # پیش فرض دقیقه
        if len(parts) == 2:
            duration = int(parts[1])
        elif len(parts) == 3 and parts[2].lower().startswith("ساعت"):
            duration = int(parts[1]) * 60
        
        mute_until = datetime.now() + timedelta(minutes=duration)
        mute_timers[message.chat.id] = mute_until
        bot.reply_to(message, f"کاربر سکوت شد تا {mute_until.strftime('%H+3:%M+30')}")
        return
    
# رفع سکوت
@bot.message_handler(func=lambda m: m.text == "رفع سکوت")
def unmute_user(message):
    if message.from_user.id in admins + [owner_id, special_user_id]:
        if message.reply_to_message:
            uid = message.reply_to_message.from_user.id
            if uid in user_silenced:
                del user_silenced[uid]
                bot.reply_to(message, f"{message.reply_to_message.from_user.first_name} از سکوت خارج شد.")
            else:
                bot.reply_to(message, "این کاربر در حالت سکوت نیست.")
        else:
            bot.reply_to(message, "لطفاً ریپلای روی کاربر مورد نظر بزنید.")


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

    # حالت ۳: حذف با user_id عددی
    elif len(args) > 1 and args[1].isdigit():
        user_id = int(args[1])
        try:
            bot.kick_chat_member(chat_id, user_id)
            bot.reply_to(message, f"کاربر {user_id} حذف شد ✅")
        except Exception as e:
            bot.reply_to(message, f"خطا در حذف: {e}")

    else:
        bot.reply_to(message, "❌ لطفاً دستور رو به‌درستی وارد کنید.\nمثال: \n- ریپلای روی پیام و نوشتن «حذف»\n- حذف 123456789")
    
    # ======= حالت تکرار =======
    if text.strip() == "تکرار روشن" and is_admin:
        repeater_on = True
        bot.reply_to(message, "حالت تکرار روشن شد ✅")
        return
    if text.strip() == "تکرار خاموش" and is_admin:
        repeater_on = False
        bot.reply_to(message, "حالت تکرار خاموش شد ❌")
        return
    
    # ======= اگر حالت تکرار فعال باشد =======
    if repeater_on:
        try:
            bot.forward_message(message.chat.id, message.chat.id, message.message_id)
        except:
            pass

# ======= وبهوک =======
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
