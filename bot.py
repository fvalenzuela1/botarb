import os
import logging
import asyncio
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ---------------------------
# CONFIG
# ---------------------------

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

app = Flask(__name__)

# Crear la aplicación de Telegram
bot_app = Application.builder().token(TOKEN).build()

initialized = False  # evita doble init


# ---------------------------
# FUNCIONES DE ARBITRAJE
# ---------------------------

def completar_arbitraje(s1, p1, p2):
    shares1 = s1 / p1
    s2 = shares1 * p2
    return s2, shares1

def arbitraje_total(S, p1, p2):
    s1 = S * p1 / (p1 + p2)
    s2 = S * p2 / (p1 + p2)
    return s1, s2


# ---------------------------
# HANDLERS
# ---------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🧮 Completar arbitraje", callback_data="completar")],
        [InlineKeyboardButton("🔀 Arbitraje total", callback_data="total")]
    ]
    await update.message.reply_text(
        "Selecciona una opción:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id

    if query.data == "completar":
        context.application.user_data[user_id] = {"mode": "completar"}
        await query.message.reply_text(
            "Envíame: `s1 p1 p2`\nEj: `100 0.54 0.23`",
            parse_mode="Markdown"
        )

    elif query.data == "total":
        context.application.user_data[user_id] = {"mode": "total"}
        await query.message.reply_text(
            "Envíame: `S p1 p2`\nEj: `1000 0.68 0.28`",
            parse_mode="Markdown"
        )


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    mode = context.application.user_data.get(user_id, {}).get("mode")

    if not mode:
        await update.message.reply_text("Usa /start para comenzar.")
        return

    try:
        a, b, c = map(float, update.message.text.split())
    except:
        await update.message.reply_text("Formato inválido. Envía 3 números.")
        return

    if mode == "completar":
        s2, shares = completar_arbitraje(a, b, c)
        await update.message.reply_text(
            f"🔍 *Completar Arbitraje*\n\n"
            f"Comprar: *{s2:.2f} USD*\n"
            f"Shares finales: {shares:.4f}",
            parse_mode="Markdown"
        )

    elif mode == "total":
        s1, s2 = arbitraje_total(a, b, c)
        await update.message.reply_text(
            f"🔀 *Arbitraje Total*\n\n"
            f"s1 = {s1:.2f} USD\n"
            f"s2 = {s2:.2f} USD",
            parse_mode="Markdown"
        )


# Registrar handlers
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CallbackQueryHandler(button_handler))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))


# ---------------------------
# INITIALIZACIÓN PTB20+
# ---------------------------

async def ensure_initialized():
    global initialized
    if not initialized:
        await bot_app.initialize()
        await bot_app.start()
        initialized = True


# ---------------------------
# FLASK + WEBHOOK
# ---------------------------

@app.get("/setwebhook")
def set_webhook():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    loop.run_until_complete(ensure_initialized())
    loop.run_until_complete(bot_app.bot.set_webhook(
        url=WEBHOOK_URL,
        allowed_updates=["message", "callback_query"]
    ))
    loop.close()

    return "Webhook configurado"


@app.post("/")
def receive_update():
    data = request.get_json(force=True)
    update = Update.de_json(data, bot_app.bot)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    loop.run_until_complete(ensure_initialized())
    loop.run_until_complete(bot_app.process_update(update))
    loop.close()

    return "OK"


# ---------------------------
# LOCAL RUN
# ---------------------------

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
