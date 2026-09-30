import logging
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters, ConversationHandler
)
import sqlite3

# --- تنظیمات اختصاصی شما ---
BOT_TOKEN = "8850920519:AAEfrJV1qSSz6sDLz2hi7XyPBUwe1KREVM4"
ADMIN_ID = 8852983684
CHANNEL_USERNAME = "@LuckyRoll_IR"
CHANNEL_LINK = "https://t.me/LuckyRoll_IR"

WAITING_VOUCHER_DEPOSIT, WAITING_RECEIPT_DEPOSIT, WAITING_WITHDRAW_INFO = range(3)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- دیتابیس ---
def init_db():
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance INTEGER DEFAULT 0,
            total_wagered INTEGER DEFAULT 0,
            referred_by INTEGER,
            referral_count INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, balance, total_wagered, referred_by, referral_count FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
        cursor.execute("SELECT user_id, balance, total_wagered, referred_by, referral_count FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
    conn.close()
    return {"user_id": row[0], "balance": row[1], "total_wagered": row[2], "referred_by": row[3], "referral_count": row[4]}

def update_balance(user_id, amount):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

def update_wagered(user_id, amount):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET total_wagered = total_wagered + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

# --- کیبوردها ---
def get_main_keyboard():
    return ReplyKeyboardMarkup([
        ["🎲 بازی تاس", "💰 کیف پول"],
        ["👥 دعوت از دوستان", "📢 کانال ما"]
    ], resize_keyboard=True)

def get_dice_keyboard():
    return ReplyKeyboardMarkup([
        ["🔴 زوج (ضریب ۲)", "🔵 فرد (ضریب ۲)"],
        ["1️⃣ عدد ۱", "2️⃣ عدد ۲", "3️⃣ عدد ۳"],
        ["4️⃣ عدد ۴", "5️⃣ عدد ۵", "6️⃣ عدد ۶"],
        ["🔙 بازگشت به منوی اصلی"]
    ], resize_keyboard=True)

def get_wallet_keyboard():
    return ReplyKeyboardMarkup([
        ["➕ شارژ حساب", "➖ درخواست برداشت"],
        ["🔙 بازگشت به منوی اصلی"]
    ], resize_keyboard=True)

# --- بررسی عضویت کانال با مدیریت خطا ---
async def check_channel_membership(bot, user_id):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logging.error(f"Error checking membership: {e}")
        # در صورت بروز خطا در دسترسی به کانال، اجازه عبور داده می‌شود تا ربات هنگ نکند
        return True

# --- دستور /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    get_user(user_id)
    
    if context.args and len(context.args) > 0:
        try:
            referrer_id = int(context.args[0])
            if referrer_id != user_id:
                conn = sqlite3.connect("bot_database.db")
                cursor = conn.cursor()
                cursor.execute("SELECT referred_by FROM users WHERE user_id = ?", (user_id,))
                ref = cursor.fetchone()[0]
                if not ref:
                    cursor.execute("UPDATE users SET referred_by = ? WHERE user_id = ?", (referrer_id, user_id))
                    conn.commit()
                conn.close()
        except ValueError:
            pass

    is_member = await check_channel_membership(context.bot, user_id)
    if not is_member:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 عضویت در کانال", url=CHANNEL_LINK)],
            [InlineKeyboardButton("عضو شدم ✅", callback_data="check_join")]
        ])
        await update.message.reply_text(
            f"👋 **سلام! به ربات تاس LuckyRoll خوش آمدید.**\n\n"
            f"⚠️️ برای استفاده از ربات، شرط‌بندی و دریافت هدیه‌ها، ابتدا باید عضو کانال رسمی ما شوید:\n\n"
            f"👉 {CHANNEL_USERNAME}\n\n"
            f"پس از عضویت، روی دکمه زیر کلیک کنید.",
            reply_markup=keyboard, parse_mode="Markdown"
        )
        return

    user_data = get_user(user_id)
    if user_data["referred_by"]:
        referrer = get_user(user_data["referred_by"])
        if referrer["referral_count"] < 3:
            conn = sqlite3.connect("bot_database.db")
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET balance = balance + 40000, referral_count = referral_count + 1 WHERE user_id = ?", (user_data["referred_by"],))
            conn.commit()
            conn.close()
            try:
                await context.bot.send_message(
                    chat_id=user_data["referred_by"],
                    text="🎉 کاربر جدیدی با لینک شما عضو شد! **۴۰,۰۰۰ تومان** به کیف پول شما اضافه شد."
                )
            except Exception:
                pass

    await update.message.reply_text(
        "🎲 **به ربات تاس خوش آمدید!**\nلطفاً از منوی زیر گزینه‌ای را انتخاب کنید:",
        reply_markup=get_main_keyboard()
    )

async def check_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if await check_channel_membership(context.bot, user_id):
        try:
            await query.message.delete()
        except Exception:
            pass
        await query.message.reply_text("✅ عضویت شما تایید شد!", reply_markup=get_main_keyboard())
    else:
        await query.message.reply_text("❌ شما هنوز عضو کانال نشده‌اید!")

