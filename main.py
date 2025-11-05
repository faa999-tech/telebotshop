import asyncio
import logging
import json
from datetime import datetime
from typing import Dict, Any

from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

import config
from database import db
from tripay import tripay

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Bot and dispatcher setup
bot = Bot(token=config.BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()

# Import admin handlers
from admin_handlers import admin_router, init_db_connection

# States for FSM
class TopUpStates(StatesGroup):
    waiting_amount = State()
    selecting_channel = State()

class PurchaseStates(StatesGroup):
    waiting_product_id = State()
    waiting_quantity = State()  # State baru untuk memilih jumlah
    waiting_confirmation = State()  # New state for confirmation

class EditStartStates(StatesGroup):
    waiting_text = State()

# Utility functions
def format_currency(amount: int) -> str:
    """Format amount to IDR currency"""
    return f"Rp {amount:,}".replace(',', '.')

def create_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Create main menu keyboard"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💰 Cek Saldo", callback_data="check_balance"),
        InlineKeyboardButton(text="💳 Top Up", callback_data="topup")
    )
    builder.row(
        InlineKeyboardButton(text="🛍️ Produk", callback_data="products"),
        InlineKeyboardButton(text="📊 Riwayat", callback_data="history")
    )
    builder.row(
        InlineKeyboardButton(text="👤 Profil", callback_data="profile")
    )
    return builder.as_markup()

async def ensure_user_exists(user: types.User) -> bool:
    """Ensure user exists in database and migrate balance if needed"""
    existing_user = await db.get_user(user.id)
    if not existing_user:
        success = await db.create_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name
        )
        # After creating, try to migrate balance from duplicate users
        migrated = await db.migrate_balance_to_current_user(user.id, user.username, user.first_name)
        if migrated:
            # Notify user about migration
            try:
                await user.send_message(
                    "⚠️ <b>Saldo Anda telah dipindahkan dari akun lama ke akun ini secara otomatis.</b>\n\n"
                    "Jika Anda merasa ada kesalahan, silakan hubungi admin.",
                    parse_mode="HTML"
                )
            except Exception:
                pass
        return success
    else:
        # If user already exists, still check for possible migration (in case username/first_name changed)
        migrated = await db.migrate_balance_to_current_user(user.id, user.username, user.first_name)
        if migrated:
            try:
                await user.send_message(
                    "⚠️ <b>Saldo Anda telah dipindahkan dari akun lama ke akun ini secara otomatis.</b>\n\n"
                    "Jika Anda merasa ada kesalahan, silakan hubungi admin.",
                    parse_mode="HTML"
                )
            except Exception:
                pass
    return True

# Command handlers
@router.message(Command("start"))
async def cmd_start(message: types.Message):
    """Handle /start command"""
    await ensure_user_exists(message.from_user)
    start_text = await db.get_setting('start_text')
    if not start_text:
        start_text = (
            "🤖 *Selamat datang di Toko Digital Bot!*\n\n"
            f"Halo {message.from_user.first_name}! 👋\n\n"
            "*Fitur yang tersedia:*\n"
            "💰 Cek Saldo - Lihat saldo terkini\n"
            "💳 Top Up - Isi saldo via Tripay\n"
            "🛍️ Produk - Lihat produk yang tersedia\n"
            "📊 Riwayat - Lihat riwayat transaksi\n\n"
            "*Perintah cepat:*\n"
            "/saldo - Cek saldo\n"
            "/topup - Top up saldo\n"
            "/produk - Lihat produk\n"
            "/beli [ID] - Beli produk\n"
            "/riwayat - Riwayat transaksi\n"
            "/profile - Lihat profil akun\n\n"
            "Pilih menu di bawah untuk memulai:"
        )
    await message.answer(
        start_text,
        reply_markup=create_main_menu_keyboard(),
        parse_mode="Markdown"
    )

