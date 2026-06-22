import os
import json
import random
import datetime
import jdatetime
from hijri_converter import convert
import requests
from flask import Flask, request
import telebot
from telebot import types
import pytz

# ===== توکن و پورت =====
TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
PORT = int(os.environ.get("PORT", 5000))

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# ===== مسیر فایل‌های ذخیره‌سازی =====
DATA_FILE = "bot_data.json"
PICTURE_FOLDER = os.path.join(os.path.dirname(__file__), "pictures")

# ===== تصاویر ماه‌های شمسی =====
MONTH_IMAGES = {
    1: "farvardin.png", 2: "ordibehesht.png", 3: "khordad.png",
    4: "tir.png", 5: "mordad.png", 6: "shahrivar.png",
    7: "mehr.png", 8: "aban.png", 9: "azar.png",
    10: "dey.png", 11: "bahman.png", 12: "esfand.png"
}

# ===== داده‌های جرعت و حقیقت =====
DARE_LIST = [
    "یه جوک بگو که همه بخندن 😂",
    "برای ۳۰ ثانیه صدای حیوانات دربیار 🐸",
    "یه سلفی با قیافه عجیب بفرست 🤳",
    "یه آهنگ بخون (حتی اگه بلد نباشی) 🎵",
    "یه کامنت محبت‌آمیز زیر پست آخر یه غریبه بذار 💬",
    "بدون دستت ده تا پوش‌آپ بزن 💪",
    "یه دقیقه مثل ربات حرف بزن 🤖",
    "یه شعر مسخره از خودت بگو 📝",
    "صدای اذان بده! 📢",
    "اسم ۵ نفر از گروه رو با چشم بسته بگو 🙈",
    "برقص! (ویدیو بفرست) 💃",
    "یه جمله انگیزشی به سبک استاد خودساخته بگو 🧠",
    "ادای معلم مدرسه‌ات رو دربیار 👨‍🏫",
    "یه مزیت عجیب درباره خودت بگو 🌟",
    "برای ۱ دقیقه هر کی پیام داد با «قربانت» جواب بده 🙏",
]

TRUTH_LIST = [
    "آخرین باری که گریه کردی کِی بود؟ 😢",
    "به کدوم عضو گروه بیشتر اعتماد داری؟ 🤝",
    "اگه الان ۱ میلیون داشتی چیکار می‌کردی؟ 💰",
    "بدترین دروغی که تو عمرت گفتی چیه؟ 🤥",
    "از چی بیشتر می‌ترسی؟ 😨",
    "اگه می‌تونستی یه روز باهاش عوض بشی کی رو انتخاب می‌کردی؟ 🔄",
    "آخرین باری که کسی رو دوست داشتی کِی بود؟ ❤️",
    "اگه یه آرزو داشتی چی می‌خواستی؟ 🌠",
    "بزرگ‌ترین رازی که داری چیه؟ 🤫",
    "اگه می‌تونستی یه چیزی رو تو زندگیت عوض کنی چی بود؟ 🔁",
    "بیشترین پول رو تا حالا یه جا چقدر خرج کردی؟ 💸",
    "اولین عشقت کی بود (اسم نبر)؟ 💕",
    "از کدوم کار خودت شرم داری؟ 😳",
    "بدترین خاطره‌ات چیه؟ 😬",
    "اگه بدونی فردا دنیا تموم میشه، امشب چیکار می‌کنی؟ 🌍",
]

# ===== لود و ذخیره داده =====
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "mute_users": {},
        "repeat_mode": {},
        "warns": {},
        "notes": {},
        "banned_words": {},
        "welcome_msg": {},
        "goodbye_msg": {},
        "pins": {},
        "poll_data": {},
        "dare_truth_active": {},
        "whisper_pending": {},
        "group_members": {},
        "scores": {},
        "custom_commands": {},
        "flood_count": {},
        "antiflood": {},
    }

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)

data = load_data()

# ===== کمک‌کننده‌ها =====
def is_muted(user_id):
    uid = str(user_id)
    if uid in data["mute_users"]:
        mute_until = data["mute_users"][uid]
        if datetime.datetime.fromisoformat(mute_until) > datetime.datetime.now():
            return True
        else:
            del data["mute_users"][uid]
            save_data(data)
    return False

def get_chat_id(message):
    return str(message.chat.id)

