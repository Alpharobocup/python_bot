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

# اطلاعات خود ربات (برای تشخیص منشن/آیدی ربات در پیام‌ها)
try:
    BOT_ME = bot.get_me()
except Exception:
    BOT_ME = None

# ===== مسیر فایل‌های ذخیره‌سازی =====
DATA_FILE = "bot_data.json"
PICTURE_FOLDER = os.path.join(os.path.dirname(__file__), "pictures")
ADMIN_IDS = [1656900957, 7388352162]

def is_admin(message):
    return message.from_user.id in ADMIN_IDS
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

# ===== تنظیمات ماژول یادگیری و حافظه گروه =====
BOT_TRIGGER_WORDS = ["ربات", "بات"]      # کلماتی که با گفتنشون ربات وارد بحث میشه
MAX_STORED_MESSAGES = 3000                # حداکثر پیام ذخیره‌شده برای هر گروه (حافظه)
AUTO_REPLY_CHANCE = 0.04                  # احتمال شرکت خودجوش ربات در بحث (۴٪)
AUTO_REPLY_COOLDOWN = 90                  # حداقل فاصله زمانی (ثانیه) بین دو مشارکت خودجوش
MIN_MESSAGES_TO_LEARN = 30                # حداقل پیام لازم تا ربات شروع کنه به جمله‌سازی
MAX_CHAIN_KEYS = 4000                     # سقف اندازه مدل زبانی هر گروه (برای جلوگیری از رشد بی‌رویه)

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
        # ---- کلیدهای مربوط به یادگیری و حافظه گروهی ----
        "chat_messages": {},        # {cid: [ {user_id, name, username, text, date}, ... ]}
        "learning_enabled": {},     # {cid: True/False}
        "markov_chain": {},         # {cid: {word: [next_word, next_word, ...]}}
        "markov_starters": {},      # {cid: [word, word, ...]}
        "last_auto_reply": {},      # {cid: timestamp}
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

# ===== یادگیری و حافظه گروهی (Markov Chain) =====
# این بخش مسئول اینه که: هر پیام گروه رو ذخیره کنه، ازش یه مدل ساده زبانی
# (زنجیره مارکوف) به‌صورت مستقل برای هر گروه بسازه، و بعداً بتونه با همون
# سبک گروه جمله بسازه و در بحث‌ها شرکت کنه. همینطور امکان جستجو و یادآوری
# حرف‌های قبلی افراد رو فراهم می‌کنه.

def is_learning_enabled(cid):
    # پیش‌فرض یادگیری روشنه مگر اینکه ادمین خاموشش کرده باشه
    return data["learning_enabled"].get(cid, True)

def remember_message(message):
    """هر پیام متنی گروه رو در حافظه اون گروه ذخیره می‌کنه (برای یادآوری بعدی)."""
    if not message.text:
        return
    cid = get_chat_id(message)
    if cid not in data["chat_messages"]:
        data["chat_messages"][cid] = []

    entry = {
        "user_id": message.from_user.id,
        "name": message.from_user.first_name or "کاربر",
        "username": message.from_user.username or "",
        "text": message.text,
        "date": datetime.datetime.now().isoformat(),
    }
    data["chat_messages"][cid].append(entry)

    # جلوگیری از رشد بی‌نهایت حافظه هر گروه
    if len(data["chat_messages"][cid]) > MAX_STORED_MESSAGES:
        data["chat_messages"][cid] = data["chat_messages"][cid][-MAX_STORED_MESSAGES:]

    save_data(data)

def tokenize(text):
    """متن رو به کلمات تمیز تبدیل می‌کنه (بدون لینک/منشن/دستور)."""
    words = []
    for w in text.strip().split():
        if w.startswith("http") or w.startswith("@") or w.startswith("/"):
            continue
        words.append(w)
    return words

def train_markov(cid, text):
    """مدل زبانی گروه رو با یک پیام جدید آپدیت می‌کنه (یادگیری بدون نظارت)."""
    words = tokenize(text)
    if len(words) < 2:
        return

    if cid not in data["markov_chain"]:
        data["markov_chain"][cid] = {}
    if cid not in data["markov_starters"]:
        data["markov_starters"][cid] = []

    chain = data["markov_chain"][cid]
    starters = data["markov_starters"][cid]

    starters.append(words[0])
    if len(starters) > 500:
        data["markov_starters"][cid] = starters[-500:]

    for i in range(len(words) - 1):
        key = words[i]
        nxt = words[i + 1]
        if key not in chain:
            chain[key] = []
        chain[key].append(nxt)
        if len(chain[key]) > 50:
            chain[key] = chain[key][-50:]

    # سقف اندازه مدل تا حافظه سرور شلوغ نشه
    if len(chain) > MAX_CHAIN_KEYS:
        for k in list(chain.keys())[:500]:
            del chain[k]

    save_data(data)

