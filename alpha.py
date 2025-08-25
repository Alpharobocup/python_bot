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

OWNER_ID = 1656900957
repeat_mode = False
mute_timers = {}
user_silenced = {}

welcome_messages = [
    "سلام {name} به گروه {group} خوش اومدی! 🌟",
    "خوش آمدی {name}! گروه {group} منتظرته 😎",
    "به جمع ما خوش اومدی {name}! توی {group} خوش بگذرون 🙂",
]

@bot.message_handler(content_types=['new_chat_members'])
def welcome(message):
    for member in message.new_chat_members:
        text = random.choice(welcome_messages).format(name=member.first_name, group=message.chat.title)
        try:
            photo = bot.get_chat(message.chat.id).photo
            if photo:
                bot.send_photo(message.chat.id, photo.file_id, caption=text)
            else:
                bot.send_message(message.chat.id, text)
        except:
            bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: True, content_types=['text'])
def reply_info(message):
    if message.reply_to_message and "اطلاعات" in message.text:
        user = message.reply_to_message.from_user
        info = f"""
📌 اطلاعات کاربر:
👤 نام: {user.first_name or '-'} {user.last_name or '-'}
🔗 یوزرنیم: @{user.username if user.username else 'ندارد'}
🆔 آیدی عددی: {user.id}
🌐 زبان: {user.language_code or 'نامشخص'}
🤖 ربات هست؟ {"بله" if user.is_bot else "خیر"}
        """
        bot.reply_to(message, info)

@bot.message_handler(func=lambda m: True, content_types=['text','sticker','video','photo','animation','audio','voice'])
def handle_message(message):
    global repeat_mode

    user_id = message.from_user.id
    text = message.text or ""
    try:
        admins = [a.user.id for a in bot.get_chat_administrators(message.chat.id)]
    except:
        admins = []
    is_admin = user_id == OWNER_ID or user_id in admins

    if text.strip() == "پاکسازی مستر" and is_admin:
        try:
            for msg in bot.get_chat_history(message.chat.id, limit=100):
                bot.delete_message(message.chat.id, msg.message_id)
        except:
            pass
        return

    if text.startswith("سکوت") and is_admin:
        parts = text.split()
        duration = 1
        if len(parts) == 2:
            duration = int(parts[1])
        elif len(parts) == 3 and parts[2].lower().startswith("ساعت"):
            duration = int(parts[1]) * 60
        mute_until = datetime.now() + timedelta(minutes=duration)
        mute_timers[message.chat.id] = mute_until
        bot.reply_to(message, f"کاربر سکوت شد تا {mute_until.strftime('%H:%M')}")

    if text.startswith("رفع سکوت") and is_admin:
        if message.reply_to_message:
            uid = message.reply_to_message.from_user.id
            if uid in user_silenced:
                del user_silenced[uid]
                bot.reply_to(message, f"{message.reply_to_message.from_user.first_name} از سکوت خارج شد.")
            else:
                bot.reply_to(message, "این کاربر در حالت سکوت نیست.")
        else:
            bot.reply_to(message, "لطفاً ریپلای روی کاربر مورد نظر بزنید.")

    if text.startswith("حذف") and is_admin:
        chat_id = message.chat.id
        args = text.split()
        if message.reply_to_message:
            uid = message.reply_to_message.from_user.id
        elif len(args) > 1 and args[1].isdigit():
            uid = int(args[1])
        else:
            uid = None

        if uid:
            try:
                bot.kick_chat_member(chat_id, uid)
                bot.reply_to(message, f"کاربر {uid} حذف شد ✅")
            except Exception as e:
                bot.reply_to(message, f"خطا در حذف: {e}")

    if repeat_mode:
        try:
            if message.content_type == 'text':
                bot.send_message(message.chat.id, message.text)
            elif message.content_type == 'sticker':
                bot.send_sticker(message.chat.id, message.sticker.file_id)
            elif message.content_type == 'video':
                bot.send_video(message.chat.id, message.video.file_id)
            elif message.content_type == 'photo':
                bot.send_photo(message.chat.id, message.photo[-1].file_id)
            elif message.content_type == 'animation':
                bot.send_animation(message.chat.id, message.animation.file_id)
            elif message.content_type == 'audio':
                bot.send_audio(message.chat.id, message.audio.file_id)
            elif message.content_type == 'voice':
                bot.send_voice(message.chat.id, message.voice.file_id)
        except:
            pass

@bot.message_handler(func=lambda m: m.text == "حالت تکرار روشن")
def repeat_on(message):
    global repeat_mode
    repeat_mode = True
    bot.reply_to(message, "حالت تکرار روشن شد ✅")

@bot.message_handler(func=lambda m: m.text == "حالت تکرار خاموش")
def repeat_off(message):
    global repeat_mode
    repeat_mode = False
    bot.reply_to(message, "حالت تکرار خاموش شد ❌")

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