def get_user_mention(user):
    name = user.first_name or "کاربر"
    if user.last_name:
        name += " " + user.last_name
    return types.InlineKeyboardMarkup(), f'<a href="tg://user?id={user.id}">{name}</a>'

# ===== تقویم =====
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
    return info, persian_date_obj.month

def handle_calendar(message):
    cal_info, month = get_calendar_info()
    image_file = MONTH_IMAGES.get(month)
    photo_path = os.path.join(PICTURE_FOLDER, image_file)
    if os.path.exists(photo_path):
        with open(photo_path, "rb") as photo:
            bot.send_photo(message.chat.id, photo, caption=cal_info)
    else:
        bot.send_message(message.chat.id, cal_info + f"\n⚠️ عکس ماه پیدا نشد: {image_file}")

# ===== تگ همه اعضا (inline mention) =====
def tag_all_members(message):
    chat_id = message.chat.id
    cid = str(chat_id)
    members = data["group_members"].get(cid, {})
    if not members:
        bot.reply_to(message, "⚠️ هنوز اطلاعات اعضا ذخیره نشده. کمی صبر کن تا بقیه پیام بدن.")
        return
    msg_text = "📢 توجه همه:\n\n"
    entities = []
    offset = len(msg_text.encode("utf-16-le")) // 2
    mentions = []
    for uid, uname in members.items():
        mention = uname
        mentions.append((int(uid), mention))
    for uid, name in mentions:
        part = f"@{name} " if name else f"{name} "
        # برای inline mention
        display = name if name else "کاربر"
        mention_text = f"[{display}](tg://user?id={uid}) "
        msg_text_chunk = f"[{display}]"
        mentions_text_list = []
    # ساخت متن با inline mention برای همه
    full_text = "📢 توجه همه:\n"
    for uid, name in mentions:
        display = name if name else "کاربر"
        full_text += f'<a href="tg://user?id={uid}">{display}</a> '
    bot.send_message(chat_id, full_text, parse_mode="HTML")

# ===== ذخیره اعضا =====
def save_member(message):
    cid = str(message.chat.id)
    uid = str(message.from_user.id)
    name = message.from_user.first_name or ""
    if message.from_user.last_name:
        name += " " + message.from_user.last_name
    if cid not in data["group_members"]:
        data["group_members"][cid] = {}
    data["group_members"][cid][uid] = name
    save_data(data)

# ===== نجوا (whisper) =====
def handle_whisper(message):
    """
    دستور: نجوا @username پیام
    ربات میاد پی‌وی فرستنده رو می‌زنه و ازش می‌خواد متن بفرسته، بعد به طرف مقابل پی‌وی می‌زنه
    """
    parts = message.text.strip().split(maxsplit=2)
    if len(parts) < 3:
        bot.reply_to(message, "❗ فرمت: نجوا @یوزرنیم پیام")
        return
    target_username = parts[1].replace("@", "")
    whisper_text = parts[2]
    sender_id = message.from_user.id
    sender_name = message.from_user.first_name or "کسی"
    cid = str(message.chat.id)

    # ذخیره اطلاعات نجوا
    data["whisper_pending"][str(sender_id)] = {
        "target_username": target_username,
        "text": whisper_text,
        "chat_id": cid,
        "sender_name": sender_name
    }
    save_data(data)

    # پیدا کردن آیدی هدف از اعضای ذخیره‌شده
    target_id = None
    members = data["group_members"].get(cid, {})
    for uid, uname in members.items():
        if uname and target_username.lower() in uname.lower():
            target_id = int(uid)
            break

    if target_id:
        try:
            bot.send_message(
                target_id,
                f"🤫 یه نجوا برات داری از طرف <b>{sender_name}</b> در گروه:\n\n<i>{whisper_text}</i>",
                parse_mode="HTML"
            )
            bot.reply_to(message, f"✅ نجوا به {target_username} فرستاده شد 🤫")
        except Exception:
            bot.reply_to(message, f"⚠️ نمی‌تونم به {target_username} پیام بدم. باید اول ربات رو استارت کرده باشه.")
    else:
        bot.reply_to(message, f"⚠️ کاربر {target_username} پیدا نشد. اگه اخیراً تو گروه پیام داده باشه پیدا می‌شه.")

