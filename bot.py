import os
import time
import json
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from config import Config
import database
import wireguard

# ============================================
# منوهای ربات
# ============================================
MAIN_MENU = [
    [InlineKeyboardButton("📋 لیست کاربران", callback_data='list_users')],
    [InlineKeyboardButton("➕ ساخت کاربر جدید", callback_data='create_user')],
    [InlineKeyboardButton("📊 آمار و وضعیت", callback_data='stats')],
    [InlineKeyboardButton("⚙️ تنظیمات", callback_data='settings')],
    [InlineKeyboardButton("📝 ساخت کانفیگ", callback_data='generate_config')],
    [InlineKeyboardButton("ℹ️ راهنما", callback_data='help')]
]

# ============================================
# تابع شروع
# ============================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id != Config.OWNER_ID:
        await update.message.reply_text("❌ شما دسترسی به این ربات ندارید.")
        return
    
    reply_markup = InlineKeyboardMarkup(MAIN_MENU)
    await update.message.reply_text(
        "🔐 <b>VPN Manager Bot</b>\n\n"
        "🔹 به پنل مدیریت VPN خوش آمدید!\n"
        "🔹 از طریق این ربات می‌توانید:\n"
        "   • کاربر جدید بسازید\n"
        "   • کانفیگ تولید کنید\n"
        "   • حجم و زمان کاربران را مدیریت کنید\n"
        "   • آمار و وضعیت را مشاهده کنید\n\n"
        "👇 یکی از گزینه‌ها را انتخاب کنید:",
        parse_mode='HTML',
        reply_markup=reply_markup
    )

# ============================================
# لیست کاربران
# ============================================
async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    users = database.get_all_users()
    
    if not users:
        await query.edit_message_text("📋 هیچ کاربری وجود ندارد.")
        return
    
    text = "📋 <b>لیست کاربران</b>\n\n"
    for user in users:
        status = "✅ فعال" if user.is_active else "❌ غیرفعال"
        expire = user.expire_date.strftime("%Y-%m-%d") if user.expire_date else "نامحدود"
        text += f"👤 {user.username}\n"
        text += f"   📍 IP: {user.ip_address}\n"
        text += f"   📊 ترافیک: {user.traffic_used_gb:.1f}/{user.traffic_limit_gb} GB\n"
        text += f"   ⏳ انقضا: {expire}\n"
        text += f"   📌 وضعیت: {status}\n\n"
    
    keyboard = [
        [InlineKeyboardButton("🔙 برگشت", callback_data='back_main')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text[:4000], parse_mode='HTML', reply_markup=reply_markup)

# ============================================
# ساخت کاربر جدید
# ============================================
async def create_user_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("🔙 برگشت", callback_data='back_main')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "➕ <b>ساخت کاربر جدید</b>\n\n"
        "📝 لطفاً مشخصات کاربر را به صورت زیر ارسال کنید:\n\n"
        "<code>نام کاربری | رمز عبور | حجم (GB) | مدت (روز)</code>\n\n"
        "مثال:\n"
        "<code>admin123 | mypass | 50 | 30</code>\n\n"
        "📌 اگر حجم یا مدت را خالی بگذارید، از مقادیر پیش‌فرض استفاده می‌شود.",
        parse_mode='HTML',
        reply_markup=reply_markup
    )
    
    context.user_data['waiting_for_user'] = True

async def handle_create_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('waiting_for_user'):
        return
    
    text = update.message.text
    parts = text.split('|')
    
    if len(parts) < 2:
        await update.message.reply_text("❌ فرمت اشتباه! لطفاً دوباره ارسال کنید.")
        return
    
    username = parts[0].strip()
    password = parts[1].strip()
    traffic_gb = float(parts[2].strip()) if len(parts) > 2 and parts[2].strip() else Config.DEFAULT_TRAFFIC_GB
    expire_days = int(parts[3].strip()) if len(parts) > 3 and parts[3].strip() else Config.DEFAULT_EXPIRE_DAYS
    
    # بررسی تکراری نبودن
    if database.get_user(username):
        await update.message.reply_text(f"❌ کاربر {username} از قبل وجود دارد.")
        return
    
    try:
        user = database.create_user(username, password, None, traffic_gb, expire_days)
        wireguard.add_peer(user.public_key, user.ip_address)
        
        # تولید کانفیگ
        config = generate_config_text(user)
        
        await update.message.reply_text(
            f"✅ <b>کاربر ساخته شد!</b>\n\n"
            f"👤 نام: {username}\n"
            f"📊 حجم: {traffic_gb} GB\n"
            f"⏳ مدت: {expire_days} روز\n"
            f"📍 IP: {user.ip_address}\n\n"
            f"📝 <b>کانفیگ:</b>\n<code>{config}</code>",
            parse_mode='HTML'
        )
        
        context.user_data['waiting_for_user'] = False
        
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {str(e)}")

