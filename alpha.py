import os
import logging
import random
import asyncio
from datetime import datetime
from flask import Flask, request, jsonify
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

# تنظیم لاگ‌گیری
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# دریافت متغیرهای محیطی
TOKEN = os.environ.get('BOT_TOKEN')
WEBHOOK_URL = os.environ.get('WEBHOOK_URL')

if not TOKEN or not WEBHOOK_URL:
    raise ValueError("متغیرهای محیطی تنظیم نشده‌اند!")

# ایجاد اپلیکیشن Flask
app = Flask(__name__)
bot = Bot(token=TOKEN)
application = Application.builder().token(TOKEN).build()

# ============ دیتابیس موقت (در حافظه) ============
# برای ذخیره وضعیت بازی‌ها و تنظیمات کاربران
user_settings = {}
games = {}
whisper_history = {}

# ============ لیست سوالات و چالش‌ها ============

# لیست سوالات جرعت/حقیقت - حالت دوستانه
truth_questions_friendly = [
    "آخرین باری که گریه کردی کی بود و چرا؟",
    "بهترین خاطره‌ی دوران کودکیت چیه؟",
    "اگر می‌تونستی یک روز رو دوباره زندگی کنی، کدوم روز رو انتخاب می‌کردی؟",
    "بزرگترین ترس تو چیه؟",
    "بهترین تعریفی که تا حالا شنیدی چی بود؟",
    "آرزوی بزرگت در زندگی چیه؟",
    "اگر می‌تونستی با یه شخصیت تاریخی شام بخوری، کی رو انتخاب می‌کردی؟",
    "چیزی که همیشه می‌خواستی بگی ولی نتونستی رو به کسی بگو؟",
    "به نظرت مهم‌ترین ویژگی یه دوست خوب چیه؟",
    "اگر یه روز می‌تونستی نامرئی بشی، چیکار می‌کردی؟"
]

dare_questions_friendly = [
    "۱۰ ثانیه مثل یه قورباغه بپر!",
    "با صدای بلند یه آهنگ بخون (می‌تونی آهنگ خودت باشه)!",
    "به مدت ۳۰ ثانیه فقط با حرکات بدن حرف بزن!",
    "یه داستان خنده‌دار از زندگیت بگو!",
    "۵ حرکت ورزشی انجام بده!",
    "با یه لهجه‌ی مختلف (مثلاً اصفهانی یا مشهدی) حرف بزن!",
    "از پنجره داد بزن: «من بهترین‌ام!»",
    "یه نقاشی از یه حیوان بکش و به بقیه نشون بده!",
    "۳۰ ثانیه مثل یه ربات حرف بزن!",
    "یه شعر کوتاه برای یه نفر تو گروه بگو!"
]

# لیست سوالات جرعت/حقیقت - حالت داغ 🔥
truth_questions_hot = [
    "تا حالا عاشق شدی؟ برا کی؟",
    "آخرین باری که دروغ گفتی کی بود و به کی؟",
    "چیزی که هیچ کس ازت نمیدونه رو بگو!",
    "بهترین و بدترین خصوصیت خودت چیه؟",
    "تا حالا به کسی خیانت کردی؟ (عاطفی یا غیرعاطفی)",
    "اگر الان می‌تونستی با یه نفر تو این گروه قرار بذاری، کی رو انتخاب می‌کردی؟",
    "آخرین باری که به کسی حسودی کردی کی بود؟",
    "تا حالا از کسی پول قرض گرفتی و پس ندادی؟",
    "چیزی که از خانواده‌ات پنهون می‌کنی چیه؟",
    "اگر مجبور باشی یکی از دوستات رو انتخاب کنی که دیگه نبینیش، کی رو انتخاب می‌کنی؟"
]

