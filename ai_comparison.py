import requests
import json
import os
import random
from datetime import datetime
from hashlib import sha256

SYSTEM_PROMPT = """You are an expert Azerbaijani automotive journalist writing for a premium Instagram page called @azvscars.
Your job is to pick two real, well-known competing cars and write a detailed comparison post in Azerbaijani.

CRITICAL LANGUAGE RULES:
- Write ONLY correct, natural Azerbaijani. Do NOT invent words.
- Valid Azerbaijani letters: A B C Ç D E Ə F G Ğ H X I İ J K Q L M N O Ö P R S Ş T U Ü V Y Z
- Common Azerbaijani automotive words: GÜC (power), SÜRƏT (speed), QİYMƏT (price), MÜHƏRRİK (engine), DÖYÜŞ (battle), YARIŞI (race/competition), DÖVRÜ (era), XÜLASƏSİ (summary), REYTİNQİ (rating), ZƏFƏRI (victory), RƏQABƏT (competition), ÜSTÜNLÜK (superiority)
- battle_title must be 2-4 words MAX, real Azerbaijani, related to the specific cars. Examples: "ALMAN DÖYÜŞÜ", "SUV YARIŞI", "SEDAN RƏQABƏTI", "İTALYAN ZƏFƏRI", "FRANSIZ DÖYÜŞÜ", "ELEKTRİK YARIŞI"
- battle_title must be 2-4 words MAX, real Azerbaijani, related to the specific cars. Examples: "ALMAN DÖYÜŞÜ", "SUV YARIŞI", "SEDAN RƏQABƏTI", "İTALYAN ZƏFƏRI", "FRANSIZ DÖYÜŞÜ", "ELEKTRİK YARIŞI"

Pick controversial, owner-tribe matchups that make people defend their side, similar to Barcelona vs Real Madrid debates.
Prefer pairs with a clear argument: China vs Germany, EV vs petrol, old-school V8 vs modern hybrid, Toyota/Lexus reliability vs German status, Tesla tech vs BMW/Mercedes luxury, Korean value vs Japanese reliability, American muscle vs European precision.
The cars do not always need to be exact same-class twins, but they must be realistically cross-shopped or culturally debated by car owners.
Good examples: BYD Seal vs Mercedes-Benz C-Class, Zeekr 001 vs Mercedes EQE, NIO ET5 vs BMW i4, Li Auto L9 vs Mercedes GLE, Tesla Model 3 Performance vs BMW M3, Toyota Land Cruiser vs Mercedes G-Class, Lexus LX vs Range Rover, old C63 V8 vs new C63 hybrid, Mustang GT vs BMW M4, Hyundai Ioniq 5 N vs Volkswagen Golf R.
Avoid boring random pairings that will not create comments.
Vary the pairs every time. Provide ONLY accurate, real-world specs.

Output ONLY valid JSON, absolutely no other text:
{
  "car1_name": "BMW M3 Competition",
  "car2_name": "Mercedes-AMG C63 S",
  "car1_search_query": "BMW M3 G80 side view",
  "car2_search_query": "Mercedes AMG C63 W205 side view",
  "battle_title": "ALMAN DÖYÜŞÜ",
  "slide2_title": "MÜHƏRRİK VƏ GÜC",
  "slide2_car1_stat": "3.0L I6 / 503 HP",
  "slide2_car2_stat": "4.0L V8 / 503 HP",
  "slide3_title": "0-100 KM/S",
  "slide3_car1_stat": "3.8 san.",
  "slide3_car2_stat": "3.9 san.",
  "slide4_title": "BAŞLANĞIC QİYMƏTİ",
  "slide4_car1_stat": "$76,000",
  "slide4_car2_stat": "$83,000",
  "caption": "2-3 sentences in natural Azerbaijani comparing these two cars with emojis.",
  "hashtags": "#azvscars #azerbaijan #avto #baku #masin"
}
"""