# ===== اخطار =====
def warn_user(message):
    if not message.reply_to_message:
        bot.reply_to(message, "❗ روی پیام کسی ریپلای کن")
        return
    target = message.reply_to_message.from_user
    uid = str(target.id)
    cid = get_chat_id(message)
    if cid not in data["warns"]:
        data["warns"][cid] = {}
    data["warns"][cid][uid] = data["warns"][cid].get(uid, 0) + 1
    count = data["warns"][cid][uid]
    save_data(data)
    name = target.first_name or "کاربر"
    bot.reply_to(message, f"⚠️ {name} اخطار گرفت! ({count}/3)")
    if count >= 3:
        try:
            bot.ban_chat_member(message.chat.id, target.id)
            bot.send_message(message.chat.id, f"🚫 {name} بعد از ۳ اخطار بن شد!")
            data["warns"][cid][uid] = 0
            save_data(data)
        except Exception as e:
            bot.reply_to(message, f"❌ نمی‌تونم بن کنم: {e}")

def reset_warn(message):
    if not message.reply_to_message:
        bot.reply_to(message, "❗ روی پیام کسی ریپلای کن")
        return
    uid = str(message.reply_to_message.from_user.id)
    cid = get_chat_id(message)
    if cid in data["warns"] and uid in data["warns"][cid]:
        data["warns"][cid][uid] = 0
        save_data(data)
    bot.reply_to(message, "✅ اخطارهای کاربر ریست شد")

# ===== کیک و بن =====
def kick_user(message):
    if not message.reply_to_message:
        bot.reply_to(message, "❗ روی پیام کسی ریپلای کن")
        return
    target = message.reply_to_message.from_user
    try:
        bot.ban_chat_member(message.chat.id, target.id)
        bot.unban_chat_member(message.chat.id, target.id)
        bot.reply_to(message, f"👢 {target.first_name} کیک شد!")
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {e}")

def ban_user(message):
    if not message.reply_to_message:
        bot.reply_to(message, "❗ روی پیام کسی ریپلای کن")
        return
    target = message.reply_to_message.from_user
    try:
        bot.ban_chat_member(message.chat.id, target.id)
        bot.reply_to(message, f"🚫 {target.first_name} بن شد!")
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {e}")

def unban_user(message):
    if not message.reply_to_message:
        bot.reply_to(message, "❗ روی پیام کسی ریپلای کن")
        return
    target = message.reply_to_message.from_user
    try:
        bot.unban_chat_member(message.chat.id, target.id)
        bot.reply_to(message, f"✅ {target.first_name} آنبن شد!")
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {e}")

# ===== پین =====
def pin_message(message):
    if not message.reply_to_message:
        bot.reply_to(message, "❗ روی پیامی ریپلای کن تا پین بشه")
        return
    try:
        bot.pin_chat_message(message.chat.id, message.reply_to_message.message_id)
        bot.reply_to(message, "📌 پیام پین شد!")
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {e}")

def unpin_message(message):
    try:
        bot.unpin_chat_message(message.chat.id)
        bot.reply_to(message, "✅ پین برداشته شد!")
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {e}")

# ===== یادداشت گروه =====
def save_note(message):
    parts = message.text.strip().split(maxsplit=2)
    if len(parts) < 3:
        bot.reply_to(message, "❗ فرمت: یادداشت نام متن")
        return
    cid = get_chat_id(message)
    note_name = parts[1]
    note_text = parts[2]
    if cid not in data["notes"]:
        data["notes"][cid] = {}
    data["notes"][cid][note_name] = note_text
    save_data(data)
    bot.reply_to(message, f"✅ یادداشت «{note_name}» ذخیره شد!")

def get_note(message):
    parts = message.text.strip().split()
    if len(parts) < 2:
        bot.reply_to(message, "❗ فرمت: بیار نام_یادداشت")
        return
    cid = get_chat_id(message)
    note_name = parts[1]
    note = data["notes"].get(cid, {}).get(note_name)
    if note:
        bot.reply_to(message, f"📝 {note_name}:\n{note}")
    else:
        bot.reply_to(message, f"❌ یادداشتی با نام «{note_name}» پیدا نشد")

def list_notes(message):
    cid = get_chat_id(message)
    notes = data["notes"].get(cid, {})
    if not notes:
        bot.reply_to(message, "📭 هیچ یادداشتی ثبت نشده")
        return
    text = "📋 یادداشت‌های گروه:\n\n"
    for name in notes:
        text += f"• {name}\n"
    bot.reply_to(message, text)