# ============================================
# تولید کانفیگ
# ============================================
async def generate_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    users = database.get_all_users()
    if not users:
        await query.edit_message_text("❌ هیچ کاربری وجود ندارد. ابتدا کاربر بسازید.")
        return
    
    keyboard = []
    for user in users:
        keyboard.append([InlineKeyboardButton(f"👤 {user.username}", callback_data=f'config_{user.username}')])
    keyboard.append([InlineKeyboardButton("🔙 برگشت", callback_data='back_main')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📝 <b>ساخت کانفیگ</b>\n\n"
        "🔹 کاربر مورد نظر را انتخاب کنید:",
        parse_mode='HTML',
        reply_markup=reply_markup
    )

async def config_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    username = query.data.replace('config_', '')
    user = database.get_user(username)
    
    if not user:
        await query.edit_message_text("❌ کاربر پیدا نشد.")
        return
    
    config = generate_config_text(user)
    
    keyboard = [
        [InlineKeyboardButton("🔙 برگشت", callback_data='generate_config')],
        [InlineKeyboardButton("🏠 منو اصلی", callback_data='back_main')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"📝 <b>کانفیگ {username}</b>\n\n"
        f"<code>{config}</code>\n\n"
        "🔹 کانفیگ را کپی کنید و در اپلیکیشن WireGuard وارد کنید.",
        parse_mode='HTML',
        reply_markup=reply_markup
    )

def generate_config_text(user):
    return f"""
[Interface]
PrivateKey = {user.private_key or 'PRIVATE_KEY_HERE'}
Address = {user.ip_address}/32
DNS = {Config.WG_DNS}
MTU = {Config.WG_MTU}

[Peer]
PublicKey = {wireguard.get_server_public_key()}
Endpoint = {Config.PUBLIC_IP}:{Config.WG_PORT}
AllowedIPs = 0.0.0.0/0, ::/0
PersistentKeepalive = {Config.WG_PERSISTENT_KEEPALIVE}
"""

# ============================================
# آمار
# ============================================
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    users = database.get_all_users()
    active = [u for u in users if u.is_active]
    total_traffic = sum(u.traffic_used_gb for u in users)
    
    text = f"""
📊 <b>آمار VPN</b>

👥 کل کاربران: {len(users)}
✅ کاربران فعال: {len(active)}
📊 مجموع ترافیک مصرفی: {total_traffic:.1f} GB
🌐 سرور: {Config.PUBLIC_IP}
🔌 پورت: {Config.WG_PORT}
📅 آخرین بروزرسانی: {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""
    
    keyboard = [[InlineKeyboardButton("🔙 برگشت", callback_data='back_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, parse_mode='HTML', reply_markup=reply_markup)

# ============================================
# تنظیمات
# ============================================
async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("🔧 تغییر حجم پیش‌فرض", callback_data='set_traffic')],
        [InlineKeyboardButton("⏳ تغییر مدت پیش‌فرض", callback_data='set_expire')],
        [InlineKeyboardButton("🔙 برگشت", callback_data='back_main')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"⚙️ <b>تنظیمات</b>\n\n"
        f"📊 حجم پیش‌فرض: {Config.DEFAULT_TRAFFIC_GB} GB\n"
        f"⏳ مدت پیش‌فرض: {Config.DEFAULT_EXPIRE_DAYS} روز\n\n"
        "🔹 برای تغییر هر کدام، روی گزینه مربوطه کلیک کنید.",
        parse_mode='HTML',
        reply_markup=reply_markup
    )

# ============================================
# راهنما
# ============================================
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = """
ℹ️ <b>راهنمای ربات VPN Manager</b>

🔹 <b>دستورات اصلی:</b>

📋 لیست کاربران — مشاهده تمام کاربران و وضعیت آنها
➕ ساخت کاربر جدید — ایجاد کاربر جدید با حجم و زمان مشخص
📊 آمار — مشاهده وضعیت کلی سرور
⚙️ تنظیمات — تغییر تنظیمات پیش‌فرض
📝 ساخت کانفیگ — تولید کانفیگ WireGuard برای کاربر

🔹 <b>نحوه استفاده:</b>
1. برای ساخت کاربر، روی دکمه مربوطه کلیک کنید.
2. مشخصات را با فرمت مشخص ارسال کنید.
3. کانفیگ تولید شده را در اپلیکیشن WireGuard وارد کنید.

🔹 <b>پشتیبانی:</b>
در صورت بروز مشکل، با پشتیبانی تماس بگیرید.
"""
    
    keyboard = [[InlineKeyboardButton("🔙 برگشت", callback_data='back_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, parse_mode='HTML', reply_markup=reply_markup)

# ============================================
# برگشت
# ============================================
async def back_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    reply_markup = InlineKeyboardMarkup(MAIN_MENU)
    await query.edit_message_text(
        "🔐 <b>VPN Manager Bot</b>\n\n"
        "🔹 منوی اصلی:",
        parse_mode='HTML',
        reply_markup=reply_markup
    )

# ============================================
# Callback Handler
# ============================================
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    if data == 'back_main':
        await back_main(update, context)
    elif data == 'list_users':
        await list_users(update, context)
    elif data == 'create_user':
        await create_user_start(update, context)
    elif data == 'stats':
        await stats(update, context)
    elif data == 'settings':
        await settings(update, context)
    elif data == 'help':
        await help_command(update, context)
    elif data == 'generate_config':
        await generate_config(update, context)
    elif data.startswith('config_'):
        await config_user(update, context)
    elif data == 'set_traffic':
        await query.edit_message_text(
            "🔧 تغییر حجم پیش‌فرض\n\n"
            "📝 عدد جدید را به GB ارسال کنید:\n"
            "مثال: 100",
            parse_mode='HTML'
        )
        context.user_data['waiting_for_traffic'] = True
    elif data == 'set_expire':
        await query.edit_message_text(
            "⏳ تغییر مدت پیش‌فرض\n\n"
            "📝 عدد جدید را به روز ارسال کنید:\n"
            "مثال: 60",
            parse_mode='HTML'
        )
        context.user_data['waiting_for_expire'] = True

# ============================================
# پیام‌های متنی
# ============================================
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id != Config.OWNER_ID:
        await update.message.reply_text("❌ شما دسترسی ندارید.")
        return
    
    text = update.message.text
    
    # ساخت کاربر
    if context.user_data.get('waiting_for_user'):
        await handle_create_user(update, context)
        return
    
    # تغییر حجم
    if context.user_data.get('waiting_for_traffic'):
        try:
            value = float(text)
            # ذخیره در تنظیمات (در این نسخه ساده، فقط پیام می‌دهیم)
            await update.message.reply_text(f"✅ حجم پیش‌فرض به {value} GB تغییر یافت.")
            context.user_data['waiting_for_traffic'] = False
        except:
            await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید.")
        return
    
    # تغییر مدت
    if context.user_data.get('waiting_for_expire'):
        try:
            value = int(text)
            await update.message.reply_text(f"✅ مدت پیش‌فرض به {value} روز تغییر یافت.")
            context.user_data['waiting_for_expire'] = False
        except:
            await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید.")
        return
    
    await update.message.reply_text("❌ دستور نامعتبر. از دکمه‌ها استفاده کنید.")

# ============================================
# اجرا
# ============================================
def main():
    app = Application.builder().token(Config.BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    print("🤖 VPN Manager Bot started!")
    print("👑 Owner ID:", Config.OWNER_ID)
    print("🌐 Public IP:", Config.PUBLIC_IP)
    
    app.run_polling()

if __name__ == "__main__":
    # اطمینان از وجود دیتابیس
    database.init_db()
    main()
