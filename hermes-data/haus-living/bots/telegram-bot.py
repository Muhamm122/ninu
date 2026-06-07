#!/usr/bin/env python3
"""
Haus Living Telegram Bot
========================
Bot untuk Haus Living (@haus_living1) — brand furnitur premium.
Menggunakan python-telegram-bot v20+ (async).

Cara jalankan:
    export BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"
    python3 telegram-bot.py
"""

import os
import logging
from datetime import datetime
from functools import wraps

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# ─── Konfigurasi ───────────────────────────────────────────────────────────────

# Try env var first, then file
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
if not BOT_TOKEN:
    token_file = os.path.expanduser("~/.hermes/haus-living/secrets/tg_bot_token")
    if os.path.exists(token_file):
        with open(token_file) as f:
            BOT_TOKEN = f.read().strip()
if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN belum diset. Jalankan: export BOT_TOKEN='token_anda'"
    )

WA_NUMBER = "6281234567890"
WA_LINK_BASE = f"https://wa.me/{WA_NUMBER}"
BRAND = "Haus Living"
BRAND_HANDLE = "@haus_living1"

logging.basicConfig(
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ─── Data Produk ───────────────────────────────────────────────────────────────

PRODUCTS = {
    "sofa_lshape": {
        "nama": "Sofa L-Shape",
        "harga": 12_500_000,
        "label": "Rp 12.500.000",
        "desc": "Sofa L-Shape premium dengan busa high-density & kain anti-noda. Cocok untuk ruang tamu modern.",
        "kategori": "Sofa",
    },
    "sofa_3seater": {
        "nama": "Sofa 3-Seater",
        "harga": 8_900_000,
        "label": "Rp 8.900.000",
        "desc": "Sofa 3 dudukan elegan, rangka kayu solid, bantalan empuk.",
        "kategori": "Sofa",
    },
    "sofa_bed": {
        "nama": "Sofa Bed",
        "harga": 10_500_000,
        "label": "Rp 10.500.000",
        "desc": "Sofa bed multifungsi, mekanisme lipat mulus, ideal ruang terbatas.",
        "kategori": "Sofa",
    },
    "meja_makan": {
        "nama": "Meja Makan 6 Seater",
        "harga": 8_900_000,
        "label": "Rp 8.900.000",
        "desc": "Meja makan kayu solid untuk 6 orang, finishing natural.",
        "kategori": "Meja",
    },
    "rak_tv": {
        "nama": "Rak TV Floating",
        "harga": 4_250_000,
        "label": "Rp 4.250.000",
        "desc": "Rak TV wall-mounted minimalis, ruang penyimpanan tersembunyi.",
        "kategori": "Rak & Storage",
    },
    "bed_frame": {
        "nama": "Bed Frame + Storage",
        "harga": 6_800_000,
        "label": "Rp 6.800.000",
        "desc": "Bed frame dengan laci storage di bawah, kayu solid premium.",
        "kategori": "Kamar Tidur",
    },
    "wardrobe": {
        "nama": "Wardrobe 3 Pintu",
        "harga": 7_500_000,
        "label": "Rp 7.500.000",
        "desc": "Lemari pakaian 3 pintu sliding, cerita built-in look.",
        "kategori": "Kamar Tidur",
    },
    "bookshelf": {
        "nama": "Bookshelf 5 Tier",
        "harga": 3_200_000,
        "label": "Rp 3.200.000",
        "desc": "Rak buku 5 susun open-shelf, desain industrial-modern.",
        "kategori": "Rak & Storage",
    },
    "console": {
        "nama": "Console Table",
        "harga": 2_800_000,
        "label": "Rp 2.800.000",
        "desc": "Console table sempit untuk entryway / behind sofa, finishing walnut.",
        "kategori": "Meja",
    },
    "meja_kerja": {
        "nama": "Meja Kerja",
        "harga": 3_500_000,
        "label": "Rp 3.500.000",
        "desc": "Meja kerja minimalis dengan cable management, cocok WFH.",
        "kategori": "Meja",
    },
}

# ─── Data Promo ────────────────────────────────────────────────────────────────

PROMOS = [
    {
        "judul": "🎉 Grand Opening Promo",
        "detail": "Diskon **15%** untuk semua produk Sofa! Berlaku sampai akhir bulan.",
        "kodem": "SOFA15",
    },
    {
        "judul": "🛋️ Bundle Hemat",
        "detail": "Beli Sofa + Meja Makan → diskon **10%** total. Mix & match bebas!",
        "kodem": "BUNDLE10",
    },
    {
        "judul": "🚚 Gratis Ongkir",
        "detail": "Free delivery area Jabodetabek untuk pembelian min **Rp 5.000.000**.",
        "kodem": "FREEDELIVERY",
    },
]

# ─── Simulasi Order Store ──────────────────────────────────────────────────────

# Dict sederhana untuk demo; di produksi gunakan database.
# Key: order_id (str), Value: dict
ORDERS: dict[str, dict] = {}
_next_order_id = 1

# ─── Conversation states ──────────────────────────────────────────────────────

HARGA_CHOOSE, HARGA_SHOW = range(2)
ORDER_PRODUCT, ORDER_QTY, ORDER_NAME, ORDER_ADDRESS = range(2, 6)
STATUS_INPUT = range(1)

# ─── Helper ────────────────────────────────────────────────────────────────────

def wa_link(text: str) -> str:
    """Buat link WhatsApp dengan pesan pre-filled."""
    import urllib.parse
    return f"{WA_LINK_BASE}?text={urllib.parse.quote(text)}"


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🛋️ Katalog", callback_data="menu_katalog"),
             InlineKeyboardButton("💰 Cek Harga", callback_data="menu_harga")],
            [InlineKeyboardButton("🛒 Order", callback_data="menu_order"),
             InlineKeyboardButton("📦 Status Order", callback_data="menu_status")],
            [InlineKeyboardButton("🔥 Promo", callback_data="menu_promo"),
             InlineKeyboardButton("💬 WhatsApp", callback_data="menu_wa")],
        ]
    )


