import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from flask import Flask, request
import os

logging.basicConfig(level=logging.INFO)

TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

app = Flask(__name__)
bot_app = ApplicationBuilder().token(TOKEN).build()

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
# START / MENU
# ---------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🧮 Completar arbitraje", callback_data="completar")],
        [InlineKeyboardButton("🔀 Arbitraje total", callback_data="total")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Selecciona una opción:", reply_markup=reply_markup)

# ---------------------------
# CALLBACKS
# ---------------------------

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "completar":
        await query.message.reply_text(
            "Envíame los valores así:\n\n"
            "`s1 p1 p2`\n"
            "Ejemplo: `100 0.54 0.23`",
            parse_mode="Markdown"
        )
        context.user_data["mode"] = "completar"

    elif query.data == "total":
        await query.message.reply_text(
            "Envíame los valores así:\n\n"
            "`S p1 p2`\n"
            "Ejemplo: `1000 0.68 0.28`",
            parse_mode="Markdown"
        )
        context.user_data["mode"] = "total"

# ---------------------------
# TEXTO
# ---------------------------

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = context.user_data.get("mode", None)

    if not mode:
        await update.message.reply_text("Usa /start para comenzar.")
        return

    try:
        parts = update.message.text.split()
        a = float(parts[0])
        b = float(parts[1])
        c = float(parts[2])
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
# FLASK WEBHOOK
# ---------------------------

@app.post("/")
def main_webhook():
    update = Update.de_json(request.get_json(force=True), bot_app.bot)
    bot_app.update_queue.put_nowait(update)
    return "OK", 200

@app.get("/setwebhook")
def set_webhook():
    bot_app.bot.set_webhook(url=WEBHOOK_URL)
    return "Webhook set"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
