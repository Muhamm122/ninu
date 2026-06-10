#!/usr/bin/env python3
"""
UnionPay CC Generator - Copy-paste friendly output with fake address
Usage: python3 unionpay_gen.py [count]
"""

import random
import sys
from datetime import datetime, timedelta

UNIONPAY_BINS = [
    "622126", "622127", "622128", "622129", "622130",
    "622131", "622132", "622133", "622134", "622135",
    "622136", "622137", "622138", "622139", "622140",
    "624", "625", "626",
    "6282", "6283", "6284", "6285", "6286", "6287", "6288",
    "622836", "622837", "625919", "625917", "625918",
    "628218", "628219", "628220", "622200", "622202",
    "622203", "622208", "622210", "622211", "622212",
    "622213", "622214", "622215", "622216", "622220",
    "622223", "622224", "622225", "622229", "622230",
]

FIRST_NAMES = [
    "WEI", "LI", "ZHANG", "WANG", "CHEN", "LIU", "YANG", "HUANG",
    "ZHAO", "ZHOU", "WU", "XU", "SUN", "MA", "ZHU", "HU",
    "ADAM", "ALEX", "SARAH", "JAMES", "MARY", "JOHN", "LINDA",
    "ROBERT", "MICHAEL", "DAVID", "RICHARD", "JOSEPH", "THOMAS",
    "AKIRA", "YUKI", "HANA", "KENJI", "SORA", "REI", "MIYU",
    "MINHO", "SEOYEON", "JIWON", "TAEHYUNG", "JIMIN", "JENNIE",
    "AHMED", "FATIMA", "MOHAMMED", "ALI", "OMAR", "AISHA",
    "CARLOS", "MARIA", "JOSE", "ANA", "LUIS", "CARMEN",
]

LAST_NAMES = [
    "ZHANG", "WANG", "LI", "CHEN", "LIU", "YANG", "HUANG",
    "ZHAO", "ZHOU", "WU", "XU", "SUN", "MA", "ZHU", "LIN",
    "SMITH", "JOHNSON", "WILLIAMS", "BROWN", "JONES", "GARCIA",
    "MILLER", "DAVIS", "RODRIGUEZ", "MARTINEZ", "HERNANDEZ",
    "TANAKA", "SATO", "SUZUKI", "TAKAHASHI", "WATANABE",
    "KIM", "LEE", "PARK", "CHOI", "JUNG", "KANG", "CHO",
    "NGUYEN", "TRAN", "LE", "PHAM", "HOANG", "VU",
    "ALI", "HUSSAIN", "KHAN", "AHMED", "SIDDIQUI",
    "SANTOS", "REYES", "CRUZ", "GONZALEZ", "RAMIREZ",
]