# --- پردازش پیام‌ها ---
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    text = update.message.text
    user_id = update.effective_user.id
    
    if not await check_channel_membership(context.bot, user_id):
        await start(update, context)
        return

    user = get_user(user_id)

    if text == "🔙 بازگشت به منوی اصلی":
        await update.message.reply_text("منوی اصلی:", reply_markup=get_main_keyboard())
    elif text == "🎲 بازی تاس":
        await update.message.reply_text("شرط خود را انتخاب کنید:\n(مبلغ شرط ثابت ۱۰,۰۰۰ تومان می‌باشد)", reply_markup=get_dice_keyboard())
    elif text in ["🔴 زوج (ضریب ۲)", "🔵 فرد (ضریب ۲)", "1️⃣ عدد ۱", "2️⃣ عدد ۲", "3️⃣ عدد ۳", "4️⃣ عدد ۴", "5️⃣ عدد ۵", "6️⃣ عدد ۶"]:
        BET_AMOUNT = 10000
        if user["balance"] < BET_AMOUNT:
            await update.message.reply_text("⚠️ موجودی شما کافی نیست. لطفاً حساب خود را شارژ کنید.")
            return

        update_balance(user_id, -BET_AMOUNT)
        update_wagered(user_id, BET_AMOUNT)

        msg = await context.bot.send_dice(chat_id=update.effective_chat.id, emoji="🎲")
        dice_val = msg.dice.value

        win = False
        multiplier = 2.0 if "زوج" in text or "فرد" in text else 6.0

        if text == "🔴 زوج (ضریب ۲)" and dice_val % 2 == 0: win = True
        elif text == "🔵 فرد (ضریب ۲)" and dice_val % 2 != 0: win = True
        elif "۱" in text and dice_val == 1: win = True
        elif "۲" in text and dice_val == 2: win = True
        elif "۳" in text and dice_val == 3: win = True
        elif "۴" in text and dice_val == 4: win = True
        elif "۵" in text and dice_val == 5: win = True
        elif "۶" in text and dice_val == 6: win = True

        if win:
            win_amount = int(BET_AMOUNT * multiplier)
            update_balance(user_id, win_amount)
            res = f"🎉 **شما برنده شدید!**\n🎲 عدد تاس: {dice_val}\n💰 برد: {win_amount:,} تومان"
        else:
            res = f"❌ **شما باختید!**\n🎲 عدد تاس: {dice_val}"

        await update.message.reply_text(res, parse_mode="Markdown", reply_markup=get_dice_keyboard())

    elif text == "💰 کیف پول":
        await update.message.reply_text(
            f"💳 **اطلاعات کیف پول شما:**\n\n"
            f"💵 موجودی فعلی: **{user['balance']:,} تومان**\n"
            f"📊 میزان گردش مالی: **{user['total_wagered']:,} / ۳۰۰,۰۰۰ تومان**",
            parse_mode="Markdown", reply_markup=get_wallet_keyboard()
        )
    elif text == "👥 دعوت از دوستان":
        bot_info = await context.bot.get_me()
        link = f"https://t.me/{bot_info.username}?start={user_id}"
        await update.message.reply_text(
            f"👥 **دعوت از دوستان**\n\n"
            f"با اشتراک‌گذاری لینک زیر، به ازای هر دوستی که عضو کانال شود **۴۰,۰۰۰ تومان** هدیه بگیرید (حداکثر ۳ نفر):\n\n"
            f"🔗 `{link}`\n\n"
            f"تعداد دعوت‌های موفق شما: **{user['referral_count']} / ۳**",
            parse_mode="Markdown"
        )
    elif text == "📢 کانال ما":
        await update.message.reply_text(f"کانال رسمی ما:\n{CHANNEL_LINK}")

# --- واریز و برداشت ---
async def start_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎫 کد یو ووچر", callback_data="dep_voucher")],
        [InlineKeyboardButton("💳 کارت به کارت", callback_data="dep_card")]
    ])
    await update.message.reply_text("روش شارژ حساب را انتخاب کنید (حداقل مبلغ ۳۰۰,۰۰۰ تومان):", reply_markup=keyboard)

async def deposit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "dep_voucher":
        await query.message.reply_text("لطفاً کد یو ووچر خود را ارسال کنید:")
        return WAITING_VOUCHER_DEPOSIT
    elif query.data == "dep_card":
        await query.message.reply_text("لطفاً مبلغ واریزی را واریز کرده و **عکس رسید** را ارسال کنید:")
        return WAITING_RECEIPT_DEPOSIT