def product_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    for key, prod in PRODUCTS.items():
        buttons.append(
            [InlineKeyboardButton(f"{prod['nama']} — {prod['label']}", callback_data=f"prod_{key}")]
        )
    buttons.append([InlineKeyboardButton("⬅️ Kembali ke Menu", callback_data="back_menu")])
    return InlineKeyboardMarkup(buttons)


def order_product_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    for key, prod in PRODUCTS.items():
        buttons.append(
            [InlineKeyboardButton(prod["nama"], callback_data=f"orderprod_{key}")]
        )
    buttons.append([InlineKeyboardButton("❌ Batal", callback_data="cancel")])
    return InlineKeyboardMarkup(buttons)


# ─── Error handler decorator ───────────────────────────────────────────────────

def catch_errors(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        try:
            return await func(update, context, *args, **kwargs)
        except Exception as exc:
            logger.exception("Error di %s", func.__name__)
            text = "⚠️ Maaf, terjadi kesalahan. Silakan coba lagi atau hubungi kami via WhatsApp."
            try:
                if update.callback_query:
                    await update.callback_query.answer()
                    await update.callback_query.edit_message_text(
                        text, reply_markup=main_menu_keyboard()
                    )
                elif update.effective_message:
                    await update.effective_message.reply_text(
                        text, reply_markup=main_menu_keyboard()
                    )
            except Exception:
                pass
    return wrapper

# ─── /start ────────────────────────────────────────────────────────────────────

@catch_errors
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Welcome message + main menu."""
    user = update.effective_user
    text = (
        f"Selamat datang di *{BRAND}* {BRAND_HANDLE}! 🏠✨\n\n"
        "Kami menyediakan furnitur premium dengan desain modern & harga terjangkau.\n\n"
        "Silakan pilih menu di bawah atau ketik command langsung:\n"
        "/katalog — Lihat katalog produk\n"
        "/harga — Cek harga produk\n"
        "/order — Buat pesanan\n"
        "/status — Cek status order\n"
        "/promo — Promo saat ini"
    )
    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(),
    )

# ─── /katalog ──────────────────────────────────────────────────────────────────

@catch_errors
async def katalog_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _show_katalog(update.effective_message)

async def _show_katalog(msg):
    text = f"🛋️ *Katalog {BRAND}*\n\nPilih produk untuk detail:"
    await msg.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=product_keyboard(),
    )

# ─── /harga (ConversationHandler) ─────────────────────────────────────────────

@catch_errors
async def harga_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point /harga — tampilkan daftar produk."""
    await update.message.reply_text(
        "💰 *Cek Harga Produk*\n\nPilih produk yang ingin Anda cek:",
        parse_mode="Markdown",
        reply_markup=product_keyboard(),
    )
    return HARGA_CHOOSE

@catch_errors
async def harga_product_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "back_menu":
        await query.edit_message_text(
            f"🏠 *{BRAND}* — Menu Utama",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(),
        )
        return ConversationHandler.END

    prod_key = query.data.replace("prod_", "")
    prod = PRODUCTS.get(prod_key)
    if not prod:
        await query.edit_message_text("Produk tidak ditemukan.", reply_markup=main_menu_keyboard())
        return ConversationHandler.END

    wa_msg = f"Halo {BRAND}, saya tertarik dengan {prod['nama']} ({prod['label']}). Apakah masih tersedia?"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Tanya via WhatsApp", url=wa_link(wa_msg))],
        [InlineKeyboardButton("⬅️ Kembali", callback_data="back_harga")],
    ])

    text = (
        f"💰 *{prod['nama']}*\n\n"
        f"📋 Kategori: {prod['kategori']}\n"
        f"💵 Harga: *{prod['label']}*\n"
        f"📝 {prod['desc']}"
    )
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)
    return HARGA_SHOW

