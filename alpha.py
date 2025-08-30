import os
import datetime
import jdatetime
from hijri_converter import convert
import requests
from flask import Flask, request
import telebot
import pytz
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import threading
import time
from datetime import datetime
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





# مسیر پوشه عکس‌ها (داخل فولدر پروژه)
PICTURE_FOLDER = os.path.join(os.path.dirname(__file__), "pictures")

# نام عکس‌های ماه‌ها (1 = فروردین, 2 = اردیبهشت, … 12 = اسفند)
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

# تابع گرفتن اطلاعات تقویم
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

    return info, persian_date_obj.month  # برمی‌گردونه ماه برای عکس

# هندلر تقویم با عکس
def handle_calendar(message):
    cal_info, month = get_calendar_info()
    image_file = MONTH_IMAGES.get(month)
    photo_path = os.path.join(PICTURE_FOLDER, image_file)

    # بررسی وجود عکس
    if os.path.exists(photo_path):
        with open(photo_path, "rb") as photo:
            bot.send_photo(message.chat.id, photo, caption=cal_info)
    else:
        bot.send_message(message.chat.id, cal_info + f"\n⚠️ عکس ماه پیدا نشد: {image_file}")


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






def build_time_panel(hour=6, minute=0):
    markup = InlineKeyboardMarkup(row_width=3)
    
    # ردیف ساعت
    markup.add(
        InlineKeyboardButton("▲ ساعت", callback_data="hour_up"),
        InlineKeyboardButton(f"{hour:02d}h", callback_data="noop"),
        InlineKeyboardButton("▼ ساعت", callback_data="hour_down"),
    )
    
    # ردیف دقیقه
    markup.add(
        InlineKeyboardButton("▲ دقیقه", callback_data="min_up"),
        InlineKeyboardButton(f"{minute:02d}m", callback_data="noop"),
        InlineKeyboardButton("▼ دقیقه", callback_data="min_down"),
    )
    
    # دکمه تایید
    markup.add(
        InlineKeyboardButton("✅ تایید", callback_data="confirm_time")
    )
    return markup


# برای هر گروه یک ساعت و دقیقه ذخیره می‌کنیم
group_times = {}  # {chat_id: {"hour": 6, "minute": 0}}


@bot.callback_query_handler(func=lambda call: True)
def handle_time_buttons(call):
    chat_id = call.message.chat.id
    if chat_id not in group_times:
        group_times[chat_id] = {"hour": 6, "minute": 0}
    
    hour = group_times[chat_id]["hour"]
    minute = group_times[chat_id]["minute"]
    
    if call.data == "hour_up":
        hour = (hour + 1) % 24
    elif call.data == "hour_down":
        hour = (hour - 1) % 24
    elif call.data == "min_up":
        minute = (minute + 1) % 60
    elif call.data == "min_down":
        minute = (minute - 1) % 60
    elif call.data == "confirm_time":
        bot.answer_callback_query(call.id, f"⏰ زمان ارسال پیام تنظیم شد: {hour:02d}:{minute:02d}")
        return
    
    # ذخیره تغییرات
    group_times[chat_id]["hour"] = hour
    group_times[chat_id]["minute"] = minute
    
    # آپدیت پیام با ساعت و دقیقه جدید
    bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=build_time_panel(hour, minute))




threading.Thread(target=schedule_calendar, daemon=True).start()



#@bot.message_handler(func=lambda m: m.text and m.text.strip() == "پنل تقویم")
def calendar_panel(message):
    chat_id = message.chat.id

    # اگر گروه هنوز در group_times نیست، مقدار پیش‌فرض بذار
    if chat_id not in group_times:
        group_times[chat_id] = {"hour": 6, "minute": 0}

    # ارسال پنل زمان با ساعت و دقیقه فعلی گروه
    bot.send_message(chat_id, "پنل تنظیم ساعت تقویم:", reply_markup=build_time_panel(
        hour=group_times[chat_id]["hour"], 
        minute=group_times[chat_id]["minute"]
    ))




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

    # روشن/خاموش کردن حالت تکرار
    if "تکرار روشن" in text:
        set_repeat_on(message)
    elif "تکرار خاموش" in text:
        set_repeat_off(message)

    # نمایش تقویم
    if "تقویم" in text:
        handle_calendar(message)
    
    # پنل تقویم (در صورت نیاز)
    # if "پنل تقویم" in text:
    #     calendar_panel(message)

    # سکوت کردن کاربران
    if text.startswith("سکو"):
        parts = text.split()
        if len(parts) > 1 and parts[1].isdigit():
            mute_user(message, int(parts[1]))
        else:
            mute_user(message, 1)

    # رفع سکوت
    if text.startswith("رف"):
        unmute_user(message)

    # حذف پیام
    if "دل" in text:
        delete_message(message)

    # ریپلای روی عکس → قرار دادن عکس در گروه
    if message.reply_to_message and message.reply_to_message.content_type == "photo" and text == "قرار بده":
        set_group_photo(message)

    # حالت تکرار
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
