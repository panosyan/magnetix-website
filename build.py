#!/usr/bin/env python3
"""Build the Magnetix static website into ./public.

Inputs (all in this folder):
  assets/items.json        chair list exported from the Mac Models/ folder (code, price, stock; no buyer data)
  assets/img/<slug>/       front/side/semi (white) + int-front/int-side/int-semi (interior) photos
  data-captions.json       Armenian post captions, used as chair descriptions
Run:  python3 build.py
"""
import json, os, re, shutil, html, datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, 'public')
SITE = os.environ.get('SITE_URL', 'https://magnetix.onrender.com').rstrip('/')
PHONE = '+374 99 503009'
PHONE_RAW = '37499503009'
EMAIL = 'magnetixfurniture@gmail.com'
IG = 'https://www.instagram.com/magnetix.am/'
FB = 'https://www.facebook.com/magnetix.am'
SHEET_CSV = os.environ.get('SHEET_CSV', 'https://docs.google.com/spreadsheets/d/e/2PACX-1vSyHX8xAUl1c9w0xTGGRTLEaRhSMnY8tcohFePf1wn5HpHqMtuJ7wUzHIqrHRSMN7LYh407XomkYkLI/pub?gid=0&single=true&output=csv')  # published Google Sheet (CSV) with live price/stock/sold out
HIDE = {'928black', '928grey', '8856 B'}  # 8856 B = duplicate of 8856 B black  # wrong/unconfirmed codes: keep off the site until GAP confirms