@catch_errors
async def harga_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "💰 *Cek Harga Produk*\n\nPilih produk yang ingin Anda cek:",
        parse_mode="Markdown",
        reply_markup=product_keyboard(),
    )
    return HARGA_CHOOSE

@catch_errors
async def harga_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "Cek harga dibatalkan. Ketik /harga untuk mulai lagi.",
        reply_markup=main_menu_keyboard(),
    )
    return ConversationHandler.END

# ─── /order (ConversationHandler) ──────────────────────────────────────────────

@catch_errors
async def order_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "🛒 *Buat Pesanan*\n\nPilih produk yang ingin dipesan:",
        parse_mode="Markdown",
        reply_markup=order_product_keyboard(),
    )
    return ORDER_PRODUCT

@catch_errors
async def order_product_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "cancel":
        await query.edit_message_text(
            "Order dibatalkan.", reply_markup=main_menu_keyboard()
        )
        return ConversationHandler.END

    prod_key = query.data.replace("orderprod_", "")
    prod = PRODUCTS.get(prod_key)
    if not prod:
        await query.edit_message_text("Produk tidak ditemukan.", reply_markup=main_menu_keyboard())
        return ConversationHandler.END

    context.user_data["order_product_key"] = prod_key
    context.user_data["order_product"] = prod

    await query.edit_message_text(
        f"🛒 *{prod['nama']}* dipilih!\n\n"
        "Berapa jumlah yang ingin dipesan? (contoh: 1, 2, 3)",
        parse_mode="Markdown",
    )
    return ORDER_QTY

@catch_errors
async def order_qty_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    try:
        qty = int(text)
        if qty < 1 or qty > 100:
            raise ValueError
    except ValueError:
        await update.message.reply_text("⚠️ Masukkan angka 1–100. Berapa jumlah pesanan?")
        return ORDER_QTY

    context.user_data["order_qty"] = qty
    await update.message.reply_text("👤 Nama lengkap pemesan:")
    return ORDER_NAME

@catch_errors
async def order_name_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = update.message.text.strip()
    if not name:
        await update.message.reply_text("⚠️ Nama tidak boleh kosong. Masukkan nama lengkap:")
        return ORDER_NAME

    context.user_data["order_name"] = name
    await update.message.reply_text("📍 Alamat pengiriman lengkap:")
    return ORDER_ADDRESS