# ===== کلمات ممنوع =====
def add_banned_word(message):
    parts = message.text.strip().split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "❗ فرمت: فیلتر کلمه")
        return
    cid = get_chat_id(message)
    word = parts[1].lower()
    if cid not in data["banned_words"]:
        data["banned_words"][cid] = []
    if word not in data["banned_words"][cid]:
        data["banned_words"][cid].append(word)
        save_data(data)
    bot.reply_to(message, f"✅ کلمه «{word}» فیلتر شد!")

def remove_banned_word(message):
    parts = message.text.strip().split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "❗ فرمت: آنفیلتر کلمه")
        return
    cid = get_chat_id(message)
    word = parts[1].lower()
    if cid in data["banned_words"] and word in data["banned_words"][cid]:
        data["banned_words"][cid].remove(word)
        save_data(data)
    bot.reply_to(message, f"✅ فیلتر «{word}» برداشته شد!")

def check_banned_words(message):
    cid = get_chat_id(message)
    banned = data["banned_words"].get(cid, [])
    text = message.text.lower() if message.text else ""
    for word in banned:
        if word in text:
            try:
                bot.delete_message(message.chat.id, message.message_id)
                bot.send_message(message.chat.id,
                    f"⛔ پیام {message.from_user.first_name} به دلیل کلمه ممنوع حذف شد.")
            except:
                pass
            return True
    return False

# ===== خوش‌آمد و خداحافظ =====
def set_welcome(message):
    parts = message.text.strip().split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "❗ فرمت: خوشامد متن_پیام")
        return
    cid = get_chat_id(message)
    data["welcome_msg"][cid] = parts[1]
    save_data(data)
    bot.reply_to(message, "✅ پیام خوش‌آمدگویی تنظیم شد!")

def set_goodbye(message):
    parts = message.text.strip().split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "❗ فرمت: خداحافظ متن_پیام")
        return
    cid = get_chat_id(message)
    data["goodbye_msg"][cid] = parts[1]
    save_data(data)
    bot.reply_to(message, "✅ پیام خداحافظی تنظیم شد!")

@bot.message_handler(content_types=["new_chat_members"])
def welcome_new_member(message):
    cid = get_chat_id(message)
    welcome = data["welcome_msg"].get(cid)
    for member in message.new_chat_members:
        name = member.first_name or "کاربر"
        uid = str(member.id)
        uname = member.first_name or ""
        if member.last_name:
            uname += " " + member.last_name
        if cid not in data["group_members"]:
            data["group_members"][cid] = {}
        data["group_members"][cid][uid] = uname
        save_data(data)
        if welcome:
            bot.send_message(message.chat.id,
                welcome.replace("{name}", f'<a href="tg://user?id={member.id}">{name}</a>'),
                parse_mode="HTML")
        else:
            bot.send_message(message.chat.id,
                f'👋 خوش اومدی <a href="tg://user?id={member.id}">{name}</a>!',
                parse_mode="HTML")

@bot.message_handler(content_types=["left_chat_member"])
def goodbye_member(message):
    cid = get_chat_id(message)
    member = message.left_chat_member
    name = member.first_name or "کاربر"
    uid = str(member.id)
    if cid in data["group_members"] and uid in data["group_members"][cid]:
        del data["group_members"][cid][uid]
        save_data(data)
    goodbye = data["goodbye_msg"].get(cid)
    if goodbye:
        bot.send_message(message.chat.id,
            goodbye.replace("{name}", name))
    else:
        bot.send_message(message.chat.id, f"👋 {name} گروه رو ترک کرد.")

# ===== سکوت =====
def mute_user_func(message, minutes):
    if not message.reply_to_message:
        bot.reply_to(message, "❗ روی پیام کسی ریپلای کن")
        return
    user_id = str(message.reply_to_message.from_user.id)
    until = datetime.datetime.now() + datetime.timedelta(minutes=minutes)
    data["mute_users"][user_id] = until.isoformat()
    save_data(data)
    bot.reply_to(message, f"🔇 کاربر {message.reply_to_message.from_user.first_name} سکوت شد برای {minutes} دقیقه")