# ---------------------------------------------------------------- texts
T = {
 'hy': dict(
  htmllang='hy', label='Հայ', title='Magnetix Furniture · Գրասենյակային բազկաթոռներ Երևանում',
  desc='Գրասենյակային և ղեկավարի բազկաթոռներ անմիջապես ներմուծողից։ Մեծ ընտրանի, ցածր գներ, մեծածախ պատվերների հատուկ պայմաններ։ Երևան։',
  nav_home='Գլխավոր', nav_cat='Կատալոգ', nav_b2b='Ընկերությունների համար', nav_contact='Կապ',
  hero_kicker='Անմիջապես ներմուծողից',
  hero_h='Գրասենյակային բազկաթոռներ՝ ներմուծողի գներով',
  hero_p='Ղեկավարի, աշխատակցի և այցելուի բազկաթոռներ։ Մեծ ընտրանի և պահեստում առկա քանակ Երևանում։',
  cta_cat='Դիտել կատալոգը', cta_wa='Գրել WhatsApp-ով', cta_call='Զանգել',
  why_h='Ինչու Magnetix',
  why=[('Ներմուծողի գներ','Աթոռները բերում ենք ուղիղ արտադրողից, առանց միջնորդների, ուստի գները շուկայականից ցածր են։'),
       ('Մեծ ընտրանի','Ավելի քան 70 մոդել և գույն՝ ղեկավարի կաշվե բազկաթոռներից մինչև ցանցային և այցելուի աթոռներ։'),
       ('Պահեստում առկա','Շատ մոդելներ առկա են տասնյակ և հարյուրավոր հատերով՝ ամբողջ գրասենյակը կահավորելու համար։'),
       ('Մեծածախ պայմաններ','Ընկերությունների համար՝ հատուկ գներ, հաշիվ-ապրանքագիր և անկանխիկ վճարում։')],
  feat_h='Ընտրված մոդելներ', all_models='Բոլոր մոդելները',
  cat_h='Կատալոգ', cat_p='Բոլոր գները ՀՀ դրամով։ Ընտրեք մոդելը և գրեք մեզ՝ պատվիրելու համար։',
  f_all='Բոլորը', f_exec='Ղեկավարի', f_office='Գրասենյակային', f_visitor='Այցելուի և բյուջետային',
  f_color='Գույն', f_anycolor='Բոլոր գույները', f_sort='Դասավորել', s_def='Ըստ նախնականի', s_up='Գինը՝ աճման կարգով', s_down='Գինը՝ նվազման կարգով',
  f_instock='Միայն առկաները', f_search='Որոնել ըստ կոդի…', none_found='Այս ընտրությամբ մոդել չգտնվեց։',
  models_n='մոդել',
  amd='դրամ', instock='Առկա է', few='Վերջին հատերը', ask='Հարցրեք առկայությունը', sold='Վաճառված է',
  model='Մոդել', color='Գույն', price='Գին', category='Տեսակ', availability='Առկայություն',
  order_wa='Պատվիրել WhatsApp-ով', order_call='Զանգել', order_ig='Գրել Instagram-ում',
  wa_msg='Բարև Ձեզ, հետաքրքրում է {m} մոդելը ({p} դրամ)։',
  bulk_note='Մեծածախ պատվերների համար՝ հատուկ պայմաններ։', bulk_link='Մանրամասն',
  other_colors='Այլ գույներ', similar='Նման մոդելներ',
  photos_white='Սպիտակ ֆոնով', photos_int='Ինտերիերում',
  b2b_h='Ընկերությունների և մեծածախ պատվերների համար',
  b2b_p='Կահավորում եք նոր գրասենյակ, բանկ, դպրոց կամ կոնֆերանս սրահ։ Մենք ներմուծող ենք, ուստի կարող ենք առաջարկել մեծածախ գներ և տրամադրել անհրաժեշտ փաստաթղթերը։',
  b2b_points=[('Մեծածախ գներ','Գինը կախված է քանակից։ Ուղարկեք ցանկը, և մենք կպատրաստենք անհատական առաջարկ։'),
              ('Հաշիվ-ապրանքագիր','Տրամադրում ենք հաշիվ և հաշիվ-ապրանքագիր ընկերության անունով։'),
              ('Անկանխիկ վճարում','Վճարումը՝ բանկային փոխանցումով։'),
              ('Մեծ քանակներ պահեստում','Շատ մոդելներ առկա են հարյուրավոր հատերով, որ ամբողջ թիմը նստի նույն աթոռներին։')],
  steps_h='Ինչպես պատվիրել', steps=['Ընտրեք մոդելները կատալոգից կամ ներբեռնեք մեր ապրանքացանկը։','Ուղարկեք մոդելների և քանակների ցանկը WhatsApp-ով կամ էլ. փոստով։','Մենք կհաստատենք առկայությունը և կուղարկենք հաշիվը։','Վճարում եք բանկային փոխանցումով, և պատվերը պատրաստ է։'],
  dl_pdf='Ներբեռնել ապրանքացանկը (PDF)', b2b_cta='Ուղարկել հարցում',
  contact_h='Կապ մեզ հետ', contact_p='Պատվերների և հարցերի համար զանգահարեք կամ գրեք մեզ։ Պատասխանում ենք արագ։',
  phone='Հեռախոս', email='Էլ. փոստ', social='Սոցիալական ցանցեր', city='Երևան, Հայաստան',
  foot_about='Գրասենյակային և ղեկավարի բազկաթոռներ անմիջապես ներմուծողից։ Երևան, Հայաստան։',
  rights='Բոլոր իրավունքները պաշտպանված են։', back='Կատալոգ',
  colors=dict(black='սև',grey='մոխրագույն',brown='շագանակագույն',white='սպիտակ',blue='կապույտ',orange='նարնջագույն',red='կարմիր',green='կանաչ',yellow='դեղին',khaki='խակի',beige='բեժ',moca='մոկա'),
 ),
 'ru': dict(
  htmllang='ru', label='Рус', title='Magnetix Furniture · Офисные кресла в Ереване',
  desc='Офисные кресла и кресла руководителя напрямую от импортёра. Большой выбор, низкие цены, особые условия для оптовых заказов. Ереван.',
  nav_home='Главная', nav_cat='Каталог', nav_b2b='Для компаний', nav_contact='Контакты',
  hero_kicker='Напрямую от импортёра',
  hero_h='Офисные кресла по ценам импортёра',
  hero_p='Кресла для руководителя, сотрудников и посетителей. Большой выбор и наличие на складе в Ереване.',
  cta_cat='Смотреть каталог', cta_wa='Написать в WhatsApp', cta_call='Позвонить',
  why_h='Почему Magnetix',
  why=[('Цены импортёра','Мы привозим кресла напрямую от производителя, без посредников, поэтому цены ниже рыночных.'),
       ('Большой выбор','Более 70 моделей и цветов: от кожаных кресел руководителя до сетчатых и стульев для посетителей.'),
       ('В наличии','Многие модели есть на складе десятками и сотнями штук, чтобы обставить весь офис.'),
       ('Опт для компаний','Особые цены, счёт-фактура и оплата банковским переводом.')],
  feat_h='Избранные модели', all_models='Все модели',
  cat_h='Каталог', cat_p='Все цены в драмах. Выберите модель и напишите нам, чтобы заказать.',
  f_all='Все', f_exec='Руководителя', f_office='Офисные', f_visitor='Для посетителей и бюджетные',
  f_color='Цвет', f_anycolor='Все цвета', f_sort='Сортировка', s_def='По умолчанию', s_up='Сначала дешевле', s_down='Сначала дороже',
  f_instock='Только в наличии', f_search='Поиск по коду…', none_found='По этому запросу моделей нет.',
  models_n='моделей',
  amd='драм', instock='В наличии', few='Последние штуки', ask='Наличие уточняйте', sold='Продано',
  model='Модель', color='Цвет', price='Цена', category='Тип', availability='Наличие',
  order_wa='Заказать в WhatsApp', order_call='Позвонить', order_ig='Написать в Instagram',
  wa_msg='Здравствуйте, интересует модель {m} ({p} драм).',
  bulk_note='Для оптовых заказов особые условия.', bulk_link='Подробнее',
  other_colors='Другие цвета', similar='Похожие модели',
  photos_white='На белом фоне', photos_int='В интерьере',
  b2b_h='Для компаний и оптовых заказов',
  b2b_p='Обставляете новый офис, банк, школу или конференц-зал? Мы импортёр, поэтому предлагаем оптовые цены и все нужные документы.',
  b2b_points=[('Оптовые цены','Цена зависит от количества. Пришлите список, и мы подготовим индивидуальное предложение.'),
              ('Счёт-фактура','Выставляем счёт и счёт-фактуру на компанию.'),
              ('Безналичная оплата','Оплата банковским переводом.'),
              ('Большие объёмы на складе','Многие модели есть сотнями штук, чтобы вся команда сидела на одинаковых креслах.')],
  steps_h='Как заказать', steps=['Выберите модели в каталоге или скачайте наш прайс-лист.','Отправьте список моделей и количество в WhatsApp или на почту.','Мы подтвердим наличие и пришлём счёт.','Вы оплачиваете банковским переводом, и заказ готов.'],
  dl_pdf='Скачать прайс-лист (PDF)', b2b_cta='Отправить запрос',
  contact_h='Связаться с нами', contact_p='Для заказов и вопросов позвоните или напишите нам. Отвечаем быстро.',
  phone='Телефон', email='Эл. почта', social='Соцсети', city='Ереван, Армения',
  foot_about='Офисные кресла и кресла руководителя напрямую от импортёра. Ереван, Армения.',
  rights='Все права защищены.', back='Каталог',
  colors=dict(black='чёрный',grey='серый',brown='коричневый',white='белый',blue='синий',orange='оранжевый',red='красный',green='зелёный',yellow='жёлтый',khaki='хаки',beige='бежевый',moca='мокко'),
 ),
 'en': dict(
  htmllang='en', label='Eng', title='Magnetix Furniture · Office chairs in Yerevan',
  desc='Office and executive chairs direct from the importer. Wide range, low prices and special terms for bulk orders. Yerevan, Armenia.',
  nav_home='Home', nav_cat='Catalog', nav_b2b='For companies', nav_contact='Contact',
  hero_kicker='Direct from the importer',
  hero_h='Office chairs at importer prices',
  hero_p='Executive, staff and visitor chairs. A wide range, in stock in Yerevan.',
  cta_cat='Browse the catalog', cta_wa='Message on WhatsApp', cta_call='Call us',
  why_h='Why Magnetix',
  why=[('Importer prices','We bring chairs straight from the factory with no middlemen, so prices are below the market.'),
       ('Wide range','Over 70 models and colours, from leather executive chairs to mesh and visitor chairs.'),
       ('In stock','Many models are in stock by the dozen or hundred, enough to furnish a whole office.'),
       ('Bulk terms','Special prices for companies, invoices and payment by bank transfer.')],
  feat_h='Featured chairs', all_models='All models',
  cat_h='Catalog', cat_p='All prices in Armenian dram (AMD). Pick a model and message us to order.',
  f_all='All', f_exec='Executive', f_office='Office', f_visitor='Visitor & budget',
  f_color='Colour', f_anycolor='All colours', f_sort='Sort', s_def='Default', s_up='Price: low to high', s_down='Price: high to low',
  f_instock='In stock only', f_search='Search by code…', none_found='No models match this filter.',
  models_n='models',
  amd='AMD', instock='In stock', few='Last pieces', ask='Ask about stock', sold='Sold out',
  model='Model', color='Colour', price='Price', category='Type', availability='Availability',
  order_wa='Order on WhatsApp', order_call='Call', order_ig='Message on Instagram',
  wa_msg='Hello, I am interested in the {m} model ({p} AMD).',
  bulk_note='Special terms for bulk orders.', bulk_link='Learn more',
  other_colors='Other colours', similar='Similar chairs',
  photos_white='On white', photos_int='In an interior',
  b2b_h='For companies and bulk orders',
  b2b_p='Furnishing a new office, bank, school or conference room? As the importer we can offer bulk prices and all the paperwork you need.',
  b2b_points=[('Bulk prices','The price depends on quantity. Send us your list and we will prepare a quote.'),
              ('Invoices','We issue an invoice and tax invoice in your company name.'),
              ('Bank transfer','Pay by bank transfer, no cash needed.'),
              ('Large stock','Many models are in stock by the hundred, so the whole team gets the same chair.')],
  steps_h='How to order', steps=['Pick models from the catalog or download our price list.','Send the models and quantities by WhatsApp or email.','We confirm stock and send you an invoice.','You pay by bank transfer and your order is ready.'],
  dl_pdf='Download the price list (PDF)', b2b_cta='Send a request',
  contact_h='Contact us', contact_p='Call or message us for orders and questions. We reply fast.',
  phone='Phone', email='Email', social='Social', city='Yerevan, Armenia',
  foot_about='Office and executive chairs direct from the importer. Yerevan, Armenia.',
  rights='All rights reserved.', back='Catalog',
  colors=dict(black='black',grey='grey',brown='brown',white='white',blue='blue',orange='orange',red='red',green='green',yellow='yellow',khaki='khaki',beige='beige',moca='mocha'),
 ),
}
LANGS = ['hy', 'ru', 'en']
PREFIX = {'hy': '', 'ru': '/ru', 'en': '/en'}

