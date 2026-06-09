"""
CC + Fake Indonesia Data — Match Cardholder
Setiap orang punya: NIK, nama, alamat, email, phone, CC (semua konsisten)
Usage: python3 dummy_data_match.py [count]
"""

import random
import json
from datetime import datetime, timedelta

# Data pools
FIRST_NAMES_MALE = ["Adi","Budi","Cahyo","Dedi","Eko","Fajar","Guntur","Hendra","Irfan","Joko","Krisna","Lukman","Mulyadi","Nugroho","Oscar","Prasetyo","Rizki","Surya","Taufik","Umar","Wahyu","Yusuf","Zaki","Ahmad","Bayu","Dimas","Faisal","Hadi","Ihsan","Kurniawan","Muhammad","Rizky","Reza","Andre","Dian","Bambang","Agus","Rudi","Yanto","Sigit"]
FIRST_NAMES_FEMALE = ["Ani","Citra","Dewi","Eka","Fitri","Gita","Hana","Indah","Jasmine","Kartika","Lestari","Maya","Nurul","Olivia","Putri","Ratna","Sari","Tri","Umi","Vina","Wulan","Yuni","Zahra","Amelia","Bella","Clara","Diana","Eva","Fiona","Aisyah","Hannah","Kayla","Laras","Maudy","Nadia","Puti","Raisa","Syifa","Tasya","Vania","Winda","Yolanda","Zaskia","Aurora","Bilqis","Chelsea","Dinda","Elsa","Fransiska"]
LAST_NAMES = ["Pratama","Wijaya","Kusuma","Saputra","Sari","Putra","Putri","Hidayat","Nugroho","Santoso","Wibowo","Setiawan","Permata","Lestari","Rahmawati","Susanto","Halim","Siregar","Nasution","Simanjuntak","Situmorang","Manurung","Sinaga","Purba","Tarigan","Hutapea","Nainggolan","Abdullah","Ahmad","Ali","Hassan","Ibrahim","Ismail","Mohammad","Rahman","Yusof","Kurniawan","Mahendra","Pramono","Sudrajat","Tjahjono","Utomo","Widodo","Yulianto"]
STREETS = ["Merdeka","Sudirman","Thamrin","Gatot Subroto","Ahmad Yani","Diponegoro","Pangeran Antasari","Teuku Umar","Imam Bonjol","Sisingamangaraja","Ahmad Dahlan","Pattimura","Sam Ratulangi","Sukarno","Hatta","Kartini","Cut Nyak Dhien","R.A. Kartini","Dewi Sartika","Fatmawati","TB Simatupang","Casablanca","Kuningan","Senopati","Kemang","Menteng","Cikini","Panglima Polam"]
CITIES = [("Jakarta Pusat","DKI Jakarta","10000"),("Jakarta Selatan","DKI Jakarta","12000"),("Jakarta Barat","DKI Jakarta","11000"),("Jakarta Timur","DKI Jakarta","13000"),("Jakarta Utara","DKI Jakarta","14000"),("Bandung","Jawa Barat","40000"),("Surabaya","Jawa Timur","60000"),("Semarang","Jawa Tengah","50000"),("Yogyakarta","DI Yogyakarta","55000"),("Medan","Sumatera Utara","20000"),("Makassar","Sulawesi Selatan","90000")],
EMAIL_DOMAINS = ["gmail.com","yahoo.com","hotmail.com","outlook.com","protonmail.com","yandex.com","mail.com","aol.com"]
PROVIDERS = [("Telkomsel",["0811","0812","0813","0821","0822","0823","0851","0852","0853"]),(Indosat,["0814","0815","0816","0855","0856","0857","0858"]),(XL,["0817","0818","0819","0859","0877","0878"]),(Tri,["0895","0896","0897","0898","0899"]),(Smartfren,["0881","0882","0883","0884","0885"])]
CC_BINS = {"visa":{"bins":["4000","4001","4002","4003","4004","4005","4006","4007","4008","4009","4010","4011","4012","4013","4014","4015","4100","4200","4300","4400","4500"],"length":16},"mastercard":{"bins":["5100","5200","5300","5400","5500","5110","5220","5330","5440","5550","2221","2222","2223","2224","2225","2226","2227","2228","2229","2230"],"length":16},"amex":{"bins":["3400","3410","3420","3430","3440","3450","3460","3470","3480","3490","3700","3710","3720","3730","3740","3750","3760","3770","3780","3790"],"length":15}}

