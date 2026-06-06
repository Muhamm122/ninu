"""
Haus Living Discord Bot
=======================
Bot Discord untuk brand furniture Haus Living (@haus_living1).
Menampilkan katalog, cek harga, info order, promo, dan bantuan.

Cara menjalankan:
    export DISCORD_TOKEN="token_bot_anda"
    python discord-bot.py
"""

import os
import sys
import logging
import discord
from discord.ext import commands

# ─── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("haus-living")

# ─── Brand Constants ──────────────────────────────────────────────────────────
BRAND_NAME = "Haus Living"
BRAND_TAG = "@haus_living1"
COLOR_BG   = 0x1A1A1A   # dark background
COLOR_GOLD = 0xD4A574   # gold accent
FOOTER_TEXT = f"{BRAND_NAME} — {BRAND_TAG}"
THUMBNAIL   = ""  # isi URL logo brand jika ada

# ─── Product Data ─────────────────────────────────────────────────────────────
PRODUCTS = {
    "sofa l-shape":      {"nama": "Sofa L-Shape",          "harga": "Rp 12.500.000", "kategori": "Sofa",      "deskripsi": "Sofa sudut L-Shape, desain minimalis & nyaman untuk ruang tamlu keluarga."},
    "sofa 3-seater":     {"nama": "Sofa 3-Seater",         "harga": "Rp 8.900.000",  "kategori": "Sofa",      "deskripsi": "Sofa 3 dudukan, bahan premium & sandaran ergonomis."},
    "sofa bed":          {"nama": "Sofa Bed",              "harga": "Rp 10.500.000", "kategori": "Sofa",      "deskripsi": "Sofa lipat yang bisa jadi tempat tidur, multifungsi."},
    "meja makan":        {"nama": "Meja Makan 6 Seater",   "harga": "Rp 8.900.000",  "kategori": "Meja",      "deskripsi": "Meja makan kayu solid untuk 6 orang, finishing natural."},
    "rak tv":            {"nama": "Rak TV Floating",        "harga": "Rp 4.250.000",  "kategori": "Rak/Storage","deskripsi": "Rak TV dinding (floating), desain modern & hemat ruang."},
    "bed frame":         {"nama": "Bed Frame + Storage",    "harga": "Rp 6.800.000",  "kategori": "Kamar Tidur","deskripsi": "Bed frame dengan laci storage di bawah, solusi hempat ruang."},
    "wardrobe":          {"nama": "Wardrobe 3 Pintu",       "harga": "Rp 7.500.000",  "kategori": "Kamar Tidur","deskripsi": "Lemari pakaian 3 pintu, interior luas dengan cermin."},
    "bookshelf":         {"nama": "Bookshelf 5 Tier",       "harga": "Rp 3.200.000",  "kategori": "Rak/Storage","deskripsi": "Rak buku 5 tingkat, kayu solid kokoh & estetik."},
    "console table":     {"nama": "Console Table",          "harga": "Rp 2.800.000",  "kategori": "Meja",      "deskripsi": "Console table minimalis, cocok untuk entryway atau dekorasi."},
    "meja kerja":        {"nama": "Meja Kerja",             "harga": "Rp 3.500.000",  "kategori": "Meja",      "deskripsi": "Meja kerja minimalis, lengkap dengan cable management."},
}

# Alias pencarian (mendukung variasi input user)
ALIASES = {
    "l-shape": "sofa l-shape", "sofa l": "sofa l-shape", "l shape": "sofa l-shape",
    "3-seater": "sofa 3-seater", "3 seater": "sofa 3-seater", "sofa3": "sofa 3-seater",
    "sofa bed": "sofa bed", "sofabed": "sofa bed",
    "meja makan": "meja makan", "makan": "meja makan", "dining": "meja makan",
    "rak tv": "rak tv", "tv": "rak tv", "floating": "rak tv", "raktv": "rak tv",
    "bed": "bed frame", "bedframe": "bed frame", "frame": "bed frame", "kasur": "bed frame",
    "wardrobe": "wardrobe", "lemari": "wardrobe", "3 pintu": "wardrobe", "3pintu": "wardrobe",
    "bookshelf": "bookshelf", "buku": "bookshelf", "rak buku": "bookshelf", "5 tier": "bookshelf",
    "console": "console table", "consoletable": "console table", "console table": "console table",
    "meja kerja": "meja kerja", "kerja": "meja kerja", "desk": "meja kerja",
}