# ---------------------------------------------------------------- data
COLOR_RX = [('black', r'black'), ('grey', r'grey|gray|\bgr\b|agr$|gr$'), ('brown', r'brown'), ('white', r'white'),
            ('blue', r'blue'), ('orange', r'orange'), ('red', r'\bred\b'), ('green', r'green'), ('yellow', r'yellow'),
            ('khaki', r'khaki'), ('moca', r'moca')]

def colors_of(name):
    n = name.lower()
    return [c for c, rx in COLOR_RX if re.search(rx, n)]

def base_of(name):
    n = name.lower()
    n = re.sub(r'\b(black|grey|gray|brown|white|blue|orange|red|green|yellow|khaki|moca)\b', '', n)
    n = re.sub(r'(brown|gr)$', '', n.replace('+', ' ').strip())
    return re.sub(r'[^a-z0-9]', '', n)

DISPLAY = {'1047agr': '1047A Grey', '6909Agr': '6909A Grey', '9021Abrown': '9021A Brown', '6909#': '6909'}

def pretty(name):
    if name in DISPLAY: return DISPLAY[name]
    # "A310 brown+grey" -> "A310 Brown+Grey"
    fix = lambda w: w if re.search(r'\d', w) else '+'.join(p[:1].upper() + p[1:].lower() for p in w.split('+'))
    return ' '.join(fix(w) for w in name.split())