def unmute_user_func(message):
    if not message.reply_to_message:
        bot.reply_to(message, "❗ روی پیام کسی ریپلای کن")
        return
    user_id = str(message.reply_to_message.from_user.id)
    if user_id in data["mute_users"]:
        del data["mute_users"][user_id]
        save_data(data)
    bot.reply_to(message, f"🔊 سکوت {message.reply_to_message.from_user.first_name} برداشته شد")

# ===== جرعت یا حقیقت =====
def dare_truth_start(message):
    cid = get_chat_id(message)
    data["dare_truth_active"][cid] = True
    save_data(data)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🎲 جرعت"), types.KeyboardButton("💬 حقیقت"))
    markup.add(types.KeyboardButton("🛑 پایان بازی"))
    bot.reply_to(message, "🎮 بازی جرعت یا حقیقت شروع شد!\nانتخاب کن:", reply_markup=markup)

def dare_truth_end(message):
    cid = get_chat_id(message)
    data["dare_truth_active"][cid] = False
    save_data(data)
    markup = types.ReplyKeyboardRemove()
    bot.reply_to(message, "🛑 بازی تموم شد!", reply_markup=markup)

# ===== امتیاز =====
def add_score(message):
    if not message.reply_to_message:
        bot.reply_to(message, "❗ روی پیام کسی ریپلای کن")
        return
    parts = message.text.strip().split()
    amount = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1
    uid = str(message.reply_to_message.from_user.id)
    cid = get_chat_id(message)
    name = message.reply_to_message.from_user.first_name or "کاربر"
    if cid not in data["scores"]:
        data["scores"][cid] = {}
    data["scores"][cid][uid] = data["scores"][cid].get(uid, 0) + amount
    save_data(data)
    bot.reply_to(message, f"⭐ {amount} امتیاز به {name} اضافه شد! (جمع: {data['scores'][cid][uid]})")

def show_scores(message):
    cid = get_chat_id(message)
    scores = data["scores"].get(cid, {})
    members = data["group_members"].get(cid, {})
    if not scores:
        bot.reply_to(message, "📊 هنوز امتیازی ثبت نشده")
        return
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    text = "🏆 جدول امتیازات:\n\n"
    medals = ["🥇", "🥈", "🥉"]
    for i, (uid, score) in enumerate(sorted_scores[:10]):
        name = members.get(uid, "کاربر")
        medal = medals[i] if i < 3 else f"{i+1}."
        text += f"{medal} {name}: {score} امتیاز\n"
    bot.reply_to(message, text)

# ===== دستور سفارشی =====
def add_custom_command(message):
    parts = message.text.strip().split(maxsplit=2)
    if len(parts) < 3:
        bot.reply_to(message, "❗ فرمت: دستور نام_دستور پاسخ")
        return
    cid = get_chat_id(message)
    cmd = parts[1].lower()
    response = parts[2]
    if cid not in data["custom_commands"]:
        data["custom_commands"][cid] = {}
    data["custom_commands"][cid][cmd] = response
    save_data(data)
    bot.reply_to(message, f"✅ دستور «{cmd}» ثبت شد!")

# ===== انتخاب تصادفی =====
def random_pick(message):
    parts = message.text.strip().split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "❗ فرمت: انتخاب گزینه۱ / گزینه۲ / ...")
        return
    choices = [c.strip() for c in parts[1].split("/")]
    if len(choices) < 2:
        bot.reply_to(message, "❗ حداقل ۲ گزینه با / جدا کن")
        return
    picked = random.choice(choices)
    bot.reply_to(message, f"🎯 انتخاب تصادفی: **{picked}**", parse_mode="Markdown")

# ===== رول دایس =====
def roll_dice(message):
    result = random.randint(1, 6)
    bot.reply_to(message, f"🎲 تاس انداختی: {result}")

# ===== پرتاب سکه =====
def flip_coin(message):
    result = random.choice(["شیر 🦁", "خط ✏️"])
    bot.reply_to(message, f"🪙 سکه: {result}")

# ===== فال =====
FAAL_LIST = [
    "🌟 روزت پر از موفقیته! یه فرصت بزرگ در راهه.",
    "⚠️ امروز مراقب باش، شاید یه چالش پیش بیاد.",
    "💰 یه خبر مالی خوب در راهه!",
    "❤️ عشق در راهه... یا شاید هم فقط یه پیام از دوست قدیمی!",
    "🌈 بعد از سختی‌ها، روزهای بهتری می‌رسه.",
    "🍀 شانست امروز خوبه، ریسک کن!",
    "😴 بدنت به استراحت نیاز داره. امروز آروم باش.",
    "📚 یه چیز جدید یاد بگیر، برات مفیده.",
    "🎉 یه اتفاق خوش‌حال‌کننده امروز منتظرته!",
    "🤝 یه ارتباط جدید و مهم می‌سازی.",
]

