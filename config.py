import os
from dotenv import load_dotenv

load_dotenv()

# Bot Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN', '8292296245:AAHhFkMClAOsFAlCOoNiqwzGTfnEI266xJQ')

# Tripay Configuration
TRIPAY_API_KEY = os.getenv('TRIPAY_API_KEY', 'YOUR_TRIPAY_API_KEY')
TRIPAY_PRIVATE_KEY = os.getenv('TRIPAY_PRIVATE_KEY', 'YOUR_TRIPAY_PRIVATE_KEY')
TRIPAY_MERCHANT_CODE = os.getenv('TRIPAY_MERCHANT_CODE', 'YOUR_MERCHANT_CODE')
TRIPAY_BASE_URL = 'https://tripay.co.id/api-sandbox'  # Use https://tripay.co.id/api for production

# Database Configuration
DATABASE_PATH = 'bot_database.db'

# Bot Settings
MIN_TOPUP_AMOUNT = 10000  # Minimum top-up amount in IDR
ADMIN_USER_IDS = [int(x) for x in os.getenv('ADMIN_USER_IDS', '8459142797').split(',')]  # Add admin user IDs here

# Webhook Configuration
WEBHOOK_URL = os.getenv('WEBHOOK_URL', 'https://your-domain.com/webhook')
WEBHOOK_PORT = int(os.getenv('WEBHOOK_PORT', 8080)) 