@router.message(Command("saldo"))
async def cmd_balance(message: types.Message):
    """Handle /saldo command"""
    await ensure_user_exists(message.from_user)
    
    balance = await db.get_user_balance(message.from_user.id)
    
    text = f"💰 <b>Saldo Anda</b>\n\n"
    text += f"💳 Saldo saat ini: <b>{format_currency(balance)}</b>\n\n"
    
    if balance < config.MIN_TOPUP_AMOUNT:
        text += f"ℹ️ Saldo minimum untuk bertransaksi: {format_currency(config.MIN_TOPUP_AMOUNT)}\n"
        text += "Silakan top up saldo terlebih dahulu."
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="💳 Top Up", callback_data="topup"))
    keyboard.row(InlineKeyboardButton(text="🏠 Menu Utama", callback_data="main_menu"))
    
    await message.answer(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")

@router.message(Command("topup"))
async def cmd_topup(message: types.Message, state: FSMContext):
    """Handle /topup command"""
    await ensure_user_exists(message.from_user)
    
    text = f"💳 <b>Top Up Saldo</b>\n\n"
    text += f"Masukkan nominal yang ingin Anda top up.\n"
    text += f"Minimal top up: <b>{format_currency(config.MIN_TOPUP_AMOUNT)}</b>\n\n"
    text += f"Contoh: <code>50000</code> atau <code>100000</code>"
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="❌ Batal", callback_data="main_menu"))
    
    await message.answer(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
    await state.set_state(TopUpStates.waiting_amount)

@router.message(Command("produk"))
async def cmd_products(message: types.Message):
    """Handle /produk command"""
    await ensure_user_exists(message.from_user)
    await show_products(message)

@router.message(Command("beli"))
async def cmd_buy(message: types.Message, state: FSMContext):
    """Handle /beli command with quantity and confirmation"""
    await ensure_user_exists(message.from_user)
    command_args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    if not command_args:
        await message.answer(
            "❌ <b>Format salah!</b>\n\n"
            "Gunakan: <code>/beli [ID_PRODUK] [JUMLAH]</code>\n"
            "Contoh: <code>/beli 1 2</code>\n\n"
            "Ketik /produk untuk melihat daftar produk.",
            parse_mode="HTML"
        )
        return
    try:
        product_id = int(command_args[0])
        quantity = int(command_args[1]) if len(command_args) > 1 else 1
        if quantity < 1:
            await message.answer("❌ Jumlah minimal 1.", parse_mode="HTML")
            return
        product = await db.get_product(product_id)
        if not product or not product['is_active']:
            await message.answer("❌ <b>Produk tidak ditemukan atau tidak aktif!</b>", parse_mode="HTML")
            return
        available_stock = await db.get_available_stock_count(product_id)
        if available_stock == 0:
            await message.answer("❌ <b>Produk habis!</b>", parse_mode="HTML")
            return
        if quantity > available_stock:
            await message.answer(f"❌ Stok tidak cukup! Maksimal pembelian: <b>{available_stock}</b>", parse_mode="HTML")
            return
        user_balance = await db.get_user_balance(message.from_user.id)
        total_price = product['price'] * quantity
        sisa_saldo = user_balance - total_price
        if user_balance < total_price:
            await message.answer(
                f"❌ <b>Saldo tidak cukup!</b>\n\n"
                f"💰 Harga total: <b>{format_currency(total_price)}</b>\n"
                f"💳 Saldo Anda: <b>{format_currency(user_balance)}</b>\n"
                f"💸 Kurang: <b>{format_currency(total_price - user_balance)}</b>\n\n"
                "Silakan top up saldo terlebih dahulu.",
                parse_mode="HTML"
            )
            return
        # Save purchase info to FSM
        await state.update_data(
            product_id=product_id,
            quantity=quantity,
            total_price=total_price,
            sisa_saldo=sisa_saldo,
            product_name=product['name']
        )
        # Confirmation message
        text = f"Konfirmasi Pembelian:\n\n"
        text += f"🛍️ Produk: <b>{product['name']}</b>\n"
        text += f"🔢 Jumlah: <b>{quantity}</b>\n"
        text += f"💰 Total Harga: <b>{format_currency(total_price)}</b>\n"
        text += f"💳 Sisa Saldo Setelah Beli: <b>{format_currency(sisa_saldo)}</b>\n\n"
        text += "Lanjutkan pembelian?"
        keyboard = InlineKeyboardBuilder()
        keyboard.row(
            InlineKeyboardButton(text="✅ Konfirmasi", callback_data="confirm_purchase"),
            InlineKeyboardButton(text="❌ Batal", callback_data="cancel_purchase")
        )
        await message.answer(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
        await state.set_state(PurchaseStates.waiting_confirmation)
    except ValueError:
        await message.answer(
            "❌ <b>ID produk dan jumlah harus berupa angka!</b>\n\n"
            "Contoh: <code>/beli 1 2</code>",
            parse_mode="HTML"
        )

@router.message(Command("riwayat"))
async def cmd_history(message: types.Message):
    """Handle /riwayat command"""
    await ensure_user_exists(message.from_user)
    await show_transaction_history(message)

@router.message(Command("profile"))
async def cmd_profile(message: types.Message):
    """Handle /profile command"""
    await ensure_user_exists(message.from_user)
    
    # Extract user ID from command if provided (admin only)
    command_args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    
    # Check if user is admin
    is_admin = message.from_user.id in config.ADMIN_USER_IDS
    
    if command_args:
        # Admin trying to view another user's profile
        if not is_admin:
            await message.answer(
                "❌ <b>Akses Ditolak!</b>\n\n"
                "Hanya admin yang dapat melihat profil pengguna lain.\n"
                "Gunakan <code>/profile</code> untuk melihat profil Anda sendiri.",
                parse_mode="HTML"
            )
            return
        
        try:
            target_user_id = int(command_args[0])
            await show_user_profile(message, target_user_id, is_admin_view=True)
        except ValueError:
            await message.answer(
                "❌ <b>Format salah!</b>\n\n"
                "Gunakan: <code>/profile [USER_ID]</code>\n"
                "Contoh: <code>/profile 123456789</code>",
                parse_mode="HTML"
            )
    else:
        # User viewing their own profile
        await show_user_profile(message, message.from_user.id, is_admin_view=False)

@router.message(Command("editstart"))
async def cmd_editstart(message: types.Message, state: FSMContext):
    if message.from_user.id not in config.ADMIN_USER_IDS:
        await message.answer("❌ Perintah ini hanya untuk admin.")
        return
    await message.answer("Kirimkan teks baru untuk /start (Markdown didukung):")
    await state.set_state(EditStartStates.waiting_text)

@router.message(StateFilter(EditStartStates.waiting_text))
async def process_editstart_text(message: types.Message, state: FSMContext):
    if message.from_user.id not in config.ADMIN_USER_IDS:
        await message.answer("❌ Perintah ini hanya untuk admin.")
        await state.clear()
        return
    new_text = message.text
    await db.set_setting('start_text', new_text)
    await message.answer("✅ Teks /start berhasil diubah!")
    await state.clear()

# Callback query handlers
@router.callback_query(F.data == "main_menu")
async def cb_main_menu(callback: CallbackQuery):
    """Handle main menu callback"""
    await callback.message.edit_text(
        "🏠 <b>Menu Utama</b>\n\nPilih menu yang ingin Anda akses:",
        reply_markup=create_main_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "check_balance")
async def cb_check_balance(callback: CallbackQuery):
    """Handle check balance callback"""
    balance = await db.get_user_balance(callback.from_user.id)
    
    text = f"💰 <b>Saldo Anda</b>\n\n"
    text += f"💳 Saldo saat ini: <b>{format_currency(balance)}</b>"
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="💳 Top Up", callback_data="topup"))
    keyboard.row(InlineKeyboardButton(text="🏠 Menu Utama", callback_data="main_menu"))
    
    await callback.message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "topup")