CURATED_MATCHUPS = {
    "quick": [
        {
            "car1_name": "BYD Seal",
            "car2_name": "Mercedes-Benz C-Class",
            "car1_search_query": "BYD Seal side view",
            "car2_search_query": "Mercedes-Benz C-Class W206 side view",
            "battle_title": "ÇİN YOXSA ALMAN",
            "slide2_car1_stat": "Dual motor / 523 HP",
            "slide2_car2_stat": "2.0L I4 / 255 HP",
            "slide3_car1_stat": "3.8 san.",
            "slide3_car2_stat": "6.0 san.",
            "slide4_car1_stat": "$49,000",
            "slide4_car2_stat": "$48,000",
            "caption": "Sürmək üçün birini seç: yeni Çin texnologiyası yoxsa klassik Mercedes imici? Bu seçim artıq çox adamı iki tərəfə bölür.",
        },
        {
            "car1_name": "Tesla Model 3 Performance",
            "car2_name": "BMW M3 Competition",
            "car1_search_query": "Tesla Model 3 Performance side view",
            "car2_search_query": "BMW M3 Competition G80 side view",
            "battle_title": "EV YOXSA BENZİN",
            "slide2_car1_stat": "Dual motor / 510 HP",
            "slide2_car2_stat": "3.0L I6 / 503 HP",
            "slide3_car1_stat": "3.1 san.",
            "slide3_car2_stat": "3.8 san.",
            "slide4_car1_stat": "$53,000",
            "slide4_car2_stat": "$76,000",
            "caption": "Sürmək üçün birini seç: ani elektrik zərbəsi yoxsa M ruhu? Burada texnologiya və sürücü hissi üz-üzədir.",
        },
        {
            "car1_name": "BMW M4 Competition",
            "car2_name": "Audi RS5 Coupe",
            "car1_search_query": "BMW M4 Competition G82 side view",
            "car2_search_query": "Audi RS5 Coupe side view",
            "battle_title": "KUPE SEÇİMİ",
            "slide2_car1_stat": "3.0L I6 / 503 HP",
            "slide2_car2_stat": "2.9L V6 / 444 HP",
            "slide3_car1_stat": "3.9 san.",
            "slide3_car2_stat": "3.9 san.",
            "slide4_car1_stat": "$79,000",
            "slide4_car2_stat": "$80,000",
            "caption": "Sürmək üçün birini seç: M4 yoxsa RS5? Biri daha aqressiv, biri daha sakit premium güc verir. 👀",
        },
        {
            "car1_name": "Toyota Supra GR",
            "car2_name": "Nissan Z",
            "car1_search_query": "Toyota GR Supra side view",
            "car2_search_query": "Nissan Z side view",
            "battle_title": "YAPON YARIŞI",
            "slide2_car1_stat": "3.0L I6 / 382 HP",
            "slide2_car2_stat": "3.0L V6 / 400 HP",
            "slide3_car1_stat": "4.1 san.",
            "slide3_car2_stat": "4.5 san.",
            "slide4_car1_stat": "$56,000",
            "slide4_car2_stat": "$43,000",
            "caption": "Sürmək üçün birini seç: Supra yoxsa Z? Klassik Yapon ruhu, iki fərqli xarakter. 👀",
        },
        {
            "car1_name": "Volkswagen Golf R",
            "car2_name": "Honda Civic Type R",
            "car1_search_query": "Volkswagen Golf R Mk8 side view",
            "car2_search_query": "Honda Civic Type R FL5 side view",
            "battle_title": "HOT HATCH",
            "slide2_car1_stat": "2.0L I4 / 315 HP",
            "slide2_car2_stat": "2.0L I4 / 315 HP",
            "slide3_car1_stat": "4.7 san.",
            "slide3_car2_stat": "5.4 san.",
            "slide4_car1_stat": "$46,000",
            "slide4_car2_stat": "$45,000",
            "caption": "Sürmək üçün birini seç: Golf R yoxsa Type R? Gündəlik rahatlıq, yoxsa trek ruhu? 👀",
        },
        {
            "car1_name": "Tesla Model 3 Performance",
            "car2_name": "BMW i4 M50",
            "car1_search_query": "Tesla Model 3 Performance side view",
            "car2_search_query": "BMW i4 M50 side view",
            "battle_title": "ELEKTRİK DUELİ",
            "slide2_car1_stat": "Dual motor / 510 HP",
            "slide2_car2_stat": "Dual motor / 536 HP",
            "slide3_car1_stat": "3.1 san.",
            "slide3_car2_stat": "3.9 san.",
            "slide4_car1_stat": "$53,000",
            "slide4_car2_stat": "$70,000",
            "caption": "Sürmək üçün birini seç: Model 3 Performance yoxsa i4 M50? Sürət rəqəmləri çox sərtdir. 👀",
        },
        {
            "car1_name": "Mazda MX-5 Miata",
            "car2_name": "Toyota GR86",
            "car1_search_query": "Mazda MX-5 ND side view",
            "car2_search_query": "Toyota GR86 side view",
            "battle_title": "SÜRÜCÜ SEÇİMİ",
            "slide2_car1_stat": "2.0L I4 / 181 HP",
            "slide2_car2_stat": "2.4L I4 / 228 HP",
            "slide3_car1_stat": "5.7 san.",
            "slide3_car2_stat": "6.1 san.",
            "slide4_car1_stat": "$29,000",
            "slide4_car2_stat": "$30,000",
            "caption": "Sürmək üçün birini seç: MX-5 yoxsa GR86? Saf sürüş zövqü axtaranlar üçün çətin seçimdir. 👀",
        },
        {
            "car1_name": "Range Rover Sport",
            "car2_name": "Porsche Cayenne",
            "car1_search_query": "Range Rover Sport L461 side view",
            "car2_search_query": "Porsche Cayenne side view",
            "battle_title": "LUKS SUV",
            "slide2_car1_stat": "3.0L I6 / 395 HP",
            "slide2_car2_stat": "3.0L V6 / 348 HP",
            "slide3_car1_stat": "5.4 san.",
            "slide3_car2_stat": "5.7 san.",
            "slide4_car1_stat": "$83,000",
            "slide4_car2_stat": "$80,000",
            "caption": "Sürmək üçün birini seç: Range Rover Sport yoxsa Cayenne? Status, rahatlıq və sürüş eyni kadra düşür. 👀",
        },
    ],
    "main": [
        {
            "car1_name": "Zeekr 001",
            "car2_name": "Mercedes-Benz EQE",
            "car1_search_query": "Zeekr 001 side view",
            "car2_search_query": "Mercedes-Benz EQE side view",
            "battle_title": "ÇİN PREMIUMU",
            "slide2_car1_stat": "Dual motor / 536 HP",
            "slide2_car2_stat": "Dual motor / 402 HP",
            "slide3_car1_stat": "3.8 san.",
            "slide3_car2_stat": "4.5 san.",
            "slide4_car1_stat": "$60,000",
            "slide4_car2_stat": "$77,000",
            "caption": "Zeekr rəqəmlərlə hücum edir, EQE isə Mercedes imici və rahatlığı ilə cavab verir. Premium seçimdə marka vacibdir, yoxsa texnologiya?",
        },
        {
            "car1_name": "Toyota Land Cruiser 300",
            "car2_name": "Mercedes-Benz G 500",
            "car1_search_query": "Toyota Land Cruiser 300 side view",
            "car2_search_query": "Mercedes-Benz G 500 side view",
            "battle_title": "ETİBAR YOXSA STATUS",
            "slide2_car1_stat": "3.4L V6 / 409 HP",
            "slide2_car2_stat": "4.0L V8 / 416 HP",
            "slide3_car1_stat": "6.7 san.",
            "slide3_car2_stat": "5.9 san.",
            "slide4_car1_stat": "$85,000",
            "slide4_car2_stat": "$148,000",
            "caption": "Land Cruiser uzunömürlülük simvoludur, G-Class isə statusun özüdür. Bakıda hansı seçim daha ağıllıdır?",
        },
        {
            "car1_name": "BMW M5 Competition",
            "car2_name": "Mercedes-AMG E63 S",
            "car1_search_query": "BMW M5 Competition F90 side view",
            "car2_search_query": "Mercedes AMG E63 S W213 side view",
            "battle_title": "ALMAN DÖYÜŞÜ",
            "slide2_car1_stat": "4.4L V8 / 617 HP",
            "slide2_car2_stat": "4.0L V8 / 603 HP",
            "slide3_car1_stat": "3.3 san.",
            "slide3_car2_stat": "3.4 san.",
            "slide4_car1_stat": "$111,000",
            "slide4_car2_stat": "$108,000",
            "caption": "M5 daha kəskin sürət hissi verir, E63 S isə səsi və xarakteri ilə cavab verir. Güc, komfort və prestij baxımından hansı qalibdir? 🔥",
        },
        {
            "car1_name": "Porsche 911 Carrera S",
            "car2_name": "Chevrolet Corvette Stingray",
            "car1_search_query": "Porsche 911 Carrera S 992 side view",
            "car2_search_query": "Chevrolet Corvette C8 Stingray side view",
            "battle_title": "SPORT RƏQABƏTİ",
            "slide2_car1_stat": "3.0L F6 / 443 HP",
            "slide2_car2_stat": "6.2L V8 / 495 HP",
            "slide3_car1_stat": "3.5 san.",
            "slide3_car2_stat": "2.9 san.",
            "slide4_car1_stat": "$131,000",
            "slide4_car2_stat": "$69,000",
            "caption": "911 dəqiqliyi ilə seçilir, Corvette isə qiymətə görə inanılmaz performans verir. Pul səndə olsa hansı daha məntiqlidir? 🏁",
        },
        {
            "car1_name": "Toyota Camry XSE V6",
            "car2_name": "Honda Accord 2.0T",
            "car1_search_query": "Toyota Camry XSE V6 side view",
            "car2_search_query": "Honda Accord 2.0T side view",
            "battle_title": "SEDAN RƏQABƏTİ",
            "slide2_car1_stat": "3.5L V6 / 301 HP",
            "slide2_car2_stat": "2.0L I4 / 252 HP",
            "slide3_car1_stat": "5.8 san.",
            "slide3_car2_stat": "5.5 san.",
            "slide4_car1_stat": "$36,000",
            "slide4_car2_stat": "$34,000",
            "caption": "Camry V6 sakit və etibarlı güc verir, Accord 2.0T isə daha çevik hiss etdirir. Ailə sedanında hansı seçim daha ağıllıdır? 🚗",
        },
        {
            "car1_name": "Mercedes-Benz G 63 AMG",
            "car2_name": "Range Rover P530",
            "car1_search_query": "Mercedes AMG G63 side view",
            "car2_search_query": "Range Rover P530 side view",
            "battle_title": "STATUS DÖYÜŞÜ",
            "slide2_car1_stat": "4.0L V8 / 577 HP",
            "slide2_car2_stat": "4.4L V8 / 523 HP",
            "slide3_car1_stat": "4.5 san.",
            "slide3_car2_stat": "4.6 san.",
            "slide4_car1_stat": "$183,000",
            "slide4_car2_stat": "$131,000",
            "caption": "G63 daha sərt və səsli xarakterdir, Range Rover isə lüks rahatlıqla cavab verir. Bakıda hansının aurası daha güclüdür? 💎",
        },
        {
            "car1_name": "Audi RS7 Sportback",
            "car2_name": "BMW M8 Gran Coupe",
            "car1_search_query": "Audi RS7 Sportback C8 side view",
            "car2_search_query": "BMW M8 Gran Coupe side view",
            "battle_title": "FASTBACK DÖYÜŞÜ",
            "slide2_car1_stat": "4.0L V8 / 591 HP",
            "slide2_car2_stat": "4.4L V8 / 617 HP",
            "slide3_car1_stat": "3.6 san.",
            "slide3_car2_stat": "3.0 san.",
            "slide4_car1_stat": "$128,000",
            "slide4_car2_stat": "$140,000",
            "caption": "RS7 dizayn və praktikliklə vurur, M8 Gran Coupe isə daha aqressiv performans göstərir. Sənin qalibin hansıdır? ⚡",
        },
        {
            "car1_name": "Lexus LX 600",
            "car2_name": "Toyota Land Cruiser 300",
            "car1_search_query": "Lexus LX 600 side view",
            "car2_search_query": "Toyota Land Cruiser 300 side view",
            "battle_title": "YAPON SUV",
            "slide2_car1_stat": "3.4L V6 / 409 HP",
            "slide2_car2_stat": "3.4L V6 / 409 HP",
            "slide3_car1_stat": "6.9 san.",
            "slide3_car2_stat": "6.7 san.",
            "slide4_car1_stat": "$93,000",
            "slide4_car2_stat": "$85,000",
            "caption": "LX 600 daha lüks yanaşmadır, Land Cruiser isə dözümlülük simvoludur. Uzun illər üçün hansını seçərdin? 🛡️",
        },
    ],
    "war": [
        {
            "car1_name": "Li Auto L9",
            "car2_name": "Mercedes-Benz GLE 450",
            "car1_search_query": "Li Auto L9 side view",
            "car2_search_query": "Mercedes-Benz GLE 450 side view",
            "battle_title": "ÇİN YOXSA MERCEDES",
            "slide2_car1_stat": "EREV / 449 HP",
            "slide2_car2_stat": "3.0L I6 / 375 HP",
            "slide3_car1_stat": "5.3 san.",
            "slide3_car2_stat": "5.6 san.",
            "slide4_car1_stat": "$62,000",
            "slide4_car2_stat": "$70,000",
            "caption": "Bu duel car-owner mübahisəsidir: Li Auto L9 yoxsa Mercedes GLE? Biri texnologiya ilə, biri marka gücü ilə gəlir. Sol yoxsa sağ?",
        },
        {
            "car1_name": "Lexus LX 600",
            "car2_name": "Range Rover P530",
            "car1_search_query": "Lexus LX 600 side view",
            "car2_search_query": "Range Rover P530 side view",
            "battle_title": "ETİBAR YOXSA LÜKS",
            "slide2_car1_stat": "3.4L V6 / 409 HP",
            "slide2_car2_stat": "4.4L V8 / 523 HP",
            "slide3_car1_stat": "6.9 san.",
            "slide3_car2_stat": "4.6 san.",
            "slide4_car1_stat": "$93,000",
            "slide4_car2_stat": "$131,000",
            "caption": "Bir tərəfdə Lexus etibarı, digər tərəfdə Range Rover lüksü. Uzun illər üçün hansını seçərdin?",
        },
        {
            "car1_name": "BMW X5 M50i",
            "car2_name": "Mercedes-AMG GLE 53",
            "car1_search_query": "BMW X5 M50i side view",
            "car2_search_query": "Mercedes AMG GLE 53 side view",
            "battle_title": "SUV SAVAŞI",
            "slide2_car1_stat": "4.4L V8 / 523 HP",
            "slide2_car2_stat": "3.0L I6 / 429 HP",
            "slide3_car1_stat": "4.1 san.",
            "slide3_car2_stat": "5.2 san.",
            "slide4_car1_stat": "$86,000",
            "slide4_car2_stat": "$87,000",
            "caption": "100.000 AZN olsa hansını alardın? Sol yoxsa sağ? Cavabı kommentə yaz. Sabah ən çox seçilən maşını yeni rəqiblə çıxarıram.",
        },
        {
            "car1_name": "Porsche Panamera 4S",
            "car2_name": "Mercedes-AMG GT 53",
            "car1_search_query": "Porsche Panamera 4S side view",
            "car2_search_query": "Mercedes AMG GT 53 4-door side view",
            "battle_title": "LUKS SAVAŞ",
            "slide2_car1_stat": "2.9L V6 / 443 HP",
            "slide2_car2_stat": "3.0L I6 / 429 HP",
            "slide3_car1_stat": "4.1 san.",
            "slide3_car2_stat": "4.4 san.",
            "slide4_car1_stat": "$110,000",
            "slide4_car2_stat": "$107,000",
            "caption": "100.000 AZN olsa hansını alardın? Sol yoxsa sağ? Cavabı kommentə yaz. Sabah ən çox seçilən maşını yeni rəqiblə çıxarıram.",
        },
        {
            "car1_name": "Ford Mustang GT",
            "car2_name": "Chevrolet Camaro SS",
            "car1_search_query": "Ford Mustang GT S550 side view",
            "car2_search_query": "Chevrolet Camaro SS side view",
            "battle_title": "MUSCLE WAR",
            "slide2_car1_stat": "5.0L V8 / 450 HP",
            "slide2_car2_stat": "6.2L V8 / 455 HP",
            "slide3_car1_stat": "4.3 san.",
            "slide3_car2_stat": "4.0 san.",
            "slide4_car1_stat": "$42,000",
            "slide4_car2_stat": "$44,000",
            "caption": "100.000 AZN olsa hansını alardın? Sol yoxsa sağ? Cavabı kommentə yaz. Sabah ən çox seçilən maşını yeni rəqiblə çıxarıram.",
        },
        {
            "car1_name": "Audi S8",
            "car2_name": "BMW 760i",
            "car1_search_query": "Audi S8 D5 side view",
            "car2_search_query": "BMW 760i G70 side view",
            "battle_title": "BİZNES SAVAŞI",
            "slide2_car1_stat": "4.0L V8 / 563 HP",
            "slide2_car2_stat": "4.4L V8 / 536 HP",
            "slide3_car1_stat": "3.8 san.",
            "slide3_car2_stat": "4.1 san.",
            "slide4_car1_stat": "$124,000",
            "slide4_car2_stat": "$122,000",
            "caption": "100.000 AZN olsa hansını alardın? Sol yoxsa sağ? Cavabı kommentə yaz. Sabah ən çox seçilən maşını yeni rəqiblə çıxarıram.",
        },
    ],
    "night": [
        {
            "car1_name": "Mercedes-AMG C63 S Coupe",
            "car2_name": "BMW M4 Competition",
            "car1_search_query": "Mercedes AMG C63 S Coupe side view",
            "car2_search_query": "BMW M4 Competition G82 side view",
            "battle_title": "GECƏ DÖYÜŞÜ",
            "slide2_car1_stat": "4.0L V8 / 503 HP",
            "slide2_car2_stat": "3.0L I6 / 503 HP",
            "slide3_car1_stat": "3.9 san.",
            "slide3_car2_stat": "3.9 san.",
            "slide4_car1_stat": "$82,000",
            "slide4_car2_stat": "$79,000",
            "caption": "Gecə Bakıda sürmək üçün hansını seçərdin? 1 sözlə yaz: sol yoxsa sağ?",
        },
        {
            "car1_name": "BMW M5 CS",
            "car2_name": "Audi RS6 Avant",
            "car1_search_query": "BMW M5 CS side view",
            "car2_search_query": "Audi RS6 Avant C8 side view",
            "battle_title": "GECƏ CANAVARI",
            "slide2_car1_stat": "4.4L V8 / 627 HP",
            "slide2_car2_stat": "4.0L V8 / 591 HP",
            "slide3_car1_stat": "2.9 san.",
            "slide3_car2_stat": "3.6 san.",
            "slide4_car1_stat": "$143,000",
            "slide4_car2_stat": "$126,000",
            "caption": "Gecə Bakıda sürmək üçün hansını seçərdin? 1 sözlə yaz: sol yoxsa sağ?",
        },
        {
            "car1_name": "Nissan GT-R",
            "car2_name": "Porsche 911 Turbo S",
            "car1_search_query": "Nissan GT-R R35 side view",
            "car2_search_query": "Porsche 911 Turbo S 992 side view",
            "battle_title": "TURBO GECƏSİ",
            "slide2_car1_stat": "3.8L V6 / 565 HP",
            "slide2_car2_stat": "3.8L F6 / 640 HP",
            "slide3_car1_stat": "2.9 san.",
            "slide3_car2_stat": "2.6 san.",
            "slide4_car1_stat": "$121,000",
            "slide4_car2_stat": "$230,000",
            "caption": "Gecə Bakıda sürmək üçün hansını seçərdin? 1 sözlə yaz: sol yoxsa sağ?",
        },
        {
            "car1_name": "Lamborghini Huracan EVO",
            "car2_name": "Ferrari F8 Tributo",
            "car1_search_query": "Lamborghini Huracan EVO side view",
            "car2_search_query": "Ferrari F8 Tributo side view",
            "battle_title": "İTALYAN GECƏSİ",
            "slide2_car1_stat": "5.2L V10 / 631 HP",
            "slide2_car2_stat": "3.9L V8 / 710 HP",
            "slide3_car1_stat": "2.9 san.",
            "slide3_car2_stat": "2.9 san.",
            "slide4_car1_stat": "$250,000",
            "slide4_car2_stat": "$280,000",
            "caption": "Gecə Bakıda sürmək üçün hansını seçərdin? 1 sözlə yaz: sol yoxsa sağ?",
        },
    ],
}