# Fake address components
STREET_NAMES = [
    "Jalan Sudirman", "Jalan Thamrin", "Jalan Gatot Subroto",
    "Jalan MH Thamrin", "Jalan Rasuna Said", "Jalan HR Rasuna Said",
    "Jalan Casablanca", "Jalan Prof Dr Satrio", "Jalan Kuningan",
    "Jalan Asia Afrika", "Jalan Diponegoro", "Jalan Imam Bonjol",
    "Jalan Teuku Umar", "Jalan Cikini Raya", "Jalan Sabang",
    "Jalan Hayam Wuruk", "Jalan Gajah Mada", "Jalan Mangga Besar",
    "Jalan Kelapa Gading", "Jalan Sunter", "Jalan Pluit",
    "Jalan Pantai Indah Kapuk", "Jalan Kedoya", "Jalan Meruya",
    "Jalan Ciledug", "Jalan Cempaka Putih", "Jalan Rawamangun",
    "Jalan Pulogadung", "Jalan Cakung", "Jalan Bekasi Raya",
    "Jalan Bogor Raya", "Jalan Depok", "Jalan Cibubur",
    "Jalan Cileungsi", "Jalan Sentul", "Jalan Cimahi",
    "Jalan Riau", "Jalan Medan Merdeka", "Jalan Veteran",
    "Jalan Ahmad Yani", "Jalan DI Panjaitan", "Jalan MT Haryono",
    "Jalan Jenderal Sudirman", "Jalan Letjen S Parman",
    "Jalan Tomang Raya", "Jalan Grogol", "Jalan Daan Mogot",
    "Jalan Kalideres", "Jalan Kembangan", "Jalan Kebon Jeruk",
    "Jalan Panjang", "Jalan Kedoya Baru", "Jalan Pesanggrahan",
    "Jalan Ciputat", "Jalan Fatmawati", "Jalan TB Simatupang",
    "Jalan Cilandak", "Jalan Kemang", "Jalan Bangka",
    "Jalan Kemang Raya", "Jalan Antasari", "Jalan Ampera",
    "Jalan Cipete", "Jalan Senopati", "Jalan Senayan",
    "Jalan Wijaya", "Jalan Wolter Monginsidi", "Jalan Melawai",
    "Jalan Panglima Polim", "Jalan Sultan Hasanuddin",
    "Jalan Pondok Indah", "Jalan Metro Pondok Indah",
    "Jalan Cipulir", "Jalan Kebayoran Lama", "Jalan Ciledug Raya",
    "Jalan Kebon Sirih", "Jalan KH Wahid Hasyim", "Jalan Sabang",
    "Jalan Jaksa", "Jalan Kebon Melati", "Jalan Angkasa",
    "Jalan Gunung Sahari", "Jalan Pasar Baru", "Jalan Pintu Besar",
    "Jalan Pinangsia", "Jalan Mangga Dua", "Jalan Gunung Sahari Raya",
    "Jalan Ancol", "Jalan Lodan", "Jalan RE Martadinata",
    "Jalan Taman Sari", "Jalan Mangga Besar Raya", "Jalan Taman Sari Raya",
    "Jalan Kartini", "Jalan Kramat", "Jalan Salemba",
    "Jalan Matraman", "Jalan Paseban", "Jalan Galunggung",
    "Jalan Cempaka Baru", "Jalan Percetakan Negara",
    "Jalan Rawasari", "Jalan Cempaka Putih Raya",
    "Jalan Sunter Jaya", "Jalan Sunter Agung", "Jalan Sunter Mas",
    "Jalan Pluit Selatan", "Jalan Pluit Utara", "Jalan Pluit Karang",
    "Jalan Muara Karang", "Jalan Bandengan", "Jalan Pekojan",
    "Jalan Jembatan Lima", "Jalan Pekojan Raya", "Jalan Tambora",
    "Jalan Duri Utara", "Jalan Duri Selatan", "Jalan Kali Besar",
    "Jalan Tiang Bendera", "Jalan Roa Malaka", "Jalan Kunir",
    "Jalan Pinangsia Timur", "Jalan Pinangsia Barat",
    "Jalan Mangga Dua Raya", "Jalan Pangeran Jayakarta",
    "Jalan Jaya", "Jalan Hayam Wuruk Raya", "Jalan Sukarasa",
    "Jalan Taman Sari Barat", "Jalan Taman Sari Timur",
    "Jalan Mangga Besar Utara", "Jalan Mangga Besar Selatan",
    "Jalan Kartini Raya", "Jalan Kramat Raya", "Jalan Salemba Raya",
    "Jalan Matraman Raya", "Jalan DI Panjaitan Raya",
    "Jalan MT Haryono Raya", "Jalan Cawang", "Jatinegara",
    "Jalan Raya Bogor", "Jalan Raya Bekasi", "Jalan Raya Cakung",
    "Jalan Raya Pulogadung", "Jalan Raya Jatinegara",
    "Jalan Raya Cilincing", "Jalan Raya Koja", "Jalan Raya Tanjung Priok",
    "Jalan Raya Sunter", "Jalan Raya Kelapa Gading",
    "Jalan Raya Boulevard", "Jalan Raya Pantai Indah",
    "Jalan Raya Kedoya", "Jalan Raya Meruya", "Jalan Raya Ciledug",
    "Jalan Raya Ciputat", "Jalan Raya Fatmawati",
    "Jalan Raya Cilandak", "Jalan Raya Kemang",
    "Jalan Raya Kebayoran", "Jalan Raya Pondok Indah",
    "Jalan Raya Lebak Bulus", "Jalan Raya Ciganjur",
    "Jalan Raya Jagakarsa", "Jalan Raya Lenteng Agung",
    "Jalan Raya Pasar Minggu", "Jalan Raya Ragunan",
    "Jalan Raya Pejaten", "Jalan Raya Warung Buncit",
    "Jalan Raya Mampang", "Jalan Raya Kuningan",
    "Jalan Raya Casablanca", "Jalan Raya Tebet",
    "Jalan Raya Pancoran", "Jalan Raya Kalibata",
    "Jalan Raya Cawang", "Jatinegara Timur", "Jatinegara Barat",
    "Jatinegara Kaum", "Jatinegara Cakung", "Jatinegara Jaya",
    "Jatinegara Indah", "Jatinegara Baru", "Jatinegara Lama",
    "Jatinegara Asli", "Jatinegara Baru", "Jatinegara Indah",
]