def category(price):
    if price is None: return 'office'
    if price >= 60000: return 'exec'
    if price >= 20000: return 'office'
    return 'visitor'

def fmt(p):
    return f'{p:,}'.replace(',', ' ') if p else ''

caps = json.load(open(os.path.join(ROOT, 'data-captions.json')))
def description(folder):
    c = caps.get(folder)
    if not c: return None, None
    parts = [p.strip() for p in c.split('\n\n')]
    body = parts[1] if len(parts) > 1 else None
    feat = None
    m = re.search(r'Առանձնահատկություն՝\s*(.+)', c)
    if m: feat = m.group(1).strip()
    return body, feat

items = []
for it in json.load(open(os.path.join(ROOT, 'assets/items.json'))):
    if it['name'] in HIDE: continue
    d = os.path.join(OUT, 'img', it['slug'])
    if not os.path.exists(os.path.join(d, 'semi.jpg')): continue
    it['title'] = pretty(it['name'])
    it['colors'] = colors_of(it['name'])
    it['base'] = base_of(it['name'])
    it['cat'] = category(it['price'])
    it['desc'], it['feat'] = description(it['folder'])
    st = it['stock']
    it['status'] = 'sold' if it['sold'] else ('ask' if st is None else ('few' if st <= 5 else 'instock'))
    items.append(it)
ORDER = {'instock': 0, 'few': 1, 'ask': 2, 'sold': 3}
items.sort(key=lambda i: (ORDER[i['status']] == 3, i['title'].lower()))
BY_SLUG = {i['slug']: i for i in items}
FEATURED = [s for s in ['a310-white-blue', 'a303-1-red', 'a301-brown', '6909a', '2825', '821b-grey', '1001', 'j6960a'] if s in BY_SLUG]

# ---------------------------------------------------------------- html helpers
e = html.escape
ICON = {
 'wa': '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2Zm0 18.2a8.2 8.2 0 0 1-4.2-1.2l-.3-.2-3 .8.8-2.9-.2-.3A8.2 8.2 0 1 1 12 20.2Zm4.5-6.1c-.2-.1-1.5-.7-1.7-.8-.2-.1-.4-.1-.6.1l-.8 1c-.1.2-.3.2-.5.1a6.7 6.7 0 0 1-3.3-2.9c-.3-.4.2-.4.7-1.3.1-.2 0-.3 0-.4l-.8-1.8c-.2-.5-.4-.4-.6-.4h-.5a1 1 0 0 0-.7.3 3 3 0 0 0-.9 2.2 5.1 5.1 0 0 0 1.1 2.7 11.6 11.6 0 0 0 4.4 3.9c1.6.7 2.3.8 3.1.6.5-.1 1.5-.6 1.7-1.2.2-.6.2-1.1.1-1.2l-.5-.2Z"/></svg>',
 'phone': '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M6.6 10.8a15.1 15.1 0 0 0 6.6 6.6l2.2-2.2a1 1 0 0 1 1-.2 11.4 11.4 0 0 0 3.6.6 1 1 0 0 1 1 1V20a1 1 0 0 1-1 1A17 17 0 0 1 3 4a1 1 0 0 1 1-1h3.5a1 1 0 0 1 1 1 11.4 11.4 0 0 0 .6 3.6 1 1 0 0 1-.3 1l-2.2 2.2Z"/></svg>',
 'ig': '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 7a5 5 0 1 0 0 10 5 5 0 0 0 0-10Zm0 8.2a3.2 3.2 0 1 1 0-6.4 3.2 3.2 0 0 1 0 6.4ZM17.3 5.5a1.2 1.2 0 1 0 0 2.4 1.2 1.2 0 0 0 0-2.4ZM21.9 7.1c-.1-1.6-.4-3-1.6-4.2S17.7 1.3 16.1 1.2C14.5 1.1 9.5 1.1 7.9 1.2 6.3 1.3 4.9 1.6 3.7 2.8S2.1 5.5 2 7.1c-.1 1.6-.1 6.6 0 8.2.1 1.6.4 3 1.6 4.2s2.6 1.5 4.2 1.6c1.6.1 6.6.1 8.2 0 1.6-.1 3-.4 4.2-1.6s1.5-2.6 1.6-4.2c.1-1.6.1-6.6 0-8.2Zm-2.2 10a3.2 3.2 0 0 1-1.8 1.8c-1.3.5-4.3.4-5.7.4s-4.4.1-5.7-.4a3.2 3.2 0 0 1-1.8-1.8c-.5-1.3-.4-4.3-.4-5.7s-.1-4.4.4-5.7A3.2 3.2 0 0 1 6.5 3.9c1.3-.5 4.3-.4 5.7-.4s4.4-.1 5.7.4a3.2 3.2 0 0 1 1.8 1.8c.5 1.3.4 4.3.4 5.7s.1 4.4-.4 5.7Z"/></svg>',
 'fb': '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M13.5 21v-7.5H16l.4-3h-2.9V8.6c0-.9.3-1.5 1.5-1.5h1.6V4.4a21 21 0 0 0-2.3-.1c-2.3 0-3.9 1.4-3.9 4v2.2H8v3h2.4V21h3.1Z"/></svg>',
 'mail': '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M3 5h18a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1Zm9 7.6L4 7.3V17h16V7.3l-8 5.3Zm0-2.1L19 7H5l7 3.5Z"/></svg>',
 'dl': '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M11 3h2v9.2l3.3-3.3 1.4 1.4L12 16l-5.7-5.7 1.4-1.4L11 12.2V3ZM4 18h16v2H4v-2Z"/></svg>',
}