def generate_sentence(cid, seed_word=None, max_words=20):
    """با استفاده از مدلی که از گفتگوهای همون گروه یاد گرفته، یک جمله می‌سازه."""
    chain = data["markov_chain"].get(cid, {})
    starters = data["markov_starters"].get(cid, [])
    if not chain or not starters:
        return None

    current = seed_word if (seed_word and seed_word in chain) else random.choice(starters)
    result = [current]

    for _ in range(max_words - 1):
        next_options = chain.get(current)
        if not next_options:
            break
        current = random.choice(next_options)
        result.append(current)

    return " ".join(result)

def is_bot_mentioned(message):
    """تشخیص میده که آیا پیام، ربات رو صدا زده (منشن/ریپلای/کلمه محرک)."""
    text = message.text or ""
    if BOT_ME and BOT_ME.username and f"@{BOT_ME.username}" in text:
        return True
    for w in BOT_TRIGGER_WORDS:
        if w in text:
            return True
    if (
        message.reply_to_message
        and message.reply_to_message.from_user
        and BOT_ME
        and message.reply_to_message.from_user.id == BOT_ME.id
    ):
        return True
    return False

def handle_bot_participation(message):
    """تصمیم می‌گیره ربات وارد بحث بشه یا نه، و در صورت لزوم جواب می‌سازه."""
    cid = get_chat_id(message)
    if not is_learning_enabled(cid):
        return

    mentioned = is_bot_mentioned(message)

    now_ts = datetime.datetime.now().timestamp()
    last_ts = data["last_auto_reply"].get(cid, 0)

    should_random_join = (
        not mentioned
        and (now_ts - last_ts) > AUTO_REPLY_COOLDOWN
        and random.random() < AUTO_REPLY_CHANCE
    )

    if not (mentioned or should_random_join):
        return

    total_learned = len(data["chat_messages"].get(cid, []))
    if total_learned < MIN_MESSAGES_TO_LEARN:
        if mentioned:
            bot.reply_to(message, "😅 هنوز دارم یاد می‌گیرم تو این گروه چطور حرف بزنم، یکم بیشتر باهم حرف بزنید تا دستم بیاد!")
        return

    # سعی می‌کنیم جمله رو با یکی از کلمات پیام فعلی شروع کنیم تا مرتبط‌تر باشه
    words = tokenize(message.text or "")
    seed = None
    chain = data["markov_chain"].get(cid, {})
    for w in reversed(words):
        if w in chain:
            seed = w
            break

    sentence = generate_sentence(cid, seed_word=seed)
    if not sentence:
        return

    data["last_auto_reply"][cid] = now_ts
    save_data(data)

    if mentioned:
        bot.reply_to(message, sentence)
    else:
        bot.send_message(message.chat.id, sentence)

def recall_user_messages(message):
    """دستور «چی گفت» → یادآوری حرف‌های قبلی یک کاربر خاص در همون گروه."""
    cid = get_chat_id(message)
    raw = message.text.strip()
    rest = raw[len("چی گفت"):].strip()
    rest_parts = rest.split(maxsplit=1) if rest else []

    target_name = None
    keyword = None

    if message.reply_to_message:
        target_name = message.reply_to_message.from_user.first_name or "کاربر"
        if rest:
            keyword = rest
    elif rest_parts:
        target_name = rest_parts[0].replace("@", "")
        if len(rest_parts) > 1:
            keyword = rest_parts[1]
    else:
        bot.reply_to(message, "❗ فرمت: چی گفت @یوزرنیم [کلمه] یا ریپلای رو پیام یه نفر بزن و بنویس «چی گفت»")
        return

    messages = data["chat_messages"].get(cid, [])
    matched = [
        m for m in messages
        if target_name.lower() in (m.get("name") or "").lower()
        or target_name.lower() == (m.get("username") or "").lower()
    ]
    if keyword:
        matched = [m for m in matched if keyword.lower() in m["text"].lower()]

    if not matched:
        bot.reply_to(message, f"❌ چیزی از «{target_name}» تو حافظه‌ام پیدا نکردم")
        return

    matched = matched[-5:]
    text_out = f"🗣️ چیزهایی که {target_name} گفته:\n\n"
    for m in matched:
        text_out += f"• {m['text']}\n"
    bot.reply_to(message, text_out)

def search_group_memory(message):
    """دستور «بگرد» → جستجوی یک کلمه در کل حافظه گفتگوهای گروه."""
    cid = get_chat_id(message)
    raw = message.text.strip()
    keyword = raw[len("بگرد"):].strip()
    if not keyword:
        bot.reply_to(message, "❗ فرمت: بگرد کلمه")
        return

    messages = data["chat_messages"].get(cid, [])
    matched = [m for m in messages if keyword.lower() in m["text"].lower()]
    if not matched:
        bot.reply_to(message, f"❌ چیزی درباره «{keyword}» تو حافظه‌ام پیدا نکردم")
        return

    matched = matched[-5:]
    text_out = f"🔎 نتایج جستجو برای «{keyword}»:\n\n"
    for m in matched:
        text_out += f"👤 {m['name']}: {m['text']}\n"
    bot.reply_to(message, text_out)

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
        bot.reply_to(message, "❗ فرمت: آن فیلتر کلمه")
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
    bot.reply_to(message, f"🔇 کاربر {message.reply_to_message.from_user.first_name} سکوت برای {minutes} دقیقه")

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
        bot.reply_to(message, " هنوز امتیازی ثبت نشده")
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
    n = min(int(parts[1]), 20000000000000000)
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
        resp = requests.get("https://Api.BrsApi.ir/Market/Gold_Currency.php?key=Market_CGCC", timeout=5)
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
        text = """راهنمای ربات :

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

🧠 یادگیری و حافظه گروه:
• یادگیری روشن/خاموش ← فعال یا غیرفعال کردن یادگیری خودکار (فقط ادمین)
• چی گفت @یوزر [کلمه] ← یادآوری حرف‌های یه نفر (یا ریپلای رو پیامش + «چی گفت»)
• بگرد کلمه ← جستجو تو کل حافظه گفتگوهای گروه
• صدا زدن ربات (منشن/ریپلای/گفتن «ربات») یا حتی خودجوش ← وارد بحث می‌شه

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
        text = """📖 راهنمای ربات :