dare_questions_hot = [
    "به یک نفر تو گروه بگو: «من عاشقتم!» (با لحن جدی)",
    "۳۰ ثانیه چشمات رو ببند و هرچی می‌گی رو باور کن!",
    "یه راز از خودت رو به همه بگو!",
    "با کسی که کنارت نشسته ۱۰ ثانیه دست بده و تو چشماش نگاه کن!",
    "به خودت توی آینه نگاه کن و بگو: «من از همه بهترم!»",
    "چیزی که بیشتر از همه ازش می‌ترسی رو بگو!",
    "یه چالش جسارت‌آمیز که تا حالا انجام ندادی رو انتخاب کن و انجام بده!",
    "به کسی که بیشتر از همه دوستش داری پیام بده و بگو: «تو خاصی!»",
    "اگر مجبور باشی یه شب رو با یه نفر تو این گروه بگذرونی، کی رو انتخاب می‌کنی؟",
    "یه کار احمقانه که هیچ وقت انجامش نمی‌دادی رو الان انجام بده!"
]

# ============ دستورات اصلی ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /start"""
    user = update.effective_user
    keyboard = [
        [
            InlineKeyboardButton("🎮 بازی جرعت/حقیقت", callback_data="game_truth_dare"),
            InlineKeyboardButton("🤫 نجوا (Whisper)", callback_data="whisper")
        ],
        [
            InlineKeyboardButton("ℹ️ اطلاعات ربات", callback_data="info"),
            InlineKeyboardButton("📚 راهنما", callback_data="help")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🤖 **سلام {user.first_name}!** عزیزم! 🎉\n\n"
        f"من یه ربات پیشرفته با قابلیت‌های خاص هستم!\n\n"
        f"**🌟 قابلیت‌ها:**\n"
        f"• 🎮 بازی جرعت/حقیقت (۲ حالت مختلف)\n"
        f"• 🤫 ارسال پیام‌های نجوا (Whisper)\n"
        f"• ✨ و کلی چیزای دیگه!\n\n"
        f"از دکمه‌های زیر استفاده کن یا دستورات رو بفرست:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /help"""
    await update.message.reply_text(
        "📚 **راهنمای کامل ربات**\n\n"
        "**🎮 بازی جرعت/حقیقت:**\n"
        "/game - شروع بازی (انتخاب حالت)\n"
        "/truth - دریافت سوال حقیقت\n"
        "/dare - دریافت چالش جرعت\n"
        "/game_mode - تغییر حالت بازی (دوستانه/داغ)\n\n"
        "**🤫 نجوا (Whisper):**\n"
        "/whisper [کاربر] [پیام] - ارسال پیام مخفی\n"
        "/whisper_history - مشاهده تاریخچه نجواها\n\n"
        "**📋 سایر دستورات:**\n"
        "/start - صفحه اصلی\n"
        "/help - این راهنما\n"
        "/info - اطلاعات ربات\n"
        "/time - زمان فعلی\n"
        "/echo [متن] - تکرار متن شما\n\n"
        "💡 **نکته**: برای نجوا، کاربر رو با @ یا آیدی عددی وارد کن!",
        parse_mode='Markdown'
    )

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /info"""
    await update.message.reply_text(
        f"📊 **اطلاعات فنی ربات**\n\n"
        f"• **نسخه**: 3.0.0 🚀\n"
        f"• **نوع اتصال**: Webhook ✅\n"
        f"• **میزبان**: Render.com\n"
        f"• **وضعیت**: آنلاین 🟢\n"
        f"• **قابلیت‌ها**:\n"
        f"  - بازی جرعت/حقیقت با ۲ حالت\n"
        f"  - سامانه نجوا (Whisper)\n"
        f"  - پاسخ‌دهی فوق‌سریع\n\n"
        f"⚡️ **آماده به کار!**",
        parse_mode='Markdown'
    )

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /echo - تکرار متن کاربر"""
    if context.args:
        text = ' '.join(context.args)
        await update.message.reply_text(f"🔊 **شما گفتید**: {text}", parse_mode='Markdown')
    else:
        await update.message.reply_text("❌ لطفاً یک متن برای تکرار وارد کنید!\nمثال: `/echo سلام دنیا`", parse_mode='Markdown')

async def time_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /time - نمایش زمان فعلی"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    await update.message.reply_text(f"🕐 **زمان فعلی**: {now}", parse_mode='Markdown')

# ============ بازی جرعت/حقیقت ============

async def game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع بازی جرعت/حقیقت"""
    user_id = str(update.effective_user.id)
    
    # تنظیم حالت پیش‌فرض
    if user_id not in user_settings:
        user_settings[user_id] = {'game_mode': 'friendly'}
    
    mode = user_settings[user_id]['game_mode']
    mode_emoji = "🤗 دوستانه" if mode == 'friendly' else "🔥 داغ"
    
    keyboard = [
        [
            InlineKeyboardButton("❓ حقیقت (Truth)", callback_data=f"truth_{mode}"),
            InlineKeyboardButton("⚡️ جرعت (Dare)", callback_data=f"dare_{mode}")
        ],
        [
            InlineKeyboardButton(f"🔄 تغییر حالت (حالت: {mode_emoji})", callback_data="change_mode")
        ],
        [
            InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back_to_menu")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🎮 **بازی جرعت/حقیقت**\n\n"
        f"حالت فعلی: {mode_emoji}\n\n"
        f"یکی از گزینه‌ها رو انتخاب کن:\n"
        f"• ❓ حقیقت: یه سوال صادقانه دریافت کن\n"
        f"• ⚡️ جرعت: یه چالش جسورانه دریافت کن\n\n"
        f"می‌تونی حالت بازی رو هم عوض کنی!",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def game_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تغییر حالت بازی"""
    user_id = str(update.effective_user.id)
    
    if user_id not in user_settings:
        user_settings[user_id] = {'game_mode': 'friendly'}
    
    current_mode = user_settings[user_id]['game_mode']
    new_mode = 'hot' if current_mode == 'friendly' else 'friendly'
    user_settings[user_id]['game_mode'] = new_mode
    
    mode_name = "🔥 داغ" if new_mode == 'hot' else "🤗 دوستانه"
    await update.message.reply_text(
        f"✅ حالت بازی به **{mode_name}** تغییر کرد!",
        parse_mode='Markdown'
    )

async def get_truth(update: Update, context: ContextTypes.DEFAULT_TYPE, mode='friendly'):
    """دریافت سوال حقیقت"""
    if mode == 'friendly':
        question = random.choice(truth_questions_friendly)
        mode_name = "🤗 دوستانه"
    else:
        question = random.choice(truth_questions_hot)
        mode_name = "🔥 داغ"
    
    await update.message.reply_text(
        f"❓ **سوال حقیقت** (حالت: {mode_name})\n\n"
        f"➡️ {question}\n\n"
        f"🤔 راستش رو بگو!",
        parse_mode='Markdown'
    )

async def get_dare(update: Update, context: ContextTypes.DEFAULT_TYPE, mode='friendly'):
    """دریافت چالش جرعت"""
    if mode == 'friendly':
        dare = random.choice(dare_questions_friendly)
        mode_name = "🤗 دوستانه"
    else:
        dare = random.choice(dare_questions_hot)
        mode_name = "🔥 داغ"
    
    await update.message.reply_text(
        f"⚡️ **چالش جرعت** (حالت: {mode_name})\n\n"
        f"➡️ {dare}\n\n"
        f"💪 جسور باش و انجامش بده!",
        parse_mode='Markdown'
    )

# ============ نجوا (Whisper) ============

async def whisper(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ارسال پیام نجوا به کاربر دیگر"""
    try:
        # بررسی وجود کاربر و پیام
        if not context.args or len(context.args) < 2:
            await update.message.reply_text(
                "❌ **نحوه استفاده از نجوا:**\n\n"
                "`/whisper @username پیام شما`\n"
                "یا\n"
                "`/whisper 123456789 پیام شما`\n\n"
                "مثال: `/whisper @Ali سلام! چطوری؟`",
                parse_mode='Markdown'
            )
            return
        
        # استخراج کاربر هدف و پیام
        target = context.args[0]
        message_text = ' '.join(context.args[1:])
        
        sender = update.effective_user
        chat_id = update.effective_chat.id
        
        # پیدا کردن کاربر هدف
        target_user = None
        try:
            if target.startswith('@'):
                # با یوزرنیم
                target_user = await bot.get_chat(target)
            else:
                # با آیدی عددی
                target_user = await bot.get_chat(int(target))
        except:
            await update.message.reply_text(
                "❌ کاربر مورد نظر پیدا نشد! لطفاً یوزرنیم یا آیدی درست رو وارد کن."
            )
            return
        
        # ارسال پیام نجوا به کاربر هدف (به صورت خصوصی)
        try:
            await bot.send_message(
                chat_id=target_user.id,
                text=f"🤫 **پیام نجوا از {sender.first_name}**\n\n{message_text}\n\n🔒 این پیام خصوصی و مخفی است!"
            )
            
            # ذخیره در تاریخچه
            whisper_key = f"{sender.id}_{target_user.id}"
            if whisper_key not in whisper_history:
                whisper_history[whisper_key] = []
            whisper_history[whisper_key].append({
                'from': sender.first_name,
                'to': target_user.first_name,
                'message': message_text,
                'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            
            # تایید برای فرستنده
            await update.message.reply_text(
                f"✅ پیام نجوا به {target_user.first_name} ارسال شد! 🤫\n\n"
                f"پیام: {message_text}"
            )
            
        except Exception as e:
            await update.message.reply_text(
                f"❌ خطا در ارسال پیام نجوا: {str(e)}\n\n"
                "ممکنه کاربر ربات رو استارت نکرده باشه یا محدودیت ارسال پیام داشته باشه."
            )
            
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {str(e)}")

async def whisper_history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش تاریخچه نجواها"""
    user_id = update.effective_user.id
    history_text = "📜 **تاریخچه نجواهای شما**\n\n"
    found = False
    
    for key, messages in whisper_history.items():
        if str(user_id) in key:
            found = True
            for msg in messages[-5:]:  # آخرین ۵ تا
                if msg['from'] == update.effective_user.first_name:
                    history_text += f"📤 به {msg['to']}: {msg['message']}\n"
                    history_text += f"   🕐 {msg['time']}\n\n"
                else:
                    history_text += f"📥 از {msg['from']}: {msg['message']}\n"
                    history_text += f"   🕐 {msg['time']}\n\n"
    
    if not found:
        history_text = "📭 هنوز هیچ نجوایی نداشتی!"
    
    await update.message.reply_text(history_text[:4000], parse_mode='Markdown')

# ============ Callback Query Handler ============

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت دکمه‌ها"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = str(query.from_user.id)
    
    # تنظیمات پیش‌فرض کاربر
    if user_id not in user_settings:
        user_settings[user_id] = {'game_mode': 'friendly'}
    
    if data == "game_truth_dare":
        # نمایش منوی بازی
        await game(update, context)
        
    elif data == "whisper":
        # راهنمای نجوا
        await query.edit_message_text(
            "🤫 **ارسال پیام نجوا**\n\n"
            "برای ارسال پیام مخفی به یک کاربر، از دستور زیر استفاده کن:\n\n"
            "`/whisper @username پیام شما`\n"
            "یا\n"
            "`/whisper 123456789 پیام شما`\n\n"
            "مثال:\n"
            "`/whisper @Ali سلام! چطوری؟`\n\n"
            "🔒 پیام‌ها فقط به کاربر هدف می‌رسه!",
            parse_mode='Markdown'
        )
        
    elif data == "info":
        await info(update, context)
        
    elif data == "help":
        await help_command(update, context)
        
    elif data.startswith("truth_"):
        mode = data.split("_")[1]
        user_id = str(update.effective_user.id)
        
        if user_id in user_settings:
            mode = user_settings[user_id]['game_mode']
        else:
            user_settings[user_id] = {'game_mode': 'friendly'}
            mode = user_settings[user_id]['game_mode']
        
        if mode == 'friendly':
            question = random.choice(truth_questions_friendly)
        else:
            question = random.choice(truth_questions_hot)
        
        await query.edit_message_text(
            f"❓ **سوال حقیقت**\n\n"
            f"➡️ {question}\n\n"
            f"🤔 راستش رو بگو!",
            parse_mode='Markdown'
        )
        
    elif data.startswith("dare_"):
        mode = data.split("_")[1]
        user_id = str(update.effective_user.id)
        
        if user_id in user_settings:
            mode = user_settings[user_id]['game_mode']
        else:
            user_settings[user_id] = {'game_mode': 'friendly'}
            mode = user_settings[user_id]['game_mode']
        
        if mode == 'friendly':
            dare = random.choice(dare_questions_friendly)
        else:
            dare = random.choice(dare_questions_hot)
        
        await query.edit_message_text(
            f"⚡️ **چالش جرعت**\n\n"
            f"➡️ {dare}\n\n"
            f"💪 جسور باش و انجامش بده!",
            parse_mode='Markdown'
        )
        
    elif data == "change_mode":
        # تغییر حالت بازی
        current_mode = user_settings[user_id]['game_mode']
        new_mode = 'hot' if current_mode == 'friendly' else 'friendly'
        user_settings[user_id]['game_mode'] = new_mode
        mode_name = "🔥 داغ" if new_mode == 'hot' else "🤗 دوستانه"
        
        # نمایش منوی بازی با حالت جدید
        keyboard = [
            [
                InlineKeyboardButton("❓ حقیقت (Truth)", callback_data=f"truth_{new_mode}"),
                InlineKeyboardButton("⚡️ جرعت (Dare)", callback_data=f"dare_{new_mode}")
            ],
            [
                InlineKeyboardButton(f"🔄 تغییر حالت (حالت: {mode_name})", callback_data="change_mode")
            ],
            [
                InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back_to_menu")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🎮 **بازی جرعت/حقیقت**\n\n"
            f"حالت فعلی: {mode_name}\n\n"
            f"یکی از گزینه‌ها رو انتخاب کن:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    elif data == "back_to_menu":
        # بازگشت به منوی اصلی
        keyboard = [
            [
                InlineKeyboardButton("🎮 بازی جرعت/حقیقت", callback_data="game_truth_dare"),
                InlineKeyboardButton("🤫 نجوا (Whisper)", callback_data="whisper")
            ],
            [
                InlineKeyboardButton("ℹ️ اطلاعات ربات", callback_data="info"),
                InlineKeyboardButton("📚 راهنما", callback_data="help")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🤖 **منوی اصلی**\n\n"
            f"یکی از گزینه‌ها رو انتخاب کن:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

# ============ ثبت دستورات ============

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(CommandHandler("info", info))
application.add_handler(CommandHandler("echo", echo))
application.add_handler(CommandHandler("time", time_command))
application.add_handler(CommandHandler("game", game))
application.add_handler(CommandHandler("game_mode", game_mode))
application.add_handler(CommandHandler("whisper", whisper))
application.add_handler(CommandHandler("whisper_history", whisper_history_command))
application.add_handler(CallbackQueryHandler(button_handler))

# ============ مسیرهای Flask ============

@app.route('/')
def health_check():
    """مسیر سلامت برای رندر"""
    return jsonify({
        'status': 'ok',
        'message': 'ربات تلگرام فعال است ✅',
        'version': '3.0.0',
        'webhook': f"{WEBHOOK_URL}/webhook",
        'features': ['Game', 'Whisper', 'Interactive']
    }), 200

@app.route('/webhook', methods=['POST'])
def webhook():
    """مسیر دریافت Webhook از تلگرام"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data received'}), 400
        
        # پردازش درخواست با اپلیکیشن
        async def process_update():
            update = Update.de_json(data, bot)
            await application.process_update(update)
        
        asyncio.run(process_update())
        
        return jsonify({'status': 'ok'}), 200
        
    except Exception as e:
        logger.error(f"❌ خطا در پردازش Webhook: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/set-webhook', methods=['GET'])
def set_webhook_route():
    """مسیر دستی برای تنظیم Webhook"""
    try:
        bot.delete_webhook()
        bot.set_webhook(f"{WEBHOOK_URL}/webhook")
        return jsonify({
            'status': 'success',
            'message': 'Webhook تنظیم شد',
            'webhook_url': f"{WEBHOOK_URL}/webhook"
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/delete-webhook', methods=['GET'])
def delete_webhook():
    """مسیر حذف Webhook"""
    try:
        bot.delete_webhook()
        return jsonify({
            'status': 'success',
            'message': 'Webhook با موفقیت حذف شد'
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# ============ اجرای اصلی ============

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"🚀 ربات نسخه 3.0.0 با Webhook روی پورت {port} در حال اجراست...")
    app.run(host='0.0.0.0', port=port)