def wa_link(text=None):
    from urllib.parse import quote
    return f'https://wa.me/{PHONE_RAW}' + (f'?text={quote(text)}' if text else '')

def url(lang, path=''):
    return f'{PREFIX[lang]}/{path}'

def status_badge(t, s):
    return f'<span class="badge b-{s}">{e(t[s])}</span>'

def card(t, lang, it):
    cls = ' is-sold' if it['status'] == 'sold' else ''
    price = f'{fmt(it["price"])} {t["amd"]}' if it['price'] else ''
    return (f'<a class="card{cls}" href="{url(lang, "chair/" + it["slug"] + "/")}" data-slug="{it["slug"]}" data-cat="{it["cat"]}" data-colors="{" ".join(it["colors"])}" '
            f'data-price="{it["price"] or 0}" data-status="{it["status"]}" data-name="{e(it["title"].lower())}">'
            f'<div class="card-img"><img loading="lazy" src="/img/{it["slug"]}/semi-sm.jpg" alt="{e(it["title"])}" width="480" height="600">'
            f'<img loading="lazy" class="alt" src="/img/{it["slug"]}/int-semi-sm.jpg" alt="" width="480" height="600" aria-hidden="true">'
            f'{status_badge(t, it["status"]) if it["status"] in ("few", "sold") else ""}</div>'
            f'<div class="card-body"><h3>{e(it["title"])}</h3><p class="price">{price}</p></div></a>')

def page(lang, path, title, desc, body, active='', og_img='/og.jpg'):
    t = T[lang]
    alts = ''.join(f'<link rel="alternate" hreflang="{T[l]["htmllang"]}" href="{SITE}{url(l, path)}">' for l in LANGS)
    nav = ''.join(f'<a href="{url(lang, p)}"{" aria-current=page" if active == k else ""}>{e(t[k])}</a>'
                  for k, p in [('nav_home', ''), ('nav_cat', 'catalog/'), ('nav_b2b', 'b2b/'), ('nav_contact', 'contact/')])
    langs = ''.join(f'<a href="{url(l, path)}" lang="{T[l]["htmllang"]}"{" class=on" if l == lang else ""}>{T[l]["label"]}</a>' for l in LANGS)
    year = datetime.date.today().year
    return f'''<!doctype html>
<html lang="{t['htmllang']}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{SITE}{url(lang, path)}">{alts}
<meta property="og:type" content="website"><meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}">
<meta property="og:image" content="{SITE}{og_img}"><meta property="og:url" content="{SITE}{url(lang, path)}">
<meta name="theme-color" content="#0e0e0e">
<link rel="icon" href="/favicon.png">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@500;600;700&family=Noto+Sans+Armenian:wght@400;500;600;700&family=Noto+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/style.css">
</head>
<body class="lang-{lang}">
<header class="top">
 <div class="wrap top-in">
  <a class="logo" href="{url(lang)}"><img src="/logo-light.png" alt="Magnetix Furniture" width="178" height="60"></a>
  <nav class="menu" id="menu">{nav}</nav>
  <div class="top-r"><div class="langs">{langs}</div>
   <a class="top-call" href="tel:+{PHONE_RAW}">{ICON['phone']}<span>{PHONE}</span></a>
   <button class="burger" aria-label="Menu" aria-controls="menu" aria-expanded="false"><span></span><span></span><span></span></button></div>
 </div>
</header>
<main>
{body}
</main>
<footer class="foot">
 <div class="wrap foot-in">
  <div><img src="/logo-light.png" alt="Magnetix Furniture" width="150" height="51"><p>{e(t['foot_about'])}</p></div>
  <div><h4>{e(t['nav_contact'])}</h4><p><a href="tel:+{PHONE_RAW}">{PHONE}</a><br><a href="mailto:{EMAIL}">{EMAIL}</a><br>{e(t['city'])}</p></div>
  <div><h4>{e(t['social'])}</h4><p class="soc"><a href="{IG}" aria-label="Instagram">{ICON['ig']}</a><a href="{FB}" aria-label="Facebook">{ICON['fb']}</a><a href="{wa_link()}" aria-label="WhatsApp">{ICON['wa']}</a></p></div>
 </div>
 <div class="wrap copy">© {year} Magnetix Furniture. {e(t['rights'])}</div>
</footer>
<a class="fab" href="{wa_link()}" aria-label="WhatsApp">{ICON['wa']}</a>
<script>window.MX_SHEET={json.dumps(SHEET_CSV)};window.MX_T={json.dumps({k: t[k] for k in ('instock','few','ask','sold','amd')}, ensure_ascii=False)};</script>
<script src="/site.js" defer></script>
</body>
</html>'''