# ─── Promo & Order Info ───────────────────────────────────────────────────────
PROMOS = [
    {"judul": "🎉 Grand Opening Disc 15%", "detail": "Diskon 15% untuk semua produk. Berlaku sampai akhir bulan ini!"},
    {"judul": "🚚 Gratis Ongkir", "detail": "Free delivery untuk pembelian di atas Rp 5.000.000 (Jabodetabek)."},
    {"judul": "💳 Cicilan 0%", "detail": "Cicilan 0% hingga 12 bulan dengan kartu kredit pilihan."},
]

ORDER_INFO = (
    "📝 **Cara Order Haus Living:**\n"
    "1️⃣  Pilih produk dari katalog (`!katalog`)\n"
    "2️⃣  Cek harga detail (`!harga <produk>`)\n"
    "3️⃣  DM admin atau hubungi via Instagram @haus_living1\n"
    "4️⃣  Bayar — konfirmasi — pengiriman! 🚚\n\n"
    "📍 **Area Pengiriman:** Jabodetabek (luar kota bisa, biaya ongkir terpisah)\n"
    "⏰ **Estimasi Pengiriman:** 7–14 hari kerja\n"
    "💳 **Pembayaran:** Transfer bank, kartu kredit (cicilan 0%), COD (Jabodetabek)"
)

# ─── Bot Setup ────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
bot.remove_command("help")  # kita buat sendiri


# ─── Helper ───────────────────────────────────────────────────────────────────
def make_embed(title: str, description: str = "", color=COLOR_GOLD) -> discord.Embed:
    """Buat embed konsisten dengan branding Haus Living."""
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_footer(text=FOOTER_TEXT)
    if THUMBNAIL:
        embed.set_thumbnail(url=THUMBNAIL)
    return embed


def resolve_product(query: str):
    """Cari produk berdasarkan query, return key atau None."""
    q = query.strip().lower()
    # Exact match di PRODUCTS
    if q in PRODUCTS:
        return q
    # Cek alias
    if q in ALIASES:
        return ALIASES[q]
    # Fuzzy: cocokkan sebagian nama
    for key in PRODUCTS:
        if q in key or key in q:
            return key
    for alias_key, prod_key in ALIASES.items():
        if q in alias_key:
            return prod_key
    return None


# ─── Events ───────────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    log.info("Bot online sebagai %s (ID: %s)", bot.user, bot.user.id)
    # Set presence
    try:
        await bot.change_presence(
            activity=discord.Activity(type=discord.ActivityType.watching, name="Rumah Impian Kamu 🏠")
        )
    except Exception:
        pass


@bot.event
async def on_command_error(ctx, error):
    """Handler error global."""
    if isinstance(error, commands.CommandNotFound):
        embed = make_embed(
            "❌ Perintah Tidak Dikenali",
            f"Perintah `{ctx.invoked_with}` tidak ditemukan.\nKetik `!help` untuk daftar perintah.",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)
    elif isinstance(error, commands.MissingRequiredArgument):
        embed = make_embed(
            "⚠️ Argumen Kurang",
            f"Perintah `{ctx.invoked_with}` membutuhkan argumen.\nKetik `!help` untuk panduan.",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)
    else:
        log.error("Error pada command %s: %s", ctx.invoked_with, error)
        embed = make_embed(
            "⚠️ Terjadi Kesalahan",
            "Terjadi error internal. Tim kami sudah diberitahu. Coba lagi nanti.",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)


# ─── Commands ─────────────────────────────────────────────────────────────────
@bot.command(name="katalog", aliases=["catalog", "katalok"])
async def katalog(ctx):
    """Menampilkan katalog lengkap produk Haus Living."""
    embed = make_embed(
        f"🛋️ Katalog {BRAND_NAME}",
        "Berikut koleksi furniture kami — ketik `!harga <nama produk>` untuk detail harga.",
    )

    # Kelompokkan per kategori
    kategori = {}
    for key, p in PRODUCTS.items():
        kat = p["kategori"]
        if kat not in kategori:
            kategori[kat] = []
        kategori[kat].append(p)

    for kat, items in kategori.items():
        lines = []
        for p in items:
            lines.append(f"**{p['nama']}** — {p['harga']}")
        embed.add_field(name=f"📁 {kat}", value="\n".join(lines), inline=False)

    await ctx.send(embed=embed)