async def cb_topup(callback: CallbackQuery, state: FSMContext):
    """Handle topup callback"""
    text = f"💳 <b>Top Up Saldo</b>\n\n"
    text += f"Masukkan nominal yang ingin Anda top up.\n"
    text += f"Minimal top up: <b>{format_currency(config.MIN_TOPUP_AMOUNT)}</b>\n\n"
    text += f"Contoh: <code>50000</code> atau <code>100000</code>"
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="❌ Batal", callback_data="main_menu"))
    
    await callback.message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
    await state.set_state(TopUpStates.waiting_amount)
    await callback.answer()

@router.callback_query(F.data == "products")
async def cb_products(callback: CallbackQuery):
    """Handle products callback"""
    await show_products(callback.message, is_callback=True)
    await callback.answer()

@router.callback_query(F.data == "history")
async def cb_history(callback: CallbackQuery):
    """Handle history callback"""
    await show_transaction_history(callback.message, is_callback=True)
    await callback.answer()

@router.callback_query(F.data == "profile")
async def cb_profile(callback: CallbackQuery):
    """Handle profile callback"""
    await show_user_profile(callback.message, callback.from_user.id, is_admin_view=False)
    await callback.answer()

@router.callback_query(F.data.startswith("buy_"))
async def cb_buy_product(callback: CallbackQuery, state: FSMContext):
    """Handle buy product callback, now with quantity selection"""
    product_id = int(callback.data.split("_")[1])
    product = await db.get_product(product_id)
    if not product or not product['is_active']:
        await callback.message.edit_text("❌ <b>Produk tidak ditemukan atau tidak aktif!</b>", parse_mode="HTML")
        await callback.answer()
        return
    available_stock = await db.get_available_stock_count(product_id)
    if available_stock == 0:
        await callback.message.edit_text("❌ <b>Produk habis!</b>", parse_mode="HTML")
        await callback.answer()
        return
    # Simpan product_id di state
    await state.update_data(product_id=product_id, max_stock=available_stock, product_name=product['name'], price=product['price'])
    # Tampilkan pilihan jumlah (1-5 atau maksimal stok)
    max_qty = min(5, available_stock)
    keyboard = InlineKeyboardBuilder()
    for qty in range(1, max_qty+1):
        keyboard.row(InlineKeyboardButton(text=f"{qty}", callback_data=f"choose_qty_{qty}"))
    keyboard.row(InlineKeyboardButton(text="❌ Batal", callback_data="cancel_purchase"))
    text = f"<b>Pilih jumlah unit untuk {product['name']}:</b>\n\nStok tersedia: <b>{available_stock}</b>\nHarga per unit: <b>{format_currency(product['price'])}</b>"
    await callback.message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
    await state.set_state(PurchaseStates.waiting_quantity)
    await callback.answer()

@router.callback_query(F.data.startswith("sold_out_"))
async def cb_sold_out(callback: CallbackQuery):
    """Handle sold out product callback"""
    product_id = int(callback.data.split("_")[2])
    
    product = await db.get_product(product_id)
    if product:
        text = f"❌ <b>Produk Habis!</b>\n\n"
        text += f"🛍️ Produk: <b>{product['name']}</b>\n"
        text += f"💰 Harga: <b>{format_currency(product['price'])}</b>\n\n"
        text += f"Produk ini sedang habis. Silakan pilih produk lain atau hubungi admin."
        
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(text="🛍️ Produk Lain", callback_data="products"))
        keyboard.row(InlineKeyboardButton(text="🏠 Menu Utama", callback_data="main_menu"))
        
        await callback.message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
    
    await callback.answer("Produk sedang habis!", show_alert=True)

