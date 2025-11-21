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

# Flask app
app = Flask(__name__)

# PTB Application (async)
bot_app = Application.builder().token(TOKEN).build()

# Event loop para ejecutar funciones async dentro de Flask (sync)
loop = asyncio.get_event_loop()


# ---------------------------
# FORMULAS
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
# START
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


# ---------------------------
# CALLBACKS
# ---------------------------

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "completar":
        context.user_data["mode"] = "completar"
        await query.message.reply_text(
            "Envíame los valores así:\n\n`s1 p1 p2`\nEjemplo: `100 0.54 0.23`",
            parse_mode="Markdown"
        )

    elif query.data == "total":
        context.user_data["mode"] = "total"
        await query.message.reply_text(
            "Envíame los valores así:\n\n`S p1 p2`\nEjemplo: `1000 0.68 0.28`",
            parse_mode="Markdown"
        )


# ---------------------------
# TEXTO
# ---------------------------

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = context.user_data.get("mode")

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
            f"Debes comprar: *{s2:.2f} USD*\n"
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


# ---------------------------
# HANDLERS
# ---------------------------

bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CallbackQueryHandler(button_handler))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))


# ---------------------------
# FLASK + WEBHOOK
# ---------------------------

@app.get("/setwebhook")
def set_webhook():
    loop.run_until_complete(bot_app.bot.set_webhook(url=WEBHOOK_URL))
    return "Webhook set"

@app.post("/")
def receive_update():
    """Telegram envía updates aquí."""
    data = request.get_json(force=True)
    update = Update.de_json(data, bot_app.bot)

    loop.run_until_complete(bot_app.process_update(update))
    return "OK"


# ---------------------------
# RUN
# ---------------------------

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