• تقویم ← تقویم امروز
• فال ← فال امروز
• تاس ← رول دایس
• سکه ← پرتاب سکه
• انتخاب گزینه۱/گزینه۲ ← انتخاب تصادفی
• حساب عبارت ← ماشین حساب
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

    # ذخیره عضو + ذخیره پیام در حافظه گروه (برای یادآوری بعدی)
    if is_group:
        save_member(message)
        remember_message(message)

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
    """if text.startswith("تومان"):
        convert_currency(message)
        return
"""
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
            if not is_admin(message):
                bot.reply_to(message, "❌ دسترسی نداری")
                return
            parts = text.split()
            minutes = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 60
            mute_user_func(message, minutes)
            return

        # رفع سکوت
        if text.startswith("رفع"):
            if not is_admin(message):
                bot.reply_to(message, "❌ دسترسی نداری")
                return            
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
            if not is_admin(message):
                bot.reply_to(message, "❌ دسترسی نداری")
                return
            if message.reply_to_message:
                try:
                    bot.delete_message(message.chat.id, message.reply_to_message.message_id)
                    bot.delete_message(message.chat.id, message.message_id)
                except Exception as e:
                    bot.reply_to(message, f"❌ {e}")
            return

        # پین
        if text == "پین":
            if not is_admin(message):
                bot.reply_to(message, "❌ دسترسی نداری")
                return
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
        if text == "یادداشت‌ ها" or text == "یادداشتها":
            list_notes(message)
            return

        # فیلتر کلمه
        if text.startswith("فیلتر "):
            if not is_admin(message):
                bot.reply_to(message, "❌ دسترسی نداری")
                return
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
        if text == "امتیاز ها":
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
            if not is_admin(message):
                bot.reply_to(message, "❌ دسترسی نداری")
                return
            add_custom_command(message)
            return

        # اجرای دستور سفارشی
        custom_cmds = data["custom_commands"].get(cid, {})
        if text.lower() in custom_cmds:
            bot.reply_to(message, custom_cmds[text.lower()])
            return
        # حذف دستور سفارشی
        if text.startswith("حذف دستور "):
            parts = text.split(maxsplit=2)
            if len(parts) < 3:
                bot.reply_to(message, "❗ فرمت: حذف دستور نام_دستور")
            else:
                cmd = parts[2].lower()
                custom_cmds = data["custom_commands"].get(cid, {})
                if cmd in custom_cmds:
                    del data["custom_commands"][cid][cmd]
                    save_data(data)
                    bot.reply_to(message, f"✅ دستور «{cmd}» حذف شد!")
                else:
                    bot.reply_to(message, f"❌ دستوری با نام «{cmd}» پیدا نشد")
            return

        # ===== یادگیری روشن/خاموش (فقط ادمین) =====
        if text == "یادگیری روشن":
            if not is_admin(message):
                bot.reply_to(message, "❌ دسترسی نداری")
                return
            data["learning_enabled"][cid] = True
            save_data(data)
            bot.reply_to(message, "🧠 یادگیری روشن شد! از الان یاد می‌گیرم تو این گروه چطور حرف بزنم.")
            return

        if text == "یادگیری خاموش":
            if not is_admin(message):
                bot.reply_to(message, "❌ دسترسی نداری")
                return
            data["learning_enabled"][cid] = False
            save_data(data)
            bot.reply_to(message, "🧠 یادگیری خاموش شد.")
            return

        # ===== یادآوری حرف‌های یه کاربر =====
        if text.startswith("چی گفت"):
            recall_user_messages(message)
            return

        # ===== جستجو در حافظه گروه =====
        if text.startswith("بگرد"):
            search_group_memory(message)
            return

    # ===== یادگیری خودکار از پیام‌های عادی + مشارکت در بحث =====
    # فقط پیام‌هایی که به هیچ‌کدوم از دستورات بالا نخوردن به این‌جا می‌رسن،
    # پس مدل زبانی با متن دستورات آلوده نمیشه و فقط از حرف زدن طبیعی افراد یاد می‌گیره.
    if is_group:
        if is_learning_enabled(cid):
            train_markov(cid, text)
        handle_bot_participation(message)

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