# Channel selection callbacks
@router.callback_query(F.data.startswith("select_channel_"))
async def cb_select_channel(callback: types.CallbackQuery, state: FSMContext):
    """Handle channel selection for top-up"""
    channel_code = callback.data.split("select_channel_")[1]
    
    data = await state.get_data()
    amount = data.get('amount')
    
    if not amount:
        await callback.answer("❌ Data tidak ditemukan, silakan mulai ulang!", show_alert=True)
        await state.clear()
        return
    
    # Create Tripay transaction with selected channel
    await callback.message.edit_text("⏳ Sedang membuat invoice pembayaran...", parse_mode="HTML")
    
    transaction_data = await tripay.create_transaction(amount, callback.from_user.id, method=channel_code)
    
    if not transaction_data:
        text = "❌ <b>Gagal membuat invoice!</b>\n\nSilakan coba lagi dalam beberapa saat."
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(text="🔄 Coba Lagi", callback_data="topup"))
        keyboard.row(InlineKeyboardButton(text="🏠 Menu Utama", callback_data="main_menu"))
        
        await callback.message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
        await state.clear()
        await callback.answer()
        return
    
    # Save transaction to database
    await db.create_tripay_transaction(
        reference=transaction_data["reference"],
        user_id=callback.from_user.id,
        amount=amount,
        checkout_url=transaction_data["checkout_url"]
    )
    
    # Get channel info for display
    channel_info = await tripay.get_channel_info(channel_code)
    channel_name = channel_info.get("name", channel_code) if channel_info else channel_code
    
    # Send payment info
    text = f"💳 <b>Invoice Pembayaran</b>\n\n"
    text += f"🏦 Channel: <b>{channel_name}</b> ({channel_code})\n"
    text += f"📋 Reference: <code>{transaction_data['reference']}</code>\n"
    text += f"💰 Nominal: <b>{format_currency(amount)}</b>\n"
    text += f"⏰ Berlaku hingga: <b>{datetime.fromtimestamp(transaction_data['expired_time']).strftime('%d/%m/%Y %H:%M')}</b>\n\n"
    text += f"Klik tombol di bawah untuk melakukan pembayaran:"
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="💳 Bayar Sekarang", url=transaction_data["checkout_url"]))
    keyboard.row(InlineKeyboardButton(text="🏠 Menu Utama", callback_data="main_menu"))
    
    await callback.message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
    await state.clear()
    await callback.answer()

@router.callback_query(F.data == "use_default_channel")
async def cb_use_default_channel(callback: types.CallbackQuery, state: FSMContext):
    """Use default channel for top-up"""
    data = await state.get_data()
    amount = data.get('amount')
    
    if not amount:
        await callback.answer("❌ Data tidak ditemukan, silakan mulai ulang!", show_alert=True)
        await state.clear()
        return
    
    # Get default channel
    default_channel = await db.get_default_channel()
    
    # Create Tripay transaction with default channel
    await callback.message.edit_text("⏳ Sedang membuat invoice pembayaran...", parse_mode="HTML")
    
    transaction_data = await tripay.create_transaction(amount, callback.from_user.id, method=default_channel)
    
    if not transaction_data:
        text = "❌ <b>Gagal membuat invoice!</b>\n\nSilakan coba lagi dalam beberapa saat."
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(text="🔄 Coba Lagi", callback_data="topup"))
        keyboard.row(InlineKeyboardButton(text="🏠 Menu Utama", callback_data="main_menu"))
        
        await callback.message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
        await state.clear()
        await callback.answer()
        return
    
    # Save transaction to database
    await db.create_tripay_transaction(
        reference=transaction_data["reference"],
        user_id=callback.from_user.id,
        amount=amount,
        checkout_url=transaction_data["checkout_url"]
    )
    
    # Get channel info for display
    channel_info = await tripay.get_channel_info(default_channel)
    channel_name = channel_info.get("name", default_channel) if channel_info else default_channel
    
    # Send payment info
    text = f"💳 <b>Invoice Pembayaran</b>\n\n"
    text += f"🏦 Channel: <b>{channel_name}</b> (Default)\n"
    text += f"📋 Reference: <code>{transaction_data['reference']}</code>\n"
    text += f"💰 Nominal: <b>{format_currency(amount)}</b>\n"
    text += f"⏰ Berlaku hingga: <b>{datetime.fromtimestamp(transaction_data['expired_time']).strftime('%d/%m/%Y %H:%M')}</b>\n\n"
    text += f"Klik tombol di bawah untuk melakukan pembayaran:"
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="💳 Bayar Sekarang", url=transaction_data["checkout_url"]))
    keyboard.row(InlineKeyboardButton(text="🏠 Menu Utama", callback_data="main_menu"))
    
    await callback.message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
    await state.clear()
    await callback.answer()