def write(path, content):
    p = os.path.join(OUT, path.lstrip('/'))
    if p.endswith('/'): p += 'index.html'
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, 'w', encoding='utf-8').write(content)

# ---------------------------------------------------------------- pages
def home(lang):
    t = T[lang]
    feat = ''.join(card(t, lang, BY_SLUG[s]) for s in FEATURED)
    hero_imgs = ''.join(f'<img src="/img/{s}/int-semi.jpg" alt="" class="h{k}">' for k, s in enumerate(['a310-white-blue', '6909a', 'a301-brown']) if s in BY_SLUG)
    why = ''.join(f'<div class="why-i"><span class="num">0{k+1}</span><h3>{e(h)}</h3><p>{e(p)}</p></div>' for k, (h, p) in enumerate(t['why']))
    n = len([i for i in items if i['status'] != 'sold'])
    body = f'''
<section class="hero">
 <div class="wrap hero-in">
  <div class="hero-txt">
   <p class="kicker">{e(t['hero_kicker'])}</p>
   <h1>{e(t['hero_h'])}</h1>
   <p class="lead">{e(t['hero_p'])}</p>
   <div class="btns"><a class="btn gold" href="{url(lang, 'catalog/')}">{e(t['cta_cat'])}</a>
   <a class="btn ghost" href="{wa_link()}">{ICON['wa']}{e(t['cta_wa'])}</a></div>
   <p class="hero-stat"><b>{n}+</b> {e(t['models_n'])} · <a href="tel:+{PHONE_RAW}">{PHONE}</a></p>
  </div>
  <div class="hero-art">{hero_imgs}</div>
 </div>
</section>
<section class="sec"><div class="wrap">
 <div class="sec-h"><h2>{e(t['feat_h'])}</h2><a class="more" href="{url(lang, 'catalog/')}">{e(t['all_models'])} →</a></div>
 <div class="grid">{feat}</div>
</div></section>
<section class="sec dark"><div class="wrap">
 <h2>{e(t['why_h'])}</h2>
 <div class="why">{why}</div>
</div></section>
<section class="sec"><div class="wrap band">
 <div><h2>{e(t['b2b_h'])}</h2><p>{e(t['b2b_p'])}</p></div>
 <div class="btns"><a class="btn gold" href="{url(lang, 'b2b/')}">{e(t['nav_b2b'])}</a><a class="btn line" href="/magnetix-inventory.pdf" download>{ICON['dl']}{e(t['dl_pdf'])}</a></div>
</div></section>'''
    write(url(lang), page(lang, '', t['title'], t['desc'], body, 'nav_home', og_img='/img/a310-white-blue/int-semi.jpg'))

def catalog(lang):
    t = T[lang]
    cols = sorted({c for i in items for c in i['colors']}, key=lambda c: t['colors'][c])
    copts = ''.join(f'<option value="{c}">{e(t["colors"][c])}</option>' for c in cols)
    chips = ''.join(f'<button class="chip{" on" if k == "all" else ""}" data-cat="{k}">{e(t[l])}</button>'
                    for k, l in [('all', 'f_all'), ('exec', 'f_exec'), ('office', 'f_office'), ('visitor', 'f_visitor')])
    cards = ''.join(card(t, lang, i) for i in items)
    body = f'''
<section class="page-h"><div class="wrap"><h1>{e(t['cat_h'])}</h1><p>{e(t['cat_p'])}</p></div></section>
<section class="sec tight"><div class="wrap">
 <div class="filters">
  <div class="chips">{chips}</div>
  <div class="frow">
   <input type="search" id="q" placeholder="{e(t['f_search'])}" aria-label="{e(t['f_search'])}">
   <select id="color" aria-label="{e(t['f_color'])}"><option value="">{e(t['f_anycolor'])}</option>{copts}</select>
   <select id="sort" aria-label="{e(t['f_sort'])}"><option value="">{e(t['s_def'])}</option><option value="up">{e(t['s_up'])}</option><option value="down">{e(t['s_down'])}</option></select>
   <label class="tog"><input type="checkbox" id="instock"> {e(t['f_instock'])}</label>
  </div>
  <p class="count"><span id="n">{len(items)}</span> {e(t['models_n'])}</p>
 </div>
 <div class="grid" id="grid">{cards}</div>
 <p class="empty" id="empty" hidden>{e(t['none_found'])}</p>
</div></section>'''
    write(url(lang, 'catalog/'), page(lang, 'catalog/', f'{t["cat_h"]} · Magnetix Furniture', t['desc'], body, 'nav_cat'))