CITIES = [
    ("Jakarta Pusat", "10540"),
    ("Jakarta Selatan", "12190"),
    ("Jakarta Barat", "11480"),
    ("Jakarta Timur", "13330"),
    ("Jakarta Utara", "14240"),
    ("Bogor", "16110"),
    ("Depok", "16416"),
    ("Tangerang", "15141"),
    ("Tangerang Selatan", "15339"),
    ("Bekasi", "17111"),
    ("Bandung", "40111"),
    ("Surabaya", "60119"),
    ("Medan", "20111"),
    ("Semarang", "50135"),
    ("Yogyakarta", "55281"),
    ("Malang", "65111"),
    ("Denpasar", "80237"),
    ("Makassar", "90111"),
    ("Palembang", "30111"),
    ("Balikpapan", "76111"),
    ("Manado", "95111"),
    ("Padang", "25111"),
    ("Pontianak", "78111"),
    ("Banjarmasin", "70117"),
    ("Samarinda", "75117"),
    ("Mataram", "83115"),
    ("Kupang", "85111"),
    ("Ambon", "97111"),
    ("Jayapura", "99111"),
    ("Batam", "29432"),
    ("Pekanbaru", "28111"),
    ("Jambi", "36111"),
    ("Bengkulu", "38119"),
    ("Bandar Lampung", "35111"),
    ("Serang", "42111"),
    ("Cirebon", "45111"),
    ("Tasikmalaya", "46111"),
    ("Purwokerto", "53111"),
    ("Magelang", "56111"),
    ("Solo", "57113"),
    ("Kediri", "64114"),
    ("Jember", "68113"),
    ("Banyuwangi", "68416"),
    ("Madiun", "63112"),
    ("Probolinggo", "67211"),
    ("Pasuruan", "67115"),
    ("Blitar", "66115"),
    ("Lumajang", "67316"),
    ("Bondowoso", "68211"),
    ("Situbondo", "68311"),
    ("Pamekasan", "69311"),
    ("Sampang", "69212"),
    ("Sumenep", "69412"),
    ("Bangkalan", "69112"),
    ("Sidoarjo", "61213"),
    ("Gresik", "61111"),
    ("Lamongan", "62211"),
    ("Tuban", "62311"),
    ("Bojonegoro", "62111"),
    ("Nganjuk", "64411"),
    ("Tulungagung", "66212"),
    ("Trenggalek", "66311"),
    ("Ponorogo", "63411"),
    ("Pacitan", "63511"),
    ("Magetan", "63311"),
    ("Ngawi", "63211"),
    ("Mojokerto", "61311"),
    ("Jombang", "61411"),
]

PROVINCES = [
    "DKI Jakarta", "Jawa Barat", "Jawa Tengah", "Jawa Timur",
    "Banten", "DI Yogyakarta", "Bali", "Sumatera Utara",
    "Sumatera Barat", "Sumatera Selatan", "Riau", "Kepulauan Riau",
    "Jambi", "Bengkulu", "Lampung", "Kalimantan Barat",
    "Kalimantan Timur", "Kalimantan Selatan", "Sulawesi Utara",
    "Sulawesi Selatan", "Sulawesi Tengah", "Nusa Tenggara Timur",
    "Maluku", "Papua", "Aceh", "Kalimantan Tengah",
    "Sulawesi Tenggara", "Gorontalo", "Maluku Utara", "Papua Barat",
    "Nusa Tenggara Barat", "Bangka Belitung", "Kalimantan Utara",
]


def generate_address():
    """Generate fake Indonesian address."""
    street = random.choice(STREET_NAMES)
    number = random.randint(1, 300)
    city, zipcode = random.choice(CITIES)
    province = random.choice(PROVINCES)
    address_line = f"No. {number}, RT {random.randint(1,12)}/RW {random.randint(1,10)}"
    return {
        "street": f"{street} {address_line}",
        "city": city,
        "province": province,
        "zipcode": zipcode,
    }


def luhn_check(card_number: str) -> bool:
    digits = [int(d) for d in card_number]
    for i in range(len(digits) - 2, -1, -2):
        digits[i] *= 2
        if digits[i] > 9:
            digits[i] -= 9
    return sum(digits) % 10 == 0


def generate_luhn(prefix: str, length: int = 16) -> str:
    number = prefix
    while len(number) < length - 1:
        number += str(random.randint(0, 9))
    digits = [int(d) for d in number]
    for i in range(len(digits) - 1, -1, -2):
        digits[i] *= 2
        if digits[i] > 9:
            digits[i] -= 9
    total = sum(digits)
    check_digit = (10 - (total % 10)) % 10
    return number + str(check_digit)


def generate_expiry():
    now = datetime.now()
    future = now + timedelta(days=random.randint(180, 365 * 5))
    return f"{future.month:02d}", f"{future.year % 100:02d}"


def generate_cvv():
    return str(random.randint(100, 999))


def generate_name():
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    if random.random() > 0.6:
        return f"{first} {random.choice(FIRST_NAMES)} {last}"
    return f"{first} {last}"


def generate_unionpay(count: int = 1) -> list:
    cards = []
    for _ in range(count):
        bin_num = random.choice(UNIONPAY_BINS)
        cc_number = generate_luhn(bin_num)
        exp_month, exp_year = generate_expiry()
        addr = generate_address()
        cards.append({
            "number": cc_number,
            "name": generate_name(),
            "expiry": f"{exp_month}/{exp_year}",
            "cvv": generate_cvv(),
            "address": addr,
        })
    return cards


if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    count = min(count, 100)
    cards = generate_unionpay(count)

    for i, card in enumerate(cards, 1):
        a = card['address']
        print(f"💳 Card #{i}")
        print(f"Number   : {card['number']}")
        print(f"Name     : {card['name']}")
        print(f"Expiry   : {card['expiry']}")
        print(f"CVV      : {card['cvv']}")
        print(f"Address  : {a['street']}")
        print(f"           {a['city']}, {a['province']} {a['zipcode']}")
        print()