async def process_voucher(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text
    user_id = update.effective_user.id
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تایید (۳۰۰ هزار تومان)", callback_data=f"app_dep_{user_id}_300000"),
         InlineKeyboardButton("❌ رد", callback_data=f"rej_dep_{user_id}")]
    ])
    await context.bot.send_message(chat_id=ADMIN_ID, text=f"📥 **درخواست شارژ (ووچر)**\nاز کاربر: `{user_id}`\nکد: `{code}`", reply_markup=keyboard, parse_mode="Markdown")
    await update.message.reply_text("درخواست شارژ ثبت شد و پس از بررسی ادمین حساب شما شارژ می‌شود.", reply_markup=get_main_keyboard())
    return ConversationHandler.END

async def process_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_id = update.message.photo[-1].file_id
    user_id = update.effective_user.id
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تایید (۳۰۰ هزار تومان)", callback_data=f"app_dep_{user_id}_300000"),
         InlineKeyboardButton("❌ رد", callback_data=f"rej_dep_{user_id}")]
    ])
    await context.bot.send_photo(chat_id=ADMIN_ID, photo=photo_id, caption=f"📥 **درخواست شارژ (رسید کارت)**\nاز کاربر: `{user_id}`", reply_markup=keyboard, parse_mode="Markdown")
    await update.message.reply_text("رسید شما دریافت شد و پس از بررسی ادمین حساب شارژ خواهد شد.", reply_markup=get_main_keyboard())
    return ConversationHandler.END

async def start_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    if user["balance"] < 300000:
        await update.message.reply_text("❌ حداقل مبلغ برداشت ۳۰۰,۰۰۰ تومان است.")
        return ConversationHandler.END
    if user["total_wagered"] < 300000:
        await update.message.reply_text("❌ شما هنوز شرط حداقل ۳۰۰,۰۰۰ تومان گردش مالی را برای برداشت برآورده نکرده‌اید.")
        return ConversationHandler.END

    await update.message.reply_text("لطفاً **شماره کارت و نام صاحب حساب** یا درخواست ووچر خود را جهت دریافت ارسال کنید:")
    return WAITING_WITHDRAW_INFO

async def process_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    info = update.message.text
    user_id = update.effective_user.id
    user = get_user(user_id)
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تایید تسویه", callback_data=f"app_wd_{user_id}_{user['balance']}"),
         InlineKeyboardButton("❌ رد درخواست", callback_data=f"rej_wd_{user_id}")]
    ])
    await context.bot.send_message(chat_id=ADMIN_ID, text=f"📤 **درخواست برداشت**\nکاربر: `{user_id}`\nمبلغ: {user['balance']:,} تومان\nاطلاعات: {info}", reply_markup=keyboard, parse_mode="Markdown")
    await update.message.reply_text("درخواست برداشت ثبت شد و به ادمین ارسال گردید.", reply_markup=get_main_keyboard())
    return ConversationHandler.END

# --- مدیریت تایید ادمین ---
async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()

    parts = data.split("_")
    action, target_type, target_user = parts[0], parts[1], int(parts[2])

    if action == "app" and target_type == "dep":
        amount = int(parts[3])
        update_balance(target_user, amount)
        await query.message.edit_reply_markup(reply_markup=None)
        await query.message.reply_text("✅ واریزی تایید شد.")
        await context.bot.send_message(chat_id=target_user, text=f"🎉 حساب شما به مبلغ {amount:,} تومان شارژ شد.")
    elif action == "rej" and target_type == "dep":
        await query.message.edit_reply_markup(reply_markup=None)
        await query.message.reply_text("❌ درخواست واریزی رد شد.")
        await context.bot.send_message(chat_id=target_user, text="❌ درخواست شارژ حساب شما رد شد.")
    elif action == "app" and target_type == "wd":
        amount = int(parts[3])
        update_balance(target_user, -amount)
        await query.message.edit_reply_markup(reply_markup=None)
        await query.message.reply_text("✅ درخواست برداشت تایید شد و از حساب کسر گردید.")
        await context.bot.send_message(chat_id=target_user, text="✅ درخواست برداشت شما تایید و تسویه شد.")
    elif action == "rej" and target_type == "wd":
        await query.message.edit_reply_markup(reply_markup=None)
        await query.message.reply_text("❌ درخواست برداشت رد شد.")
        await context.bot.send_message(chat_id=target_user, text="❌ درخواست برداشت شما رد شد.")

# --- اصلی ---
if __name__ == "__main__":
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    dep_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^➕ شارژ حساب$"), start_deposit)],
        states={
            WAITING_VOUCHER_DEPOSIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_voucher)],
            WAITING_RECEIPT_DEPOSIT: [MessageHandler(filters.PHOTO, process_receipt)],
        },
        fallbacks=[],
    )

    wd_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^➖ درخواست برداشت$"), start_withdraw)],
        states={
            WAITING_WITHDRAW_INFO: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_withdraw)],
        },
        fallbacks=[],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_join_callback, pattern="^check_join$"))
    app.add_handler(CallbackQueryHandler(deposit_callback, pattern="^dep_"))
    app.add_handler(CallbackQueryHandler(admin_callback, pattern="^(app|rej)_"))
    app.add_handler(dep_conv)
    app.add_handler(wd_conv)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("ربات با موفقیت فعال شد...")
    app.run_polling()
         