def chair(lang, it):
    t = T[lang]
    shots = [('semi', 'w'), ('front', 'w'), ('side', 'w'), ('int-semi', 'i'), ('int-front', 'i'), ('int-side', 'i')]
    shots = [(s, k) for s, k in shots if os.path.exists(os.path.join(OUT, 'img', it['slug'], s + '.jpg'))]
    main = ''.join(f'<img src="/img/{it["slug"]}/{s}.jpg" alt="{e(it["title"])}" width="960" height="1200"{" loading=lazy" if n else ""}>' for n, (s, k) in enumerate(shots))
    thumbs = ''.join(f'<button class="th{" on" if n == 0 else ""}" data-src="/img/{it["slug"]}/{s}.jpg" aria-label="{n+1}"><img loading="lazy" src="/img/{it["slug"]}/{s}.jpg" alt="" width="96" height="120"></button>' for n, (s, k) in enumerate(shots))
    colors = ', '.join(t['colors'][c] for c in it['colors']) or '—'
    catname = {'exec': t['f_exec'], 'office': t['f_office'], 'visitor': t['f_visitor']}[it['cat']]
    price = f'{fmt(it["price"])} {t["amd"]}' if it['price'] else '—'
    msg = t['wa_msg'].format(m=it['title'], p=fmt(it['price']) if it['price'] else '—')
    desc = f'<p class="desc">{e(it["desc"])}</p>' if lang == 'hy' and it['desc'] else ''
    feat = f'<tr><th>{"Առանձնահատկություն" if lang=="hy" else ""}</th><td>{e(it["feat"])}</td></tr>' if lang == 'hy' and it['feat'] else ''
    sibs = [i for i in items if i['base'] == it['base'] and i is not it]
    simi = [i for i in items if i['cat'] == it['cat'] and i is not it and i not in sibs and i['status'] != 'sold']
    simi = sorted(simi, key=lambda i: abs((i['price'] or 0) - (it['price'] or 0)))[:4]
    sib_html = f'<div class="sibs"><h4>{e(t["other_colors"])}</h4><div>' + ''.join(f'<a href="{url(lang, "chair/" + s["slug"] + "/")}" title="{e(s["title"])}"><img src="/img/{s["slug"]}/semi-sm.jpg" alt="{e(s["title"])}" width="72" height="90"></a>' for s in sibs) + '</div></div>' if sibs else ''
    body = f'''
<section class="sec chair"><div class="wrap">
 <p class="crumbs"><a href="{url(lang, 'catalog/')}">← {e(t['back'])}</a></p>
 <div class="chair-in">
  <div class="gallery"><div class="main"><div class="slides" id="slides">{main}</div><button class="arr prev" aria-label="Previous">‹</button><button class="arr next" aria-label="Next">›</button><span class="dots" id="dots"></span></div><div class="thumbs">{thumbs}</div></div>
  <div class="info">
   <p class="kicker">{e(catname)}</p>
   <h1>{e(it['title'])}</h1>
   <p class="big-price" data-slug="{it['slug']}">{price}</p>
   {status_badge(t, it['status'])}
   {desc}
   <table class="spec"><tr><th>{e(t['model'])}</th><td>{e(it['title'])}</td></tr><tr><th>{e(t['color'])}</th><td>{e(colors)}</td></tr>{feat}
   <tr><th>{e(t['category'])}</th><td>{e(catname)}</td></tr><tr><th>{e(t['availability'])}</th><td id="avail">{e(t[it['status']])}</td></tr></table>
   <div class="btns col"><a class="btn wa" href="{wa_link(msg)}">{ICON['wa']}{e(t['order_wa'])}</a>
   <div class="btns"><a class="btn line" href="tel:+{PHONE_RAW}">{ICON['phone']}{e(t['order_call'])}</a><a class="btn line" href="{IG}">{ICON['ig']}{e(t['order_ig'])}</a></div></div>
   <p class="bulk">📦 {e(t['bulk_note'])} <a href="{url(lang, 'b2b/')}">{e(t['bulk_link'])} →</a></p>
   {sib_html}
  </div>
 </div>
</div></section>
{f'<section class="sec alt"><div class="wrap"><h2>{e(t["similar"])}</h2><div class="grid">' + ''.join(card(t, lang, s) for s in simi) + '</div></div></section>' if simi else ''}'''
    ttl = f'{it["title"]} · {price} · Magnetix Furniture'
    d = (it['desc'] if lang == 'hy' and it['desc'] else f'{it["title"]}: {price}. {t["desc"]}')[:300]
    write(url(lang, f'chair/{it["slug"]}/'), page(lang, f'chair/{it["slug"]}/', ttl, d, body, 'nav_cat', og_img=f'/img/{it["slug"]}/semi.jpg'))

