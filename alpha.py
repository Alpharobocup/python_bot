import os
import telebot
from flask import Flask, request

API_TOKEN = os.environ.get("BOT_TOKEN")  # باید توی Render در Environment Variables تعریف کنی
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")  # مثلا https://your-app.onrender.com
WEBHOOK_PATH = f"/bot{API_TOKEN}"

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

# هندلر دستور /start
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "سلام! ربات روی Render اجرا شد 🚀")

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
    port = int(os.environ.get("PORT", 5000))  # Render به صورت اتوماتیک PORT رو میده
    # ست کردن وبهوک
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL + WEBHOOK_PATH)
    app.run(host="0.0.0.0", port=port)