# State handlers
@router.message(StateFilter(TopUpStates.waiting_amount))
async def process_topup_amount(message: types.Message, state: FSMContext):
    """Process top-up amount input"""
    try:
        amount = int(message.text.replace(".", "").replace(",", ""))
        
        if amount < config.MIN_TOPUP_AMOUNT:
            await message.answer(
                f"❌ <b>Nominal terlalu kecil!</b>\n\n"
                f"Minimal top up: <b>{format_currency(config.MIN_TOPUP_AMOUNT)}</b>",
                parse_mode="HTML"
            )
            return
        
        # Store amount and show channel selection
        await state.update_data(amount=amount)
        await show_channel_selection(message, state)
        
    except ValueError:
        await message.answer(
            "❌ <b>Format nominal salah!</b>\n\n"
            "Masukkan hanya angka tanpa mata uang.\n"
            "Contoh: <code>50000</code>",
            parse_mode="HTML"
        )

# Helper functions
async def show_products(message: types.Message, is_callback: bool = False):
    """Show available products"""
    products = await db.get_products()
    
    if not products:
        text = "❌ <b>Tidak ada produk tersedia</b>\n\nSilakan kembali lagi nanti."
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(text="🏠 Menu Utama", callback_data="main_menu"))
        
        if is_callback:
            await message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
        else:
            await message.answer(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
        return
    
    text = "🛍️ <b>Produk Tersedia</b>\n\n"
    
    keyboard = InlineKeyboardBuilder()
    
    for product in products:
        # Get actual stock count from stock_units
        try:
            import json
            stock_units = json.loads(product.get('stock_units', '[]'))
            stock_count = len(stock_units)
            stock_text = f"({stock_count} tersisa)" if stock_count > 0 else "(Habis)"
        except:
            stock_text = f"({product['stock']} tersisa)" if product['stock'] != -1 else "(Unlimited)"
        
        text += f"<b>{product['id']}. {product['name']}</b>\n"
        text += f"💰 Harga: <b>{format_currency(product['price'])}</b>\n"
        text += f"📦 Stok: {stock_text}\n"
        text += f"📝 {product['description']}\n\n"
        
        # Add buy button only if stock is available
        if stock_count > 0 or product['stock'] == -1:
            keyboard.row(InlineKeyboardButton(
                text=f"🛒 Beli {product['name'][:15]}...", 
                callback_data=f"buy_{product['id']}"
            ))
        else:
            keyboard.row(InlineKeyboardButton(
                text=f"❌ {product['name'][:15]}... (Habis)", 
                callback_data=f"sold_out_{product['id']}"
            ))
    
    keyboard.row(InlineKeyboardButton(text="🏠 Menu Utama", callback_data="main_menu"))
    
    if is_callback:
        await message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")

async def process_purchase(message: types.Message, product_id: int, is_callback: bool = False):
    """Process product purchase"""
    # Get product info
    product = await db.get_product(product_id)
    if not product:
        text = "❌ <b>Produk tidak ditemukan!</b>\n\nGunakan /produk untuk melihat daftar produk yang tersedia."
        if is_callback:
            await message.edit_text(text, parse_mode="HTML")
        else:
            await message.answer(text, parse_mode="HTML")
        return
    
    # Check if product is active and in stock
    if not product['is_active']:
        text = "❌ <b>Produk tidak tersedia!</b>"
        if is_callback:
            await message.edit_text(text, parse_mode="HTML")
        else:
            await message.answer(text, parse_mode="HTML")
        return
    
    # Check stock availability using stock units
    available_stock = await db.get_available_stock_count(product_id)
    if available_stock == 0:
        text = "❌ <b>Produk habis!</b>\n\nSilakan pilih produk lain atau hubungi admin untuk menambah stok."
        if is_callback:
            await message.edit_text(text, parse_mode="HTML")
        else:
            await message.answer(text, parse_mode="HTML")
        return
    
    # Process purchase
    # First, consume the stock unit
    stock_unit = await db.consume_stock_unit(product_id)
    
    if not stock_unit:
        text = "❌ <b>Stok habis saat pemrosesan!</b>\n\nSilakan coba lagi atau pilih produk lain."
        if is_callback:
            await message.edit_text(text, parse_mode="HTML")
        else:
            await message.answer(text, parse_mode="HTML")
        return
    
    # Atomically deduct balance (only if sufficient)
    success = await db.deduct_balance_if_sufficient(message.from_user.id, product['price'])
    
    if not success:
        # Balance was insufficient - return the stock unit back
        await db.add_stock_units(product_id, [stock_unit])
        
        # Get current balance for display
        user_balance = await db.get_user_balance(message.from_user.id)
        
        text = f"❌ <b>Saldo tidak cukup!</b>\n\n"
        text += f"💰 Harga produk: <b>{format_currency(product['price'])}</b>\n"
        text += f"💳 Saldo Anda: <b>{format_currency(user_balance)}</b>\n"
        text += f"💸 Kurang: <b>{format_currency(product['price'] - user_balance)}</b>\n\n"
        text += "Silakan top up saldo terlebih dahulu."
        
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(text="💳 Top Up", callback_data="topup"))
        keyboard.row(InlineKeyboardButton(text="🏠 Menu Utama", callback_data="main_menu"))
        
        if is_callback:
            await message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
        else:
            await message.answer(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
        return
    if success:
        # Create transaction record with stock data
        await db.create_transaction(
            user_id=message.from_user.id,
            transaction_type="purchase",
            amount=product['price'],
            description=f"Pembelian {product['name']}",
            reference_id=f"PUR{product_id}{int(datetime.now().timestamp())}",
            stock_data=stock_unit,
            status='completed'
        )
        
        # Get current balance after deduction for display
        current_balance = await db.get_user_balance(message.from_user.id)
        
        # Success message
        text = f"✅ <b>Pembelian Berhasil!</b>\n\n"
        text += f"🛍️ Produk: <b>{product['name']}</b>\n"
        text += f"💰 Harga: <b>{format_currency(product['price'])}</b>\n"
        text += f"💳 Saldo tersisa: <b>{format_currency(current_balance)}</b>\n\n"
        
        # Display the stock data to user
        text += f"📦 <b>Data Produk Anda:</b>\n"
        text += f"<code>{stock_unit}</code>\n\n"
        
        # Check if manual delivery needed
        product_data = json.loads(product.get('product_data', '{}'))
        if product_data.get('delivery') == 'manual':
            text += "📧 <b>Produk sudah dikirim otomatis.</b>\n"
            text += "Jika ada masalah, hubungi admin.\n\n"
            
            # Notify admin about purchase
            for admin_id in config.ADMIN_USER_IDS:
                try:
                    admin_text = f"🔔 <b>Pembelian Baru!</b>\n\n"
                    admin_text += f"👤 User: {message.from_user.first_name} (@{message.from_user.username or 'N/A'})\n"
                    admin_text += f"🆔 User ID: <code>{message.from_user.id}</code>\n"
                    admin_text += f"🛍️ Produk: {product['name']}\n"
                    admin_text += f"💰 Harga: {format_currency(product['price'])}\n"
                    admin_text += f"📦 Data: <code>{stock_unit}</code>\n"
                    admin_text += f"⏰ Waktu: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
                    
                    await bot.send_message(admin_id, admin_text, parse_mode="HTML")
                except Exception as e:
                    logger.error(f"Failed to notify admin {admin_id}: {e}")
        else:
            text += "🎉 <b>Produk telah dikirim otomatis!</b>\n"
            text += "Terima kasih atas pembelian Anda."
        
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(text="🛍️ Produk Lain", callback_data="products"))
        keyboard.row(InlineKeyboardButton(text="🏠 Menu Utama", callback_data="main_menu"))
        
        if is_callback:
            await message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
        else:
            await message.answer(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
    else:
        # If payment failed, return the stock unit back
        await db.add_stock_units(product_id, [stock_unit])
        
        text = "❌ <b>Terjadi kesalahan dalam pembayaran!</b>\n\nStok telah dikembalikan. Silakan coba lagi."
        if is_callback:
            await message.edit_text(text, parse_mode="HTML")
        else:
            await message.answer(text, parse_mode="HTML")

async def show_transaction_history(message: types.Message, is_callback: bool = False):
    """Show user transaction history"""
    transactions = await db.get_user_transactions(message.from_user.id)
    
    if not transactions:
        text = "📊 <b>Riwayat Transaksi</b>\n\n❌ Belum ada transaksi."
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(text="🏠 Menu Utama", callback_data="main_menu"))
        
        if is_callback:
            await message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
        else:
            await message.answer(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
        return
    
    text = "📊 <b>Riwayat Transaksi</b>\n\n"
    
    for transaction in transactions:
        date = datetime.fromisoformat(transaction['created_at'].replace('Z', '+00:00'))
        formatted_date = date.strftime('%d/%m/%Y %H:%M')
        
        if transaction['transaction_type'] == 'topup':
            icon = "💳"
            type_text = "Top Up"
            amount_text = f"+{format_currency(transaction['amount'])}"
        else:
            icon = "🛍️"
            type_text = "Pembelian"
            amount_text = f"-{format_currency(transaction['amount'])}"
        
        text += f"{icon} <b>{type_text}</b>\n"
        text += f"💰 {amount_text}\n"
        text += f"📝 {transaction['description']}\n"
        
        # Show stock data for purchases if available
        if transaction['transaction_type'] == 'purchase' and transaction.get('stock_data'):
            stock_data = transaction['stock_data']
            # Truncate long stock data for display
            display_data = stock_data[:30] + "..." if len(stock_data) > 30 else stock_data
            text += f"📦 Data: <code>{display_data}</code>\n"
        
        text += f"📅 {formatted_date}\n\n"
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="🏠 Menu Utama", callback_data="main_menu"))
    
    if is_callback:
        await message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")