def get_faal(message):
    faal = random.choice(FAAL_LIST)
    name = message.from_user.first_name or "دوست"
    bot.reply_to(message, f"🔮 فال {name}:\n\n{faal}")

# ===== اطلاعات کاربر =====
def get_user_info(message):
    target = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    name = f"{target.first_name or ''} {target.last_name or ''}".strip()
    username = f"@{target.username}" if target.username else "ندارد"
    lang = target.language_code or "نامشخص"
    text = f"👤 اطلاعات کاربر:\n\n"
    text += f"🆔 آیدی: <code>{target.id}</code>\n"
    text += f"📛 نام: {name}\n"
    text += f"👤 یوزرنیم: {username}\n"
    text += f"🌐 زبان: {lang}\n"
    bot.reply_to(message, text, parse_mode="HTML")

# ===== اطلاعات گروه =====
def get_group_info(message):
    chat = message.chat
    member_count = bot.get_chat_member_count(chat.id)
    text = f"📊 اطلاعات گروه:\n\n"
    text += f"📛 نام: {chat.title}\n"
    text += f"🆔 آیدی: <code>{chat.id}</code>\n"
    text += f"👥 تعداد اعضا: {member_count}\n"
    if chat.username:
        text += f"🔗 لینک: @{chat.username}\n"
    if chat.description:
        text += f"📝 توضیحات: {chat.description}\n"
    bot.reply_to(message, text, parse_mode="HTML")

# ===== شمارش معکوس =====
def countdown(message):
    parts = message.text.strip().split()
    if len(parts) < 2 or not parts[1].isdigit():
        bot.reply_to(message, "❗ فرمت: شمارش عدد (مثلاً: شمارش 5)")
        return
    n = min(int(parts[1]), 20)
    text = "⏳ شمارش معکوس:\n"
    text += " ".join([str(i) for i in range(n, 0, -1)]) + " 🚀"
    bot.reply_to(message, text)

# ===== ماشین حساب =====
def calculator(message):
    parts = message.text.strip().split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "❗ فرمت: حساب عبارت (مثلاً: حساب 2+2)")
        return
    try:
        expr = parts[1]
        allowed = set("0123456789+-*/(). ")
        if not all(c in allowed for c in expr):
            raise ValueError("عبارت مجاز نیست")
        result = eval(expr)
        bot.reply_to(message, f"🧮 {expr} = {result}")
    except Exception:
        bot.reply_to(message, "❌ عبارت ریاضی معتبر نیست")

# ===== تبدیل ارز ساده =====
def convert_currency(message):
    parts = message.text.strip().split()
    if len(parts) < 2 or not parts[1].isdigit():
        bot.reply_to(message, "❗ فرمت: تومان عدد_دلار (مثلاً: تومان 100)")
        return
    try:
        resp = requests.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=5)
        rate_usd_to_irr = resp.json().get("rates", {}).get("IRR", 500000)
        amount = int(parts[1])
        toman = int(amount * rate_usd_to_irr / 10)
        bot.reply_to(message, f"💱 {amount} دلار ≈ {toman:,} تومان")
    except Exception:
        bot.reply_to(message, "❌ خطا در دریافت نرخ ارز")

# ===== آب و هوا =====
def get_weather(message):
    parts = message.text.strip().split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "❗ فرمت: هوا شهر (مثلاً: هوا تهران)")
        return
    city = parts[1]
    try:
        url = f"https://wttr.in/{city}?format=3&lang=fa"
        resp = requests.get(url, timeout=5)
        bot.reply_to(message, f"🌤️ آب و هوای {city}:\n{resp.text}")
    except Exception:
        bot.reply_to(message, "❌ خطا در دریافت آب و هوا")

