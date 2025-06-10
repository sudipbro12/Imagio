import os
from io import BytesIO
from PIL import Image
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

user_images = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📸 Welcome to Image to PDF Bot!\n\n➕ Send images\n⚙️ Use /convert to choose resize and make PDF.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    photo = update.message.photo[-1]
    file = await photo.get_file()
    image_bytes = await file.download_as_bytearray()
    image = Image.open(BytesIO(image_bytes)).convert("RGB")

    if user_id not in user_images:
        user_images[user_id] = []

    user_images[user_id].append(image)

    await update.message.reply_text("✅ Image saved. Use /convert to make PDF.")

async def convert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in user_images or len(user_images[user_id]) == 0:
        await update.message.reply_text("❌ No images found. Please send some images first.")
        return

    keyboard = [
        [InlineKeyboardButton("🔄 Original Size", callback_data="resize_100")],
        [InlineKeyboardButton("📏 50% Size", callback_data="resize_50")],
        [InlineKeyboardButton("🎯 Custom %", callback_data="resize_custom_percent")],
        [InlineKeyboardButton("✍️ Width x Height", callback_data="resize_custom_wh")]
    ]
    await update.message.reply_text("Choose image resize option before converting:", reply_markup=InlineKeyboardMarkup(keyboard))

async def resize_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if user_id not in user_images:
        await query.edit_message_text("❌ No images to resize.")
        return

    data = query.data

    if data == "resize_50":
        percent = 50
    elif data == "resize_100":
        percent = 100
    elif data == "resize_custom_percent":
        await query.edit_message_text("🔢 Send resize percentage (1–200):")
        context.user_data["waiting_for_percent"] = True
        return
    elif data == "resize_custom_wh":
        await query.edit_message_text("📐 Send width x height like `800x600`:")
        context.user_data["waiting_for_wh"] = True
        return
    else:
        percent = 100

    resized_images = []
    for img in user_images[user_id]:
        new_size = (int(img.width * percent / 100), int(img.height * percent / 100))
        resized_images.append(img.resize(new_size))

    pdf_bytes = BytesIO()
    resized_images[0].save(pdf_bytes, save_all=True, append_images=resized_images[1:], format="PDF")
    pdf_bytes.seek(0)

    await context.bot.send_document(chat_id=user_id, document=pdf_bytes, filename="converted.pdf")
    await query.edit_message_text(f"✅ Converted with {percent}% size.")
    user_images[user_id] = []

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()

    if context.user_data.get("waiting_for_percent"):
        try:
            percent = int(text)
            if not 1 <= percent <= 200:
                raise ValueError
            resized_images = [
                img.resize((int(img.width * percent / 100), int(img.height * percent / 100)))
                for img in user_images[user_id]
            ]

            pdf_bytes = BytesIO()
            resized_images[0].save(pdf_bytes, save_all=True, append_images=resized_images[1:], format="PDF")
            pdf_bytes.seek(0)

            await update.message.reply_document(document=pdf_bytes, filename="converted.pdf")
            context.user_data["waiting_for_percent"] = False
            user_images[user_id] = []

        except:
            await update.message.reply_text("❗ Please send a valid number (1–200).")

    elif context.user_data.get("waiting_for_wh"):
        try:
            width, height = map(int, text.lower().replace("x", " ").split())
            if width <= 0 or height <= 0:
                raise ValueError

            resized_images = [img.resize((width, height)) for img in user_images[user_id]]
            pdf_bytes = BytesIO()
            resized_images[0].save(pdf_bytes, save_all=True, append_images=resized_images[1:], format="PDF")
            pdf_bytes.seek(0)

            await update.message.reply_document(document=pdf_bytes, filename="converted.pdf")
            context.user_data["waiting_for_wh"] = False
            user_images[user_id] = []

        except:
            await update.message.reply_text("❗ Format error. Please send like `800x600`")

# === Bot Initialization ===
app = ApplicationBuilder().token("7652070193:AAHJS653q4iafEB1230cO-AiozAGY_mZumE").build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
app.add_handler(CommandHandler("convert", convert))
app.add_handler(CallbackQueryHandler(resize_handler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

app.run_polling()