def b2b(lang):
    t = T[lang]
    pts = ''.join(f'<div class="why-i"><span class="num">0{k+1}</span><h3>{e(h)}</h3><p>{e(p)}</p></div>' for k, (h, p) in enumerate(t['b2b_points']))
    steps = ''.join(f'<li><span>{k+1}</span>{e(s)}</li>' for k, s in enumerate(t['steps']))
    body = f'''
<section class="page-h dark"><div class="wrap"><h1>{e(t['b2b_h'])}</h1><p>{e(t['b2b_p'])}</p>
 <div class="btns"><a class="btn gold" href="/magnetix-inventory.pdf" download>{ICON['dl']}{e(t['dl_pdf'])}</a><a class="btn ghost" href="{wa_link()}">{ICON['wa']}{e(t['b2b_cta'])}</a></div></div></section>
<section class="sec"><div class="wrap"><div class="why light">{pts}</div></div></section>
<section class="sec alt"><div class="wrap narrow"><h2>{e(t['steps_h'])}</h2><ol class="steps">{steps}</ol>
 <div class="btns"><a class="btn wa" href="{wa_link()}">{ICON['wa']}WhatsApp</a><a class="btn line" href="mailto:{EMAIL}">{ICON['mail']}{EMAIL}</a><a class="btn line" href="tel:+{PHONE_RAW}">{ICON['phone']}{PHONE}</a></div></div></section>'''
    write(url(lang, 'b2b/'), page(lang, 'b2b/', f'{t["nav_b2b"]} · Magnetix Furniture', t['b2b_p'], body, 'nav_b2b'))

def contact(lang):
    t = T[lang]
    body = f'''
<section class="page-h"><div class="wrap"><h1>{e(t['contact_h'])}</h1><p>{e(t['contact_p'])}</p></div></section>
<section class="sec tight"><div class="wrap contact">
 <a class="cbox" href="tel:+{PHONE_RAW}">{ICON['phone']}<span>{e(t['phone'])}</span><b>{PHONE}</b></a>
 <a class="cbox" href="{wa_link()}">{ICON['wa']}<span>WhatsApp</span><b>{PHONE}</b></a>
 <a class="cbox" href="mailto:{EMAIL}">{ICON['mail']}<span>{e(t['email'])}</span><b>{EMAIL}</b></a>
 <a class="cbox" href="{IG}">{ICON['ig']}<span>Instagram</span><b>@magnetix.am</b></a>
 <a class="cbox" href="{FB}">{ICON['fb']}<span>Facebook</span><b>Magnetix Furniture</b></a>
</div><div class="wrap"><p class="city">📍 {e(t['city'])}</p></div></section>'''
    write(url(lang, 'contact/'), page(lang, 'contact/', f'{t["contact_h"]} · Magnetix Furniture', t['contact_p'], body, 'nav_contact'))

# ---------------------------------------------------------------- build
def main():
    # photos live in public/img (source of truth); everything else is regenerated
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        if f == 'img': continue
        p = os.path.join(OUT, f); shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
    for src, dst in [('static/style.css', 'style.css'), ('static/site.js', 'site.js'), ('assets/magnetix-inventory.pdf', 'magnetix-inventory.pdf')]:
        shutil.copy(os.path.join(ROOT, src), os.path.join(OUT, dst))
    from PIL import Image
    Image.open(os.path.join(ROOT, 'assets/gold-white-magnetix-logo.png')).resize((356, 120), Image.LANCZOS).save(os.path.join(OUT, 'logo-light.png'), optimize=True)
    ic = Image.open(os.path.join(ROOT, 'assets/gold-white-magnetix-logo.png')).crop((0, 0, 304, 304)).resize((128, 128), Image.LANCZOS)
    bg = Image.new('RGBA', (128, 128), (14, 14, 14, 255)); bg.alpha_composite(ic); bg.save(os.path.join(OUT, 'favicon.png'))
    for lang in LANGS:
        home(lang); catalog(lang); b2b(lang); contact(lang)
        for it in items: chair(lang, it)
    urls = [url(l, p) for l in LANGS for p in ['', 'catalog/', 'b2b/', 'contact/'] + [f'chair/{i["slug"]}/' for i in items]]
    write('/sitemap.xml', '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + ''.join(f'<url><loc>{SITE}{u}</loc></url>' for u in urls) + '</urlset>')
    write('/robots.txt', f'User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\n')
    write('/404.html', page('hy', '', 'Magnetix Furniture', T['hy']['desc'], f'<section class="page-h"><div class="wrap"><h1>404</h1><p><a class="btn gold" href="/catalog/">{T["hy"]["cta_cat"]}</a></p></div></section>'))
    print(f'{len(items)} chairs, {len(urls)} pages -> public/')

if __name__ == '__main__':
    main()