async def show_user_profile(message: types.Message, user_id: int, is_admin_view: bool = False):
    """Show user profile information"""
    try:
        # Get user profile statistics
        profile_data = await db.get_user_profile_stats(user_id)
        
        if not profile_data:
            if is_admin_view:
                text = f"❌ <b>User tidak ditemukan!</b>\n\nUser dengan ID <code>{user_id}</code> tidak ada dalam database."
            else:
                text = "❌ <b>Profil tidak ditemukan!</b>\n\nTerjadi kesalahan dalam mengambil data profil Anda."
            
            keyboard = InlineKeyboardBuilder()
            keyboard.row(InlineKeyboardButton(text="🏠 Menu Utama", callback_data="main_menu"))
            
            await message.answer(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
            return
        
        user_info = profile_data['user_info']
        
        # Format creation date
        try:
            created_date = datetime.fromisoformat(user_info['created_at'].replace('Z', '+00:00'))
            formatted_date = created_date.strftime('%d/%m/%Y %H:%M')
        except:
            formatted_date = user_info['created_at']
        
        # Build profile text
        if is_admin_view:
            text = f"👤 <b>Profil Pengguna</b> (Admin View)\n\n"
        else:
            text = f"👤 <b>Profil Anda</b>\n\n"
        
        text += f"🆔 <b>User ID:</b> <code>{user_info['user_id']}</code>\n"
        text += f"👤 <b>Nama:</b> {user_info['first_name'] or 'N/A'}\n"
        text += f"📱 <b>Username:</b> @{user_info['username'] or 'N/A'}\n"
        text += f"💰 <b>Saldo Saat Ini:</b> <b>{format_currency(user_info['balance'])}</b>\n\n"
        
        text += f"📊 <b>Statistik Akun:</b>\n"
        text += f"🛍️ Total Pembelian: <b>{profile_data['total_purchases']}</b>\n"
        text += f"💸 Total Pengeluaran: <b>{format_currency(profile_data['total_spent'])}</b>\n"
        text += f"💳 Total Top-up: <b>{profile_data['total_topups']}</b>\n"
        text += f"💰 Total Nominal Top-up: <b>{format_currency(profile_data['total_topup_amount'])}</b>\n\n"
        
        text += f"📅 <b>Akun Dibuat:</b> {formatted_date}"
        
        # Add admin indicator if viewing another user's profile
        if is_admin_view:
            text += f"\n\n🔐 <i>Dilihat oleh admin</i>"
        
        keyboard = InlineKeyboardBuilder()
        
        if not is_admin_view:
            # Regular user viewing their own profile
            keyboard.row(InlineKeyboardButton(text="💳 Top Up", callback_data="topup"))
            keyboard.row(InlineKeyboardButton(text="📊 Riwayat", callback_data="history"))
        
        keyboard.row(InlineKeyboardButton(text="🏠 Menu Utama", callback_data="main_menu"))
        
        await message.answer(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Error showing user profile: {e}")
        text = "❌ <b>Terjadi kesalahan!</b>\n\nGagal menampilkan profil. Silakan coba lagi dalam beberapa saat."
        
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(text="🏠 Menu Utama", callback_data="main_menu"))
        
        await message.answer(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")

async def show_channel_selection(message: types.Message, state: FSMContext):
    """Show payment channel selection for top-up"""
    try:
        data = await state.get_data()
        amount = data.get('amount')
        
        # Get active channels from database
        active_channels = await db.get_active_channels()
        
        if not active_channels:
            # Fallback to default channels if admin hasn't set any
            active_channels = ["QRIS", "BCAVA", "DANABALANCE"]
        
        # Get channel info from Tripay
        channels_info = []
        for channel_code in active_channels:
            channel_info = await tripay.get_channel_info(channel_code)
            if channel_info:
                channels_info.append(channel_info)
        
        if not channels_info:
            # If no channel info available, show error
            text = "❌ <b>Channel pembayaran tidak tersedia!</b>\n\nSilakan hubungi admin."
            keyboard = InlineKeyboardBuilder()
            keyboard.row(InlineKeyboardButton(text="🏠 Menu Utama", callback_data="main_menu"))
            
            await message.answer(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
            await state.clear()
            return
        
        text = f"🏦 <b>Pilih Channel Pembayaran</b>\n\n"
        text += f"💰 Nominal: <b>{format_currency(amount)}</b>\n\n"
        text += f"Pilih channel pembayaran yang Anda inginkan:"
        
        keyboard = InlineKeyboardBuilder()
        
        # Add channel buttons
        for channel in channels_info:
            code = channel.get("code", "")
            name = channel.get("name", code)
            
            # Get fee info if available
            try:
                fee_info = await tripay.get_fee_calculator(amount, code)
                if fee_info:
                    total_fee = fee_info.get("total_fee", 0)
                    total_amount = amount + total_fee
                    
                    if total_fee > 0:
                        button_text = f"🏦 {name} (+{format_currency(total_fee)})"
                    else:
                        button_text = f"🏦 {name} (Gratis)"
                else:
                    button_text = f"🏦 {name}"
            except:
                button_text = f"🏦 {name}"
            
            keyboard.row(InlineKeyboardButton(
                text=button_text,
                callback_data=f"select_channel_{code}"
            ))
        
        # Add default channel option
        default_channel = await db.get_default_channel()
        keyboard.row(InlineKeyboardButton(
            text=f"⚡ Gunakan Default ({default_channel})",
            callback_data="use_default_channel"
        ))
        
        keyboard.row(InlineKeyboardButton(text="❌ Batal", callback_data="main_menu"))
        
        await message.answer(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
        await state.set_state(TopUpStates.selecting_channel)
        
    except Exception as e:
        logger.error(f"Error showing channel selection: {e}")
        text = "❌ <b>Terjadi kesalahan!</b>\n\nSilakan coba lagi dalam beberapa saat."
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(text="🏠 Menu Utama", callback_data="main_menu"))
        
        await message.answer(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
        await state.clear()

@router.callback_query(F.data == "confirm_purchase")
async def cb_confirm_purchase(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    product_id = data.get('product_id')
    quantity = data.get('quantity')
    total_price = data.get('total_price')
    sisa_saldo = data.get('sisa_saldo')
    product_name = data.get('product_name')
    user_id = callback.from_user.id
    # Re-check stock and balance before finalizing
    available_stock = await db.get_available_stock_count(product_id)
    if available_stock < quantity:
        await callback.message.edit_text(f"❌ Stok tidak cukup! Sisa stok: <b>{available_stock}</b>", parse_mode="HTML")
        await state.clear()
        await callback.answer()
        return
    user_balance = await db.get_user_balance(user_id)
    if user_balance < total_price:
        await callback.message.edit_text(f"❌ Saldo tidak cukup! Sisa saldo: <b>{format_currency(user_balance)}</b>", parse_mode="HTML")
        await state.clear()
        await callback.answer()
        return
    # Deduct balance
    success = await db.deduct_balance_if_sufficient(user_id, total_price)
    if not success:
        await callback.message.edit_text(f"❌ Gagal mengurangi saldo. Silakan coba lagi.", parse_mode="HTML")
        await state.clear()
        await callback.answer()
        return
    # Take stock units
    stock_units = []
    for _ in range(quantity):
        unit = await db.consume_stock_unit(product_id)
        if unit:
            stock_units.append(unit)
    # Save transaction (all units in one transaction, each unit in one line)
    await db.create_transaction(
        user_id=user_id,
        transaction_type="purchase",
        amount=total_price,
        description=f"Pembelian {product_name} x{quantity}",
        reference_id=f"PUR{product_id}{int(datetime.now().timestamp())}",
        stock_data="\n".join(stock_units),
        status='completed'
    )
    current_balance = await db.get_user_balance(user_id)
    text = f"✅ <b>Pembelian Berhasil!</b>\n\n"
    text += f"🛍️ Produk: <b>{product_name}</b>\n"
    text += f"🔢 Jumlah: <b>{quantity}</b>\n"
    text += f"💰 Total Harga: <b>{format_currency(total_price)}</b>\n"
    text += f"💳 Saldo tersisa: <b>{format_currency(current_balance)}</b>\n\n"
    text += f"📦 <b>Data Produk Anda:</b>\n"
    for unit in stock_units:
        text += f"<code>{unit}</code>\n"
    text += "\nTerima kasih atas pembelian Anda."
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="🛍️ Produk Lain", callback_data="products"))
    keyboard.row(InlineKeyboardButton(text="🏠 Menu Utama", callback_data="main_menu"))
    await callback.message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
    await state.clear()
    await callback.answer()

@router.callback_query(F.data == "cancel_purchase")
async def cb_cancel_purchase(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ <b>Pembelian dibatalkan.</b>", parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("choose_qty_"))
async def cb_choose_quantity(callback: CallbackQuery, state: FSMContext):
    """Handle quantity selection and show confirmation"""
    data = await state.get_data()
    product_id = data.get('product_id')
    product_name = data.get('product_name')
    price = data.get('price')
    max_stock = data.get('max_stock')
    qty = int(callback.data.split("_")[2])
    if qty < 1 or qty > max_stock:
        await callback.answer("Jumlah tidak valid!", show_alert=True)
        return
    user_balance = await db.get_user_balance(callback.from_user.id)
    total_price = price * qty
    sisa_saldo = user_balance - total_price
    # Simpan ke state
    await state.update_data(quantity=qty, total_price=total_price, sisa_saldo=sisa_saldo)
    text = f"Konfirmasi Pembelian:\n\n🛍️ Produk: <b>{product_name}</b>\n🔢 Jumlah: <b>{qty}</b>\n💰 Total Harga: <b>{format_currency(total_price)}</b>\n💳 Sisa Saldo Setelah Beli: <b>{format_currency(sisa_saldo)}</b>\n\nLanjutkan pembelian?"
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(text="✅ Konfirmasi", callback_data="confirm_purchase"),
        InlineKeyboardButton(text="❌ Batal", callback_data="cancel_purchase")
    )
    await callback.message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
    await state.set_state(PurchaseStates.waiting_confirmation)
    await callback.answer()

# Add routers to dispatcher
dp.include_router(router)
dp.include_router(admin_router)

async def main():
    """Main function to run the bot"""
    # Initialize database
    await db.init_db()
    await init_db_connection()  # Initialize admin handlers database connection
    logger.info("Database initialized")
    
    # Start polling
    logger.info("Starting bot...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main()) 