def curated_comparison(post_type="main") -> dict:
    pool = CURATED_MATCHUPS.get(post_type) or CURATED_MATCHUPS["main"]
    today_key = datetime.utcnow().strftime("%Y%m%d")
    type_offset = {"quick": 0, "main": 7, "war": 13, "night": 19}.get(post_type, 0)
    manual_seed = os.environ.get("CONTENT_SEED")
    if manual_seed:
        seed_source = f"manual:{manual_seed}:{post_type}"
    elif os.environ.get("GITHUB_RUN_ID"):
        seed_source = f"github:{today_key}:{post_type}:{os.environ.get('GITHUB_RUN_ID')}:{os.environ.get('GITHUB_RUN_ATTEMPT', '1')}"
    else:
        seed_source = f"local:{today_key}:{post_type}:{random.randint(1, 1_000_000)}"
    seed = int(sha256(seed_source.encode("utf-8")).hexdigest()[:12], 16) + type_offset
    idx = seed % len(pool)
    item = dict(pool[idx])
    item.update({
        "slide2_title": "MÜHƏRRİK VƏ GÜC",
        "slide3_title": "0-100 KM/S",
        "slide4_title": "BAŞLANĞIC QİYMƏTİ",
        "hashtags": "#azvscars #azerbaijan #avto #baku #masin #cars",
    })
    return item