# ===== راهنما =====
def show_help(message):
    is_group = message.chat.type in ["group", "supergroup"]
    if is_group:
        text = """📖 راهنمای ربات (گروه):

🗂 مدیریت:
• سکو [دقیقه] ← سکوت کاربر (ریپلای)
• رفع ← رفع سکوت (ریپلای)
• اخطار ← اخطار به کاربر (ریپلای)
• ریست اخطار ← ریست اخطارها (ریپلای)
• کیک ← اخراج موقت (ریپلای)
• بن ← بن دائم (ریپلای)
• آنبن ← رفع بن (ریپلای)
• حذف ← حذف پیام (ریپلای)
• پین ← پین پیام (ریپلای)
• آنپین ← برداشتن پین

👥 اعضا:
• تگ همه ← منشن همه اعضا
• نجوا @یوزر پیام ← نجوا به کاربر

📝 یادداشت:
• یادداشت نام متن ← ذخیره یادداشت
• بیار نام ← نمایش یادداشت
• یادداشت‌ها ← لیست یادداشت‌ها

⚙️ تنظیمات:
• خوشامد متن ← پیام خوش‌آمد
• خداحافظ متن ← پیام خداحافظی
• فیلتر کلمه ← فیلتر کلمه
• آنفیلتر کلمه ← رفع فیلتر
• تکرار روشن/خاموش

🎮 سرگرمی:
• جرعت حقیقت ← شروع بازی
• امتیاز [عدد] ← امتیاز به کاربر (ریپلای)
• امتیازها ← جدول امتیاز
• انتخاب گزینه۱/گزینه۲ ← تصادفی
• تاس ← رول دایس
• سکه ← پرتاب سکه
• فال ← فال امروز
• شمارش عدد ← شمارش معکوس

📊 اطلاعات:
• تقویم ← تقویم امروز
• کاربر ← اطلاعات کاربر
• گروه ← اطلاعات گروه
• هوا شهر ← آب و هوا
• حساب عبارت ← ماشین حساب
• تومان عدد ← تبدیل دلار به تومان

⚡ دستور سفارشی:
• دستور نام پاسخ ← ساخت دستور"""
    else:
        text = """📖 راهنمای ربات (پی‌وی):

• تقویم ← تقویم امروز
• فال ← فال امروز
• تاس ← رول دایس
• سکه ← پرتاب سکه
• انتخاب گزینه۱/گزینه۲ ← انتخاب تصادفی
• حساب عبارت ← ماشین حساب
• تومان عدد ← تبدیل ارز
• هوا شهر ← آب و هوا
• کاربر ← اطلاعات من
• شمارش عدد ← شمارش معکوس"""
    bot.reply_to(message, text)