@catch_errors
async def order_address_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    address = update.message.text.strip()
    if not address:
        await update.message.reply_text("⚠️ Alamat tidak boleh kosong. Masukkan alamat lengkap:")
        return ORDER_ADDRESS

    context.user_data["order_address"] = address

    # Simpan order
    global _next_order_id
    order_id = f"HL-{datetime.now().strftime('%y%m')}-{_next_order_id:04d}"
    _next_order_id += 1

    prod = context.user_data["order_product"]
    qty = context.user_data["order_qty"]
    name = context.user_data["order_name"]
    total = prod["harga"] * qty

    ORDERS[order_id] = {
        "id": order_id,
        "produk": prod["nama"],
        "harga_satuan": prod["label"],
        "qty": qty,
        "total": f"Rp {total:_}".replace("_", "."),
        "nama": name,
        "alamat": address,
        "status": "Menunggu Konfirmasi",
        "waktu": datetime.now().strftime("%d %b %Y, %H:%M"),
    }

    order = ORDERS[order_id]
    wa_msg = (
        f"Halo {BRAND}, saya ingin konfirmasi order:\n"
        f"Order ID: {order_id}\n"
        f"Produk: {prod['nama']} x{qty}\n"
        f"Nama: {name}\n"
        f"Alamat: {address}"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Konfirmasi via WhatsApp", url=wa_link(wa_msg))],
        [InlineKeyboardButton("🏠 Menu Utama", callback_data="back_menu")],
    ])

    text = (
        f"✅ *Pesanan Berhasil Dibuat!*\n\n"
        f"🆔 Order ID: `{order_id}`\n"
        f"🛋️ Produk: {order['produk']}\n"
        f"💰 Harga satuan: {order['harga_satuan']}\n"
        f"📦 Jumlah: {qty}\n"
        f"💵 Total: *{order['total']}*\n"
        f"👤 Nama: {order['nama']}\n"
        f"📍 Alamat: {order['alamat']}\n"
        f"📌 Status: {order['status']}\n"
        f"🕐 Waktu: {order['waktu']}\n\n"
        f"Silakan konfirmasi pesanan via WhatsApp agar kami segera memproses."
    )

    await update.message.reply_text(
        text, parse_mode="Markdown", reply_markup=keyboard
    )
    context.user_data.pop("order_product_key", None)
    context.user_data.pop("order_product", None)
    context.user_data.pop("order_qty", None)
    context.user_data.pop("order_name", None)
    context.user_data.pop("order_address", None)
    return ConversationHandler.END

@catch_errors
async def order_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "🛒 Order dibatalkan.", reply_markup=main_menu_keyboard()
    )
    return ConversationHandler.END

# ─── /status ───────────────────────────────────────────────────────────────────

@catch_errors
async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "📦 *Cek Status Order*\n\nMasukkan Order ID Anda (contoh: HL-2506-0001):",
        parse_mode="Markdown",
    )
    return STATUS_INPUT

@catch_errors
async def status_id_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    order_id = update.message.text.strip().upper()
    order = ORDERS.get(order_id)

    if not order:
        await update.message.reply_text(
            f"❌ Order ID `{order_id}` tidak ditemukan.\n\n"
            "Pastikan ID benar atau ketik /status untuk coba lagi.",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(),
        )
        return ConversationHandler.END

    wa_msg = f"Halo {BRAND}, saya ingin cek status order {order_id}."
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Tanya via WhatsApp", url=wa_link(wa_msg))],
        [InlineKeyboardButton("🏠 Menu Utama", callback_data="back_menu")],
    ])

    text = (
        f"📦 *Detail Order*\n\n"
        f"🆔 Order ID: `{order['id']}`\n"
        f"🛋️ Produk: {order['produk']}\n"
        f"💰 Harga satuan: {order['harga_satuan']}\n"
        f"📦 Jumlah: {order['qty']}\n"
        f"💵 Total: *{order['total']}*\n"
        f"👤 Nama: {order['nama']}\n"
        f"📍 Alamat: {order['alamat']}\n"
        f"📌 Status: *{order['status']}*\n"
        f"🕐 Waktu: {order['waktu']}"
    )
    await update.message.reply_text(
        text, parse_mode="Markdown", reply_markup=keyboard
    )
    return ConversationHandler.END

