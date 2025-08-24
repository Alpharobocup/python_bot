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
    for msg_id in range(message.message_id, message.message_id - 50, -1):
        try:
            bot.delete_message(message.chat.id, msg_id)
            deleted += 1
        except:
            pass
    bot.send_message(message.chat.id, f"✅ {deleted} پیام پاک شد (تا حد دسترسی ربات).")

# رفع سکوت
@bot.message_handler(commands=['unsilence'])
def unsilence_user(message):
    if not message.reply_to_message:
        bot.reply_to(message, "باید روی پیام کاربر ریپلای کنی ❗")
        return
    
    user_id = message.reply_to_message.from_user.id
    chat_id = message.chat.id
    
    try:
        bot.restrict_chat_member(
            chat_id,
            user_id,
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_polls=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True,
            can_change_info=True,
            can_invite_users=True,
            can_pin_messages=True
        )
        bot.reply_to(message, "✅ سکوت کاربر برداشته شد")
    except Exception as e:
        bot.reply_to(message, f"خطا در رفع سکوت: {e}")
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


@bot.message_handler(func=lambda m: m.text and m.text.lower().startswith("حذف"))
def delete_user(message):
    allowed_users = [1656900957]  # ایدی کاربر خاص
    chat_id = message.chat.id
    
    # بررسی ادمین بودن یا مالک بودن
    member = bot.get_chat_member(chat_id, message.from_user.id)
    if member.status not in ["administrator", "creator"] and message.from_user.id not in allowed_users:
        bot.reply_to(message, "❌ شما اجازه این کار را ندارید")
        return
    
    # حذف با ریپلای
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        bot.kick_chat_member(chat_id, target_id)
        bot.reply_to(message, "✅ کاربر حذف شد")
        return
    
    # حذف با یوزرنیم
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "❌ باید یوزرنیم کاربر را وارد کنید")
        return
    
    username = parts[1].replace("@", "")
    try:
        # پیدا کردن user_id با username
        for member in bot.get_chat_administrators(chat_id) + [bot.get_chat_member(chat_id, message.from_user.id)]:
            if member.user.username and member.user.username.lower() == username.lower():
                bot.kick_chat_member(chat_id, member.user.id)
                bot.reply_to(message, f"✅ کاربر @{username} حذف شد")
                return
        
        bot.reply_to(message, "❌ کاربر پیدا نشد یا ربات دسترسی ندارد")
    except Exception as e:
        bot.reply_to(message, f"خطا در حذف کاربر: {e}")



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