# ===== تابع عکس گروه =====
def set_group_photo(message):
    try:
        if message.reply_to_message and message.reply_to_message.content_type == "photo":
            file_id = message.reply_to_message.photo[-1].file_id
            file_info = bot.get_file(file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            with open("group_photo.jpg", "wb") as new_file:
                new_file.write(downloaded_file)
            with open("group_photo.jpg", "rb") as photo:
                bot.set_chat_photo(chat_id=message.chat.id, photo=photo)
            bot.reply_to(message, "📸 عکس گروه با موفقیت تغییر کرد ✅")
    except Exception as e:
        bot.reply_to(message, f"❌ خطا در تغییر عکس گروه: {e}")

# ===== هندل اصلی پیام‌ها =====
@bot.message_handler(func=lambda m: True, content_types=["text"])
def handle_text(message):
    global data

    user_id = message.from_user.id
    cid = get_chat_id(message)
    is_group = message.chat.type in ["group", "supergroup"]

    # ذخیره عضو
    if is_group:
        save_member(message)

    # بررسی سکوت
    if is_muted(user_id):
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except:
            pass
        return

    # بررسی کلمات ممنوع
    if is_group and check_banned_words(message):
        return

    text = message.text.strip() if message.text else ""

    # ===== دستورات گروه و پی‌وی =====

    # راهنما
    if text in ["راهنما", "help", "/help", "/start"]:
        show_help(message)
        return

    # تقویم
    if text == "تقویم":
        handle_calendar(message)
        return

    # تکرار
    if "تکرار روشن" in text:
        data["repeat_mode"][cid] = True
        save_data(data)
        bot.reply_to(message, "حالت تکرار روشن شد ✅")
        return
    if "تکرار خاموش" in text:
        data["repeat_mode"][cid] = False
        save_data(data)
        bot.reply_to(message, "حالت تکرار خاموش شد ❌")
        return

    # فال
    if text == "فال":
        get_faal(message)
        return

    # تاس
    if text == "تاس":
        roll_dice(message)
        return

    # سکه
    if text == "سکه":
        flip_coin(message)
        return

    # شمارش
    if text.startswith("شمارش"):
        countdown(message)
        return

    # حساب
    if text.startswith("حساب"):
        calculator(message)
        return

    # تبدیل ارز
    if text.startswith("تومان"):
        convert_currency(message)
        return

    # آب و هوا
    if text.startswith("هوا"):
        get_weather(message)
        return

    # انتخاب تصادفی
    if text.startswith("انتخاب"):
        random_pick(message)
        return

    # اطلاعات کاربر
    if text == "کاربر":
        get_user_info(message)
        return

    # ===== دستورات گروه =====
    if is_group:

        # اطلاعات گروه
        if text == "گروه":
            get_group_info(message)
            return

        # تگ همه
        if text == "تگ همه":
            tag_all_members(message)
            return

        # نجوا
        if text.startswith("نجوا"):
            handle_whisper(message)
            return

        # سکوت
        if text.startswith("سکو"):
            parts = text.split()
            minutes = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 60
            mute_user_func(message, minutes)
            return

        # رفع سکوت
        if text.startswith("رفع"):
            unmute_user_func(message)
            return

        # اخطار
        if text == "اخطار":
            warn_user(message)
            return

        # ریست اخطار
        if text == "ریست اخطار":
            reset_warn(message)
            return

        # کیک
        if text == "کیک":
            kick_user(message)
            return

        # بن
        if text == "بن":
            ban_user(message)
            return

        # آنبن
        if text == "آنبن":
            unban_user(message)
            return

        # حذف پیام
        if text == "حذف":
            if message.reply_to_message:
                try:
                    bot.delete_message(message.chat.id, message.reply_to_message.message_id)
                    bot.delete_message(message.chat.id, message.message_id)
                except Exception as e:
                    bot.reply_to(message, f"❌ {e}")
            return

        # پین
        if text == "پین":
            pin_message(message)
            return

        # آنپین
        if text == "آنپین":
            unpin_message(message)
            return

        # یادداشت
        if text.startswith("یادداشت "):
            save_note(message)
            return

        # نمایش یادداشت
        if text.startswith("بیار "):
            get_note(message)
            return

        # لیست یادداشت
        if text == "یادداشت‌ها" or text == "یادداشتها":
            list_notes(message)
            return

        # فیلتر کلمه
        if text.startswith("فیلتر "):
            add_banned_word(message)
            return

        # رفع فیلتر
        if text.startswith("آنفیلتر "):
            remove_banned_word(message)
            return

        # خوش‌آمد
        if text.startswith("خوشامد "):
            set_welcome(message)
            return

        # خداحافظی
        if text.startswith("خداحافظ "):
            set_goodbye(message)
            return

        # امتیاز
        if text.startswith("امتیاز"):
            add_score(message)
            return

        # جدول امتیاز
        if text == "امتیازها":
            show_scores(message)
            return

        # جرعت حقیقت - شروع
        if text == "جرعت حقیقت":
            dare_truth_start(message)
            return

        # جرعت حقیقت - بازی
        if data["dare_truth_active"].get(cid):
            if text == "🎲 جرعت":
                bot.reply_to(message, f"🎲 جرعت:\n\n{random.choice(DARE_LIST)}")
                return
            if text == "💬 حقیقت":
                bot.reply_to(message, f"💬 حقیقت:\n\n{random.choice(TRUTH_LIST)}")
                return
            if text == "🛑 پایان بازی":
                dare_truth_end(message)
                return

        # عکس گروه
        if message.reply_to_message and message.reply_to_message.content_type == "photo" and text == "قرار بده":
            set_group_photo(message)
            return

        # دستور سفارشی
        if text.startswith("دستور "):
            add_custom_command(message)
            return

        # اجرای دستور سفارشی
        custom_cmds = data["custom_commands"].get(cid, {})
        if text.lower() in custom_cmds:
            bot.reply_to(message, custom_cmds[text.lower()])
            return

    # حالت تکرار
    if data["repeat_mode"].get(cid):
        bot.reply_to(message, text)

# ===== وب‌هوک =====
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    json_str = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "!", 200

@app.route("/")
def index():
    return "Bot is running!", 200

# ===== ست وب‌هوک =====
bot.remove_webhook()
bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