@catch_errors
async def status_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Cek status dibatalkan.", reply_markup=main_menu_keyboard()
    )
    return ConversationHandler.END

# ─── /promo ────────────────────────────────────────────────────────────────────

@catch_errors
async def promo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lines = [f"🔥 *Promo {BRAND} Saat Ini*\n"]
    for p in PROMOS:
        lines.append(f"{p['judul']}")
        lines.append(f"{p['detail']}")
        lines.append(f"🎫 Kode: *{p['kodem']}*\n")

    wa_msg = f"Halo {BRAND}, saya ingin tahu lebih lanjut tentang promo yang berlaku."
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Tanya Promo via WhatsApp", url=wa_link(wa_msg))],
        [InlineKeyboardButton("🏠 Menu Utama", callback_data="back_menu")],
    ])

    await update.message.reply_text(
        "\n".join(lines), parse_mode="Markdown", reply_markup=keyboard
    )

# ─── Callback handler untuk inline buttons menu ───────────────────────────────

@catch_errors
async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle semua callback dari main menu inline buttons."""
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "back_menu":
        await query.edit_message_text(
            f"🏠 *{BRAND}* — Menu Utama",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(),
        )

    elif data == "menu_katalog":
        await query.edit_message_text(
            f"🛋️ *Katalog {BRAND}*\n\nPilih produk untuk detail:",
            parse_mode="Markdown",
            reply_markup=product_keyboard(),
        )

    elif data == "menu_harga":
        await query.edit_message_text(
            "💰 *Cek Harga Produk*\n\nPilih produk yang ingin Anda cek:",
            parse_mode="Markdown",
            reply_markup=product_keyboard(),
        )

    elif data == "menu_order":
        await query.edit_message_text(
            "🛒 *Buat Pesanan*\n\nPilih produk yang ingin dipesan:",
            parse_mode="Markdown",
            reply_markup=order_product_keyboard(),
        )

    elif data == "menu_status":
        await query.edit_message_text(
            "📦 *Cek Status Order*\n\nKetik /status lalu masukkan Order ID Anda.",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(),
        )

    elif data == "menu_promo":
        lines = [f"🔥 *Promo {BRAND} Saat Ini*\n"]
        for p in PROMOS:
            lines.append(f"{p['judul']}")
            lines.append(f"{p['detail']}")
            lines.append(f"🎫 Kode: *{p['kodem']}*\n")
        await query.edit_message_text(
            "\n".join(lines), parse_mode="Markdown", reply_markup=main_menu_keyboard()
        )

    elif data == "menu_wa":
        wa_msg = f"Halo {BRAND}, saya ingin bertanya tentang produk furnitur Anda."
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💬 Chat WhatsApp", url=wa_link(wa_msg))],
            [InlineKeyboardButton("⬅️ Kembali", callback_data="back_menu")],
        ])
        await query.edit_message_text(
            f"💬 *Hubungi {BRAND} via WhatsApp*\n\n"
            "Klik tombol di bawah untuk langsung chat dengan tim kami.",
            parse_mode="Markdown",
            reply_markup=keyboard,
        )

    elif data.startswith("prod_"):
        # Detail produk dari katalog
        prod_key = data.replace("prod_", "")
        prod = PRODUCTS.get(prod_key)
        if not prod:
            await query.edit_message_text("Produk tidak ditemukan.", reply_markup=main_menu_keyboard())
            return
        wa_msg = f"Halo {BRAND}, saya tertarik dengan {prod['nama']} ({prod['label']}). Apakah masih tersedia?"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💬 Tanya via WhatsApp", url=wa_link(wa_msg))],
            [InlineKeyboardButton("⬅️ Kembali ke Katalog", callback_data="menu_katalog")],
        ])
        text = (
            f"🛋️ *{prod['nama']}*\n\n"
            f"📋 Kategori: {prod['kategori']}\n"
            f"💵 Harga: *{prod['label']}*\n"
            f"📝 {prod['desc']}"
        )
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)

    elif data.startswith("orderprod_"):
        # Mulai order flow dari inline button
        prod_key = data.replace("orderprod_", "")
        prod = PRODUCTS.get(prod_key)
        if not prod:
            await query.edit_message_text("Produk tidak ditemukan.", reply_markup=main_menu_keyboard())
            return
        context.user_data["order_product_key"] = prod_key
        context.user_data["order_product"] = prod
        await query.edit_message_text(
            f"🛒 *{prod['nama']}* dipilih!\n\n"
            "Berapa jumlah yang ingin dipesan? (contoh: 1, 2, 3)",
            parse_mode="Markdown",
        )
        return  # Let conversation handler take over if active

    elif data == "cancel":
        await query.edit_message_text(
            "Dibatalkan.", reply_markup=main_menu_keyboard()
        )


# ─── Product detail callback (shared by katalog & harga) ──────────────────────

@catch_errors
async def product_detail_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle prod_* callbacks not caught by conversation handler."""
    query = update.callback_query
    await query.answer()

    data = query.data

    if data.startswith("prod_"):
        prod_key = data.replace("prod_", "")
        prod = PRODUCTS.get(prod_key)
        if not prod:
            await query.edit_message_text("Produk tidak ditemukan.", reply_markup=main_menu_keyboard())
            return
        wa_msg = f"Halo {BRAND}, saya tertarik dengan {prod['nama']} ({prod['label']}). Apakah masih tersedia?"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💬 Tanya via WhatsApp", url=wa_link(wa_msg))],
            [InlineKeyboardButton("⬅️ Kembali ke Katalog", callback_data="menu_katalog")],
        ])
        text = (
            f"🛋️ *{prod['nama']}*\n\n"
            f"📋 Kategori: {prod['kategori']}\n"
            f"💵 Harga: *{prod['label']}*\n"
            f"📝 {prod['desc']}"
        )
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)

