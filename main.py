import os
import random
import json
import logging
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ---------------- LOGGING ----------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ---------------- ENV VARIABLES ----------------
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_CONTACT = os.environ.get("ADMIN_CONTACT")  # telegram username WITHOUT @

if not BOT_TOKEN or not ADMIN_CONTACT:
    raise RuntimeError("BOT_TOKEN or ADMIN_CONTACT missing")

# ---------------- CONFIG ----------------
DATA_FILE = "users_data.json"
FREE_SIGNAL_LIMIT = 20
EXPIRY_MINUTES = 3
TRADING_ACTIONS = ["BUY", "SELL"]

TRADING_PAIRS = [
    "BTC/USD OTC", "ETH/USD OTC", "EUR/USD OTC", "GBP/USD OTC",
    "USD/JPY OTC", "AUD/USD OTC", "USD/CAD OTC", "GOLD",
    "TESLA OTC", "META OTC", "AMAZON OTC"
]

# ---------------- DATA STORAGE ----------------
def load_user_data():
    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            for u in data.values():
                if u.get("paid_until"):
                    u["paid_until"] = datetime.strptime(
                        u["paid_until"], "%Y-%m-%d %H:%M:%S"
                    )
            return {int(k): v for k, v in data.items()}
    except:
        return {}

def save_user_data():
    out = {}
    for uid, u in user_data.items():
        out[str(uid)] = {
            "signals": u.get("signals", 0),
            "paid_until": u["paid_until"].strftime("%Y-%m-%d %H:%M:%S")
            if u.get("paid_until") else None
        }
    with open(DATA_FILE, "w") as f:
        json.dump(out, f, indent=2)

user_data = load_user_data()

# ---------------- CORE LOGIC ----------------
def next_trade_time():
    t = datetime.now() + timedelta(minutes=EXPIRY_MINUTES)
    if t.minute % 2 != 0:
        t += timedelta(minutes=1)
    return t.replace(second=0, microsecond=0)

def generate_signal(user_id: int):
    if user_id not in user_data:
        user_data[user_id] = {"signals": 0, "paid_until": None}

    user = user_data[user_id]
    now = datetime.now()

    paid = user.get("paid_until") and user["paid_until"] > now

    if not paid and user["signals"] >= FREE_SIGNAL_LIMIT:
        return None, (
            "💰 Free limit reached.\n"
            f"Contact admin: @{ADMIN_CONTACT}"
        )

    pair = random.choice(TRADING_PAIRS)
    action = random.choice(TRADING_ACTIONS)
    trade_time = next_trade_time().strftime("%H:%M")

    emoji = "🟢" if action == "BUY" else "🔴"
    signal = f"{emoji} *{pair}* — *{action}* | 2min | {trade_time}"

    if not paid:
        user["signals"] += 1

    save_user_data()

    if paid:
        footer = f"\n(Unlimited — expires {user['paid_until'].date()})"
    else:
        footer = f"\n(Free left: {FREE_SIGNAL_LIMIT - user['signals']})"

    return signal, footer

# ---------------- COMMANDS ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚡ IQ OPTION SIGNAL BOT\n\n"
        "/signal — get signal\n"
        "/subscribe — subscription info\n"
        "/support — admin contact"
    )

async def signal_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    signal, msg = generate_signal(update.effective_user.id)
    if signal:
        await update.message.reply_text(
            f"{signal}{msg}",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(msg)

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"💳 Unlimited signals available.\n"
        f"Contact @{ADMIN_CONTACT}"
    )

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Admin: @{ADMIN_CONTACT}")

# ---------------- MAIN ----------------
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("signal", signal_cmd))
    app.add_handler(CommandHandler("subscribe", subscribe))
    app.add_handler(CommandHandler("support", support))

    logger.info("Bot started (polling)")
    app.run_polling()

if __name__ == "__main__":
    main()