def generate_comparison(post_type="main") -> dict:
    """
    Calls Cloudflare Workers AI to generate a random car comparison based on the post format.
    post_type can be: "quick", "main", "war", "night"
    """
    pages_base_url = os.environ.get("PAGES_BASE_URL", "").rstrip("/")
    admin_pass = os.environ.get("ADMIN_PASS", "")
    if pages_base_url and admin_pass:
        try:
            print("Requesting AI generation through Pages AI endpoint...")
            response = requests.post(
                f"{pages_base_url}/api/ai-comparison",
                headers={
                    "Content-Type": "application/json",
                    "X-Admin-Password": admin_pass,
                },
                json={"post_type": post_type},
                timeout=45,
            )
            response.raise_for_status()
            data = response.json()
            if data.get("ok") and isinstance(data.get("comparison"), dict):
                return data["comparison"]
            raise RuntimeError(f"Unexpected Pages AI response: {data}")
        except Exception as e:
            print(f"⚠️ Pages AI generation failed. Falling back to direct Cloudflare API or curated content. Error: {e}")

    account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID") or os.environ.get("CF_ACCOUNT_ID", "")
    api_token = os.environ.get("CLOUDFLARE_API_TOKEN") or os.environ.get("CF_API_TOKEN", "")
    
    if not account_id or not api_token:
        print("⚠️ No Cloudflare credentials found. Using curated rotating content.")
        return curated_comparison(post_type)
        
    print("Requesting AI generation from Cloudflare Workers AI...")
    
    # Current low-latency text model on Workers AI.
    model = "@cf/meta/llama-3.2-3b-instruct"
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}"
    
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    
    seed = random.randint(1, 100000)
    
    # Customize instructions based on post_type
    if post_type == "quick":
        post_instruction = "POST TYPE: 'Quick Choice'. The caption MUST be short and ask 'Sürmək üçün birini seç: A yoxsa B? Məncə bu seçim çox çətindir 👀'. Cars should be simple, highly recognizable."
    elif post_type == "war":
        post_instruction = "POST TYPE: 'Comment War'. The caption MUST ask '100.000 AZN olsa hansını alardın? Sol yoxsa sağ? Cavabı kommentə yaz. Sabah ən çox seçilən maşını yeni rəqiblə çıxarıram.'. Pick expensive cars around 100k budget."
    elif post_type == "night":
        post_instruction = "POST TYPE: 'Dark Night Battle'. The caption MUST ask 'Gecə Bakıda sürmək üçün hansını seçərdin? 1 sözlə yaz: sol yoxsa sağ?'. Pick aggressive, loud cars (e.g. C63, M5, RS7)."
    else:
        post_instruction = "POST TYPE: 'Real VS Battle'. The caption MUST compare 3 features briefly and ask 'Hansı qalibdir?'. Keep it under 5 bullet points."
    
    prompt_content = f"Generate a new, random car comparison. Random Seed: {seed}.\n{post_instruction}\nReturn ONLY the JSON object, no explanation."
    
    payload = {
        "max_tokens": 1000,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt_content}
        ]
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        result_data = response.json()
        content = result_data["result"]["response"]
        
        # Cloudflare might automatically parse it as a dict if Llama returns perfect JSON
        if isinstance(content, dict):
            return content
            
        content_text = str(content)
        # Clean up JSON formatting if the model wrapped it in markdown blocks
        if "```json" in content_text:
            content_text = content_text.split("```json")[1].split("```")[0].strip()
        elif "```" in content_text:
            content_text = content_text.split("```")[1].split("```")[0].strip()
            
        return json.loads(content_text)
        
    except Exception as e:
        print(f"Failed to fetch or parse JSON from Cloudflare AI. Error: {e}")
        # Optionally, you can print the raw response if available
        if 'response' in locals() and hasattr(response, 'text'):
            print(f"Raw Response: {response.text}")
        raise e

if __name__ == "__main__":
    print(generate_comparison())