# ─── Fallback / unknown command ────────────────────────────────────────────────

@catch_errors
async def fallback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🤔 Maaf, saya tidak mengerti. Gunakan menu di bawah atau ketik /start.",
        reply_markup=main_menu_keyboard(),
    )

# ─── Global error handler ──────────────────────────────────────────────────────

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Exception saat handling update:", exc_info=context.error)

# ─── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()

    # Harga conversation
    harga_conv = ConversationHandler(
        entry_points=[CommandHandler("harga", harga_cmd)],
        states={
            HARGA_CHOOSE: [
                CallbackQueryHandler(harga_product_chosen, pattern=r"^prod_"),
                CallbackQueryHandler(harga_cancel, pattern=r"^cancel$"),
            ],
            HARGA_SHOW: [
                CallbackQueryHandler(harga_back, pattern=r"^back_harga$"),
                CallbackQueryHandler(harga_product_chosen, pattern=r"^prod_"),
            ],
        },
        fallbacks=[CommandHandler("cancel", harga_cancel)],
        per_user=True,
    )

    # Order conversation
    order_conv = ConversationHandler(
        entry_points=[CommandHandler("order", order_cmd)],
        states={
            ORDER_PRODUCT: [
                CallbackQueryHandler(order_product_chosen, pattern=r"^orderprod_"),
            ],
            ORDER_QTY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, order_qty_received),
            ],
            ORDER_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, order_name_received),
            ],
            ORDER_ADDRESS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, order_address_received),
            ],
        },
        fallbacks=[CommandHandler("cancel", order_cancel)],
        per_user=True,
    )

    # Status conversation
    status_conv = ConversationHandler(
        entry_points=[CommandHandler("status", status_cmd)],
        states={
            STATUS_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, status_id_received),
            ],
        },
        fallbacks=[CommandHandler("cancel", status_cancel)],
        per_user=True,
    )

    # Register handlers
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("katalog", katalog_cmd))
    app.add_handler(CommandHandler("promo", promo_cmd))
    app.add_handler(harga_conv)
    app.add_handler(order_conv)
    app.add_handler(status_conv)

    # Generic menu callback (harus setelah conversation handlers)
    app.add_handler(CallbackQueryHandler(menu_callback))

    # Fallback
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, fallback))

    # Error handler
    app.add_error_handler(error_handler)

    logger.info("🚀 %s bot berjalan…", BRAND)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