def luhn_check(number):
    digits=[int(d) for d in number];total=0
    for i,d in enumerate(reversed(digits)):
        if i%2==1:d*=2;d-=9 if d>9 else 0
        total+=d
    return total%10==0

def luhn_generate(partial,length):
    for _ in range(length-len(partial)-1):partial+=str(random.randint(0,9))
    digits=[int(d) for d in partial]
    for i in range(len(digits)-1,-1,-2):digits[i]*=2;digits[i]-=9 if digits[i]>9 else 0
    check=(10-(sum(digits)%10))%10;return partial+str(check)

def format_cc(n):return f"{n[:4]} {n[4:10]} {n[10:]}"if len(n)==15 else" ".join([n[i:i+4] for i in range(0,16,4)])

def generate_person_with_cc():
    gender=random.choice(["male","female"])
    first=random.choice(FIRST_NAMES_MALE if gender=="male" else FIRST_NAMES_FEMALE)
    last=random.choice(LAST_NAMES);full_name=f"{first} {last}"
    days_ago=random.randint(18*365,60*365);birth=datetime.now()-timedelta(days=days_ago)
    city,province,zp=random.choice(CITIES);street=random.choice(STREETS);num=random.randint(1,299);rt=random.randint(1,20);rw=random.randint(1,15)
    zipcode=zp+"".join([str(random.randint(0,9)) for _ in range(5-len(zp))])
    prov,prefixes=random.choice(PROVIDERS);prefix=random.choice(prefixes);suffix="".join([str(random.randint(0,9)) for _ in range(8)])
    phone=f"+62{prefix[1:]}{suffix}"
    email=f"{random.choice([f'{first.lower()}.{last.lower()}',f'{first.lower()}{last.lower()}',f'{first.lower()}_{last.lower()}',f'{first.lower()}{random.randint(1,999)}'])}@{random.choice(EMAIL_DOMAINS)}"
    cc_type=random.choice(list(CC_BINS.keys()));cc_info=CC_BINS[cc_type];bin_prefix=random.choice(cc_info["bins"])
    cc_number=luhn_generate(bin_prefix,cc_info["length"])
    now=datetime.now();exp_year=now.year+random.randint(1,4);exp_month=random.randint(1,12)
    cvv=str(random.randint(1000,9999)) if cc_type=="amex"else str(random.randint(100,999))
    return{"nik":"".join([str(random.randint(0,9)) for _ in range(16)]),"name":full_name,"first_name":first,"last_name":last,"gender":gender,"birth_date":birth.strftime("%Y-%m-%d"),"email":email,"phone":phone,"phone_provider":prov,"address":{"street":f"Jl. {street} No. {num}","rt":f"RT {rt:03d}","rw":f"RW {rw:03d}","city":city,"province":province,"zipcode":zipcode},"cc":{"number":cc_number,"formatted":format_cc(cc_number),"type":cc_type,"bin":bin_prefix,"expiry":f"{exp_month:02d}/{str(exp_year)[-2:]}","cvv":cvv,"cardholder":full_name.upper()}}

if __name__=="__main__":
    import sys;count=int(sys.argv[1]) if len(sys.argv)>1 else 5
    data=[generate_person_with_cc() for _ in range(count)]
    for i,p in enumerate(data,1):print(f"{i}. {p['name']} | NIK:{p['nik']} | {p['cc']['formatted']} {p['cc']['type'].upper()}")
    ts=datetime.now().strftime("%Y%m%d_%H%M%S");path=f"/home/ubuntu/dummy_data_{ts}.json"
    with open(path,"w") as f:json.dump(data,f,indent=2,ensure_ascii=False)
    print(f"✅ {count} records → {path}")