@bot.command(name="harga", aliases=["price", "hrg"])
async def harga(ctx, *, produk: str):
    """Cek harga produk. Contoh: !harga sofa l-shape"""
    key = resolve_product(produk)
    if key is None:
        # Sarankan produk terdekat
        suggestions = ", ".join(f"`{p['nama']}`" for p in list(PRODUCTS.values())[:5])
        embed = make_embed(
            "❌ Produk Tidak Ditemukan",
            f'Tidak ditemukan produk untuk "{produk}".\n'
            f"Coba: {suggestions}, dll.\n"
            "Ketik `!katalog` untuk daftar lengkap.",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)
        return

    p = PRODUCTS[key]
    embed = make_embed(
        f"💰 {p['nama']}",
        p["deskripsi"],
    )
    embed.add_field(name="💵 Harga", value=p["harga"], inline=True)
    embed.add_field(name="📂 Kategori", value=p["kategori"], inline=True)
    embed.add_field(
        name="🛒 Cara Order",
        value="DM admin atau hubungi IG @haus_living1\nKetik `!order` untuk info lengkap.",
        inline=False,
    )
    embed.set_footer(text=f"{FOOTER_TEXT} | !order untuk info pemesanan")
    await ctx.send(embed=embed)


@bot.command(name="order", aliases=["pesan", "ord"])
async def order(ctx):
    """Menampilkan informasi cara pemesanan."""
    embed = make_embed(
        "🛒 Cara Pemesanan — Haus Living",
        ORDER_INFO,
    )
    embed.add_field(
        name="☎️ Hubungi Kami",
        value="📱 Instagram: @haus_living1\n💬 DM langsung ke admin Discord ini",
        inline=False,
    )
    await ctx.send(embed=embed)


@bot.command(name="promo", aliases=["diskon", "promosi"])
async def promo(ctx):
    """Menampilkan promo yang sedang berlaku."""
    embed = make_embed(
        "🎉 Promo Berlaku — Haus Living",
        "Manfaatkan promo berikut sebelum berakhir!",
    )
    for pr in PROMOS:
        embed.add_field(name=pr["judul"], value=pr["detail"], inline=False)
    embed.set_footer(text=f"{FOOTER_TEXT} | Syarat & ketentuan berlaku")
    await ctx.send(embed=embed)


@bot.command(name="help", aliases=["bantuan", "?"])
async def help_cmd(ctx):
    """Menampilkan daftar perintah bot."""
    embed = make_embed(
        f"🏠 {BRAND_NAME} — Panduan Bot",
        "Bot ini membantu Anda menjelajahi koleksi furniture Haus Living.\n"
        "Semua perintah diawali dengan `!`",
    )
    commands_list = [
        ("`!katalog`", "Menampilkan katalog lengkap produk"),
        ("`!harga <produk>`", "Cek harga & detail produk\nContoh: `!harga sofa l-shape`"),
        ("`!order`", "Info cara pemesanan & pengiriman"),
        ("`!promo`", "Lihat promo & diskon berlaku"),
        ("`!help`", "Tampilkan panduan ini"),
    ]
    for cmd, desc in commands_list:
        embed.add_field(name=cmd, value=desc, inline=False)

    embed.add_field(
        name="💡 Tips",
        value="Pencarian produk cukup ketik sebagian nama, misal `!harga bed` atau `!harga kerja`.",
        inline=False,
    )
    await ctx.send(embed=embed)


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        log.error("DISCORD_TOKEN tidak ditemukan di environment variable.")
        log.error("Cara set: export DISCORD_TOKEN=\"token_bot_anda\"")
        sys.exit(1)

    log.info("Memulai %s Discord Bot...", BRAND_NAME)
    try:
        bot.run(token)
    except discord.LoginFailure:
        log.error("Token Discord tidak valid. Periksa kembali DISCORD_TOKEN Anda.")
        sys.exit(1)
    except Exception as e:
        log.error("Gagal menjalankan bot: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
