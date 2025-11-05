import json
import logging
from datetime import datetime
from functools import wraps
from typing import Dict, Any, List

from aiogram import types, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

import config
from database import db
from tripay import tripay

logger = logging.getLogger(__name__)

# Admin router
admin_router = Router()

# States for admin conversations
class AdminStates(StatesGroup):
    # Product management
    add_product_name = State()
    add_product_price = State()
    add_product_description = State()
    add_product_stock = State()
    add_product_delivery = State()
    
    # Stock management
    add_stock_product_id = State()
    add_stock_units = State()
    add_stock_file = State()
    
    # Channel management
    set_channels_selection = State()
    set_default_channel_input = State()
    
    # Balance management
    change_balance_amount = State()
    change_balance_description = State()

class TripayConfigStates(StatesGroup):
    set_api_key = State()
    set_private_key = State()
    set_merchant_code = State()

# Admin authentication decorator
def admin_required(func):
    """Decorator to check if user is admin"""
    @wraps(func)
    async def wrapper(message: types.Message, *args, **kwargs):
        if message.from_user.id not in config.ADMIN_USER_IDS:
            await message.answer(
                "❌ <b>Akses Ditolak!</b>\n\n"
                "Anda tidak memiliki akses admin untuk menggunakan command ini.",
                parse_mode="HTML"
            )
            return
        return await func(message, *args, **kwargs)
    return wrapper

def admin_required_callback(func):
    """Decorator to check if user is admin for callback queries"""
    @wraps(func)
    async def wrapper(callback: types.CallbackQuery, *args, **kwargs):
        if callback.from_user.id not in config.ADMIN_USER_IDS:
            await callback.answer("❌ Akses ditolak! Anda bukan admin.", show_alert=True)
            return
        return await func(callback, *args, **kwargs)
    return wrapper

# Utility functions
def format_currency(amount: int) -> str:
    """Format amount to IDR currency"""
    return f"Rp {amount:,}".replace(',', '.')

def create_admin_menu_keyboard() -> InlineKeyboardMarkup:
    """Create admin main menu keyboard"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🛍️ Kelola Produk", callback_data="admin_products"),
        InlineKeyboardButton(text="💰 Kelola Saldo", callback_data="admin_balance")
    )
    builder.row(
        InlineKeyboardButton(text="🏦 Kelola Channel", callback_data="admin_channels"),
        InlineKeyboardButton(text="📊 Monitoring", callback_data="admin_monitoring")
    )
    builder.row(
        InlineKeyboardButton(text="📈 Statistik", callback_data="admin_stats"),
        InlineKeyboardButton(text="🏠 Menu Utama", callback_data="main_menu")
    )
    return builder.as_markup()

# Admin Commands
@admin_router.message(Command("admin"))
@admin_required
async def cmd_admin_menu(message: types.Message):
    """Admin main menu"""
    text = f"🔐 <b>Panel Admin</b>\n\n"
    text += f"Selamat datang, {message.from_user.first_name}!\n\n"
    text += f"<b>Menu Admin:</b>\n"
    text += f"🛍️ Kelola Produk - Tambah, lihat, hapus produk\n"
    text += f"💰 Kelola Saldo - Cari user, ubah saldo\n"
    text += f"📊 Monitoring - Top-up dan penjualan\n"
    text += f"📈 Statistik - Data statistik toko\n\n"
    text += f"Pilih menu di bawah:"
    
    await message.answer(
        text,
        reply_markup=create_admin_menu_keyboard(),
        parse_mode="HTML"
    )

# Product Management Commands
@admin_router.message(Command("addproduk"))
@admin_required
async def cmd_add_product(message: types.Message, state: FSMContext):
    """Start add product conversation"""
    text = f"➕ <b>Tambah Produk Baru</b>\n\n"
    text += f"Masukkan nama produk:"
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="❌ Batal", callback_data="admin_products"))
    
    await message.answer(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
    await state.set_state(AdminStates.add_product_name)

@admin_router.message(StateFilter(AdminStates.add_product_name))
@admin_required
async def process_product_name(message: types.Message, state: FSMContext):
    """Process product name input"""
    product_name = message.text.strip()
    
    if not product_name:
        await message.answer("❌ Nama produk tidak boleh kosong! Masukkan nama produk:")
        return
    
    await state.update_data(name=product_name)
    
    text = f"💰 <b>Harga Produk</b>\n\n"
    text += f"Produk: <b>{product_name}</b>\n\n"
    text += f"Masukkan harga produk (dalam IDR):\n"
    text += f"Contoh: <code>50000</code>"
    
    await message.answer(text, parse_mode="HTML")
    await state.set_state(AdminStates.add_product_price)

@admin_router.message(StateFilter(AdminStates.add_product_price))
@admin_required
async def process_product_price(message: types.Message, state: FSMContext):
    """Process product price input"""
    try:
        price = int(message.text.replace(".", "").replace(",", ""))
        
        if price <= 0:
            await message.answer("❌ Harga harus lebih dari 0! Masukkan harga yang valid:")
            return
        
        await state.update_data(price=price)
        
        data = await state.get_data()
        
        text = f"📝 <b>Deskripsi Produk</b>\n\n"
        text += f"Produk: <b>{data['name']}</b>\n"
        text += f"Harga: <b>{format_currency(price)}</b>\n\n"
        text += f"Masukkan deskripsi produk:"
        
        await message.answer(text, parse_mode="HTML")
        await state.set_state(AdminStates.add_product_description)
        
    except ValueError:
        await message.answer("❌ Format harga salah! Masukkan hanya angka. Contoh: 50000")

@admin_router.message(StateFilter(AdminStates.add_product_description))
@admin_required
async def process_product_description(message: types.Message, state: FSMContext):
    """Process product description input"""
    description = message.text.strip()
    
    if not description:
        await message.answer("❌ Deskripsi tidak boleh kosong! Masukkan deskripsi produk:")
        return
    
    await state.update_data(description=description)
    
    data = await state.get_data()
    
    text = f"📦 <b>Input Stok Produk</b>\n\n"
    text += f"Produk: <b>{data['name']}</b>\n"
    text += f"Harga: <b>{format_currency(data['price'])}</b>\n"
    text += f"Deskripsi: <b>{description}</b>\n\n"
    text += f"<b>Masukkan stok produk:</b>\n"
    text += f"• Format: 1 baris = 1 unit stok\n"
    text += f"• Contoh untuk akun: <code>email:password</code>\n"
    text += f"• Contoh untuk voucher: <code>VOUCHERCODE123</code>\n"
    text += f"• Atau upload file .txt\n\n"
    text += f"<b>Contoh input:</b>\n"
    text += f"<code>user1@gmail.com:pass123\n"
    text += f"user2@gmail.com:pass456\n"
    text += f"user3@gmail.com:pass789</code>"
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="📁 Upload File", callback_data="upload_stock_file"))
    keyboard.row(InlineKeyboardButton(text="❌ Batal", callback_data="admin_products"))
    
    await message.answer(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
    await state.set_state(AdminStates.add_product_stock)

@admin_router.message(StateFilter(AdminStates.add_product_stock))
@admin_required
async def process_product_stock(message: types.Message, state: FSMContext):
    """Process product stock input"""
    # Handle file upload
    if message.document:
        if not message.document.file_name.endswith('.txt'):
            await message.answer("❌ Format file harus .txt! Silakan upload file .txt atau ketik stok manual.")
            return
        
        try:
            file_info = await message.bot.get_file(message.document.file_id)
            file_content = await message.bot.download_file(file_info.file_path)
            stock_text = file_content.read().decode('utf-8')
        except Exception as e:
            await message.answer("❌ Gagal membaca file! Pastikan file .txt dan encoding UTF-8.")
            return
    else:
        # Handle text input
        stock_text = message.text.strip()
    
    if not stock_text:
        await message.answer("❌ Input stok kosong! Masukkan stok atau upload file .txt.")
        return
    
    # Parse stock units (split by lines and clean)
    stock_units = [line.strip() for line in stock_text.split('\n') if line.strip()]
    
    if not stock_units:
        await message.answer("❌ Tidak ada unit stok yang valid! Pastikan format: 1 baris = 1 unit.")
        return
    
    await state.update_data(stock_units=stock_units)
    
    data = await state.get_data()
    
    text = f"🚚 <b>Jenis Pengiriman</b>\n\n"
    text += f"Produk: <b>{data['name']}</b>\n"
    text += f"Harga: <b>{format_currency(data['price'])}</b>\n"
    text += f"Stok: <b>{len(stock_units)} unit</b>\n\n"
    text += f"<b>Preview stok (5 pertama):</b>\n"
    
    for i, unit in enumerate(stock_units[:5]):
        text += f"• <code>{unit[:50]}{'...' if len(unit) > 50 else ''}</code>\n"
    
    if len(stock_units) > 5:
        text += f"• ... dan {len(stock_units) - 5} unit lainnya\n"
    
    text += f"\nPilih jenis pengiriman:"
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(text="🤖 Otomatis", callback_data="delivery_auto"),
        InlineKeyboardButton(text="👤 Manual", callback_data="delivery_manual")
    )
    keyboard.row(InlineKeyboardButton(text="❌ Batal", callback_data="admin_products"))
    
    await message.answer(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
    await state.set_state(AdminStates.add_product_delivery)

@admin_router.callback_query(F.data.startswith("delivery_"))
@admin_required_callback
async def process_product_delivery(callback: types.CallbackQuery, state: FSMContext):
    """Process product delivery type"""
    delivery_type = callback.data.split("_")[1]  # auto or manual
    
    data = await state.get_data()
    
    # Save product to database
    product_data = json.dumps({
        "type": "digital",
        "delivery": delivery_type
    })
    
    try:
        # Create product with stock units
        product_id = await db.create_product_with_stock(
            name=data['name'],
            description=data['description'],
            price=data['price'],
            stock_units=data['stock_units'],
            is_active=True,
            product_data=product_data
        )
        
        delivery_text = "Otomatis" if delivery_type == "auto" else "Manual"
        stock_count = len(data['stock_units'])
        
        text = f"✅ <b>Produk Berhasil Ditambahkan!</b>\n\n"
        text += f"🆔 ID: <b>{product_id}</b>\n"
        text += f"📦 Nama: <b>{data['name']}</b>\n"
        text += f"💰 Harga: <b>{format_currency(data['price'])}</b>\n"
        text += f"📝 Deskripsi: <b>{data['description']}</b>\n"
        text += f"📦 Stok: <b>{stock_count} unit</b>\n"
        text += f"🚚 Pengiriman: <b>{delivery_text}</b>"
        
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(text="➕ Tambah Lagi", callback_data="add_product"))
        keyboard.row(InlineKeyboardButton(text="📋 Lihat Produk", callback_data="admin_list_products"))
        keyboard.row(InlineKeyboardButton(text="🔐 Menu Admin", callback_data="admin_menu"))
        
        await callback.message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error adding product: {e}")
        await callback.message.edit_text(
            "❌ <b>Gagal menambahkan produk!</b>\n\nTerjadi kesalahan pada database.",
            parse_mode="HTML"
        )
    
    await callback.answer()

@admin_router.message(Command("listproduk"))
@admin_required
async def cmd_list_products(message: types.Message):
    """List all products"""
    await show_admin_products(message)

@admin_router.message(Command("hapusproduk"))
@admin_required
async def cmd_delete_product(message: types.Message):
    """Delete product by ID"""
    command_args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    
    if not command_args:
        await message.answer(
            "❌ <b>Format salah!</b>\n\n"
            "Gunakan: <code>/hapusproduk [ID]</code>\n"
            "Contoh: <code>/hapusproduk 1</code>",
            parse_mode="HTML"
        )
        return
    
    try:
        product_id = int(command_args[0])
        await delete_product_by_id(message, product_id)
        
    except ValueError:
        await message.answer(
            "❌ <b>ID produk harus berupa angka!</b>\n\n"
            "Contoh: <code>/hapusproduk 1</code>",
            parse_mode="HTML"
        )

@admin_router.message(Command("addstock"))
@admin_required
async def cmd_add_stock(message: types.Message, state: FSMContext):
    """Add stock to existing product"""
    command_args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    
    if not command_args:
        await message.answer(
            "❌ <b>Format salah!</b>\n\n"
            "Gunakan: <code>/addstock [PRODUK_ID]</code>\n"
            "Contoh: <code>/addstock 1</code>",
            parse_mode="HTML"
        )
        return
    
    try:
        product_id = int(command_args[0])
        
        # Check if product exists
        product = await db.get_product(product_id)
        if not product:
            await message.answer(
                f"❌ <b>Produk tidak ditemukan!</b>\n\n"
                f"Produk dengan ID {product_id} tidak ada dalam database.",
                parse_mode="HTML"
            )
            return
        
        await state.update_data(product_id=product_id)
        
        current_stock = await db.get_available_stock_count(product_id)
        
        text = f"📦 <b>Tambah Stok Produk</b>\n\n"
        text += f"🆔 ID: <b>{product_id}</b>\n"
        text += f"📦 Nama: <b>{product['name']}</b>\n"
        text += f"💰 Harga: <b>{format_currency(product['price'])}</b>\n"
        text += f"📊 Stok saat ini: <b>{current_stock} unit</b>\n\n"
        text += f"<b>Masukkan stok tambahan:</b>\n"
        text += f"• Format: 1 baris = 1 unit stok\n"
        text += f"• Contoh: <code>email:password</code>\n"
        text += f"• Atau upload file .txt\n\n"
        text += f"<b>Contoh input:</b>\n"
        text += f"<code>user1@gmail.com:pass123\n"
        text += f"user2@gmail.com:pass456</code>"
        
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(text="📁 Upload File", callback_data="upload_addstock_file"))
        keyboard.row(InlineKeyboardButton(text="❌ Batal", callback_data="admin_products"))
        
        await message.answer(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
        await state.set_state(AdminStates.add_stock_units)
        
    except ValueError:
        await message.answer(
            "❌ <b>ID produk harus berupa angka!</b>\n\n"
            "Contoh: <code>/addstock 1</code>",
            parse_mode="HTML"
        )

@admin_router.message(Command("editharga"))
@admin_required
async def cmd_edit_product_price(message: types.Message):
    """Edit product price by ID"""
    command_args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    
    if len(command_args) < 2:
        await message.answer(
            "❌ <b>Format salah!</b>\n\n"
            "Gunakan: <code>/editharga [ID_PRODUK] [HARGA_BARU]</code>\n"
            "Contoh: <code>/editharga 1 50000</code>",
            parse_mode="HTML"
        )
        return
    
    try:
        product_id = int(command_args[0])
        new_price = int(command_args[1])
        
        # Validate price is positive
        if new_price <= 0:
            await message.answer(
                "❌ <b>Harga harus lebih dari 0!</b>\n\n"
                "Contoh: <code>/editharga 1 50000</code>",
                parse_mode="HTML"
            )
            return
        
        # Check if product exists
        product = await db.get_product(product_id)
        if not product:
            await message.answer(
                f"❌ <b>Produk tidak ditemukan!</b>\n\n"
                f"Produk dengan ID {product_id} tidak ada dalam database.",
                parse_mode="HTML"
            )
            return
        
        # Update product price
        success = await db.update_product_price(product_id, new_price)
        
        if success:
            # Format currency for display
            old_price_formatted = f"Rp {product['price']:,}".replace(',', '.')
            new_price_formatted = f"Rp {new_price:,}".replace(',', '.')
            
            await message.answer(
                f"✅ <b>Harga produk berhasil diubah!</b>\n\n"
                f"📦 <b>Produk:</b> {product['name']}\n"
                f"💰 <b>Harga Lama:</b> {old_price_formatted}\n"
                f"💰 <b>Harga Baru:</b> {new_price_formatted}\n\n"
                f"Perubahan telah disimpan ke database.",
                parse_mode="HTML"
            )
        else:
            await message.answer(
                "❌ <b>Gagal mengubah harga produk!</b>\n\n"
                "Terjadi kesalahan saat menyimpan ke database.",
                parse_mode="HTML"
            )
        
    except ValueError:
        await message.answer(
            "❌ <b>Format tidak valid!</b>\n\n"
            "ID produk dan harga harus berupa angka.\n\n"
            "Gunakan: <code>/editharga [ID_PRODUK] [HARGA_BARU]</code>\n"
            "Contoh: <code>/editharga 1 50000</code>",
            parse_mode="HTML"
        )

# Balance Management Commands
@admin_router.message(Command("caripengguna"))
@admin_required
async def cmd_search_user(message: types.Message):
    """Search user by ID"""
    command_args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    
    if not command_args:
        await message.answer(
            "❌ <b>Format salah!</b>\n\n"
            "Gunakan: <code>/caripengguna [USER_ID]</code>\n"
            "Contoh: <code>/caripengguna 123456789</code>",
            parse_mode="HTML"
        )
        return
    
    try:
        user_id = int(command_args[0])
        await show_user_info(message, user_id)
        
    except ValueError:
        await message.answer(
            "❌ <b>User ID harus berupa angka!</b>\n\n"
            "Contoh: <code>/caripengguna 123456789</code>",
            parse_mode="HTML"
        )

@admin_router.message(Command("ubahsaldo"))
@admin_required
async def cmd_change_balance(message: types.Message):
    """Change user balance"""
    command_args = message.text.split()[1:] if len(message.text.split()) > 2 else []
    
    if len(command_args) < 2:
        await message.answer(
            "❌ <b>Format salah!</b>\n\n"
            "Gunakan: <code>/ubahsaldo [USER_ID] [NOMINAL]</code>\n"
            "Contoh: <code>/ubahsaldo 123456789 50000</code>\n"
            "Gunakan angka negatif untuk mengurangi saldo.",
            parse_mode="HTML"
        )
        return
    
    try:
        user_id = int(command_args[0])
        amount = int(command_args[1])
        await change_user_balance(message, user_id, amount)
        
    except ValueError:
        await message.answer(
            "❌ <b>Format angka salah!</b>\n\n"
            "Pastikan USER_ID dan NOMINAL berupa angka.\n"
            "Contoh: <code>/ubahsaldo 123456789 50000</code>",
            parse_mode="HTML"
        )

# Monitoring Commands
@admin_router.message(Command("topupmasuk"))
@admin_required
async def cmd_topup_monitoring(message: types.Message):
    """Show recent top-ups"""
    await show_topup_monitoring(message)

@admin_router.message(Command("penjualan"))
@admin_required
async def cmd_sales_monitoring(message: types.Message):
    """Show recent sales"""
    await show_sales_monitoring(message)

# Payment Channel Management Commands
@admin_router.message(Command("setchannel"))
@admin_required
async def cmd_set_channels(message: types.Message, state: FSMContext):
    """Set active payment channels"""
    text = f"🏦 <b>Mengatur Channel Pembayaran</b>\n\n"
    text += f"Sedang mengambil daftar channel dari Tripay..."
    
    await message.answer(text, parse_mode="HTML")
    
    try:
        # Get all available channels from Tripay
        all_channels = await tripay.get_payment_channels()
        
        if not all_channels or not all_channels.get("success"):
            # Cek error konfigurasi
            if all_channels and all_channels.get("error"):
                await message.answer(f"❌ <b>{all_channels['error']}</b>", parse_mode="HTML")
                return
            await message.answer(
                "❌ <b>Gagal mengambil data channel!</b>\n\n"
                "Pastikan konfigurasi Tripay API sudah benar.",
                parse_mode="HTML"
            )
            return
        
        channels_data = all_channels.get("data", [])
        if not channels_data:
            await message.answer("❌ Tidak ada channel pembayaran yang tersedia.")
            return
        
        # Get currently active channels
        active_channels = await db.get_active_channels()
        
        text = f"🏦 <b>Pilih Channel Pembayaran Aktif</b>\n\n"
        text += f"<b>Channel yang tersedia dari Tripay:</b>\n\n"
        
        keyboard = InlineKeyboardBuilder()
        
        for channel in channels_data:
            code = channel.get("code", "")
            name = channel.get("name", "")
            is_active = code in active_channels
            
            status_icon = "✅" if is_active else "⬜"
            text += f"{status_icon} <b>{name}</b> ({code})\n"
            
            callback_data = f"toggle_channel_{code}"
            button_text = f"{'✅' if is_active else '⬜'} {name}"
            
            keyboard.row(InlineKeyboardButton(
                text=button_text, 
                callback_data=callback_data
            ))
        
        keyboard.row(
            InlineKeyboardButton(text="💾 Simpan", callback_data="save_channels"),
            InlineKeyboardButton(text="❌ Batal", callback_data="admin_menu")
        )
        
        await message.answer(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
        await state.set_state(AdminStates.set_channels_selection)
        
    except Exception as e:
        logger.error(f"Error in set_channels: {e}")
        await message.answer(
            "❌ <b>Terjadi kesalahan!</b>\n\nSilakan coba lagi nanti.",
            parse_mode="HTML"
        )

@admin_router.message(Command("listchannel"))
@admin_required
async def cmd_list_channels(message: types.Message):
    """List active payment channels"""
    try:
        all_channels = await tripay.get_payment_channels()
        if not all_channels or not all_channels.get("success"):
            if all_channels and all_channels.get("error"):
                await message.answer(f"❌ <b>{all_channels['error']}</b>", parse_mode="HTML")
                return
        await show_active_channels(message)
    except Exception as e:
        await message.answer(f"❌ <b>{str(e)}</b>", parse_mode="HTML")

@admin_router.message(Command("setdefaultchannel"))
@admin_required
async def cmd_set_default_channel(message: types.Message):
    """Set default payment channel"""
    command_args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    
    if not command_args:
        # Show available channels for selection
        try:
            active_channels = await db.get_active_channels()
            
            if not active_channels:
                await message.answer(
                    "❌ <b>Belum ada channel aktif!</b>\n\n"
                    "Gunakan /setchannel untuk mengatur channel aktif terlebih dahulu.",
                    parse_mode="HTML"
                )
                return
            
            text = f"🎯 <b>Set Default Channel</b>\n\n"
            text += f"Pilih channel default untuk top-up:\n\n"
            
            keyboard = InlineKeyboardBuilder()
            
            # Get channel info from Tripay
            for channel_code in active_channels:
                channel_info = await tripay.get_channel_info(channel_code)
                if channel_info:
                    name = channel_info.get("name", channel_code)
                    keyboard.row(InlineKeyboardButton(
                        text=f"🎯 {name} ({channel_code})",
                        callback_data=f"set_default_{channel_code}"
                    ))
            
            keyboard.row(InlineKeyboardButton(text="❌ Batal", callback_data="admin_menu"))
            
            await message.answer(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
            
        except Exception as e:
            logger.error(f"Error in set_default_channel: {e}")
            await message.answer("❌ Terjadi kesalahan saat mengambil data channel.")
        
        return
    
    # Direct channel code input
    channel_code = command_args[0].upper()
    
    try:
        # Verify channel exists and is active
        active_channels = await db.get_active_channels()
        
        if channel_code not in active_channels:
            await message.answer(
                f"❌ <b>Channel tidak aktif!</b>\n\n"
                f"Channel <code>{channel_code}</code> tidak ada dalam daftar channel aktif.\n"
                f"Gunakan /listchannel untuk melihat channel aktif.",
                parse_mode="HTML"
            )
            return
        
        # Set as default
        success = await db.set_default_channel(channel_code)
        
        if success:
            channel_info = await tripay.get_channel_info(channel_code)
            channel_name = channel_info.get("name", channel_code) if channel_info else channel_code
            
            text = f"✅ <b>Default Channel Berhasil Diset!</b>\n\n"
            text += f"🎯 Channel default: <b>{channel_name}</b> ({channel_code})\n\n"
            text += f"Channel ini akan digunakan sebagai default jika user tidak memilih channel saat top-up."
            
            await message.answer(text, parse_mode="HTML")
        else:
            await message.answer("❌ Gagal menyimpan setting default channel.")
            
    except Exception as e:
        logger.error(f"Error setting default channel: {e}")
        await message.answer("❌ Terjadi kesalahan saat menyimpan setting.")

# Stock Management Handlers
@admin_router.message(StateFilter(AdminStates.add_stock_units))
@admin_required
async def process_add_stock_units(message: types.Message, state: FSMContext):
    """Process additional stock units input"""
    # Handle file upload
    if message.document:
        if not message.document.file_name.endswith('.txt'):
            await message.answer("❌ Format file harus .txt! Silakan upload file .txt atau ketik stok manual.")
            return
        
        try:
            file_info = await message.bot.get_file(message.document.file_id)
            file_content = await message.bot.download_file(file_info.file_path)
            stock_text = file_content.read().decode('utf-8')
        except Exception as e:
            await message.answer("❌ Gagal membaca file! Pastikan file .txt dan encoding UTF-8.")
            return
    else:
        # Handle text input
        stock_text = message.text.strip()
    
    if not stock_text:
        await message.answer("❌ Input stok kosong! Masukkan stok atau upload file .txt.")
        return
    
    # Parse stock units (split by lines and clean)
    stock_units = [line.strip() for line in stock_text.split('\n') if line.strip()]
    
    if not stock_units:
        await message.answer("❌ Tidak ada unit stok yang valid! Pastikan format: 1 baris = 1 unit.")
        return
    
    data = await state.get_data()
    product_id = data['product_id']
    
    try:
        # Get product info
        product = await db.get_product(product_id)
        old_stock = await db.get_available_stock_count(product_id)
        
        # Add stock units
        success = await db.add_stock_units(product_id, stock_units)
        
        if success:
            new_stock = await db.get_available_stock_count(product_id)
            
            text = f"✅ <b>Stok Berhasil Ditambahkan!</b>\n\n"
            text += f"🆔 ID: <b>{product_id}</b>\n"
            text += f"📦 Nama: <b>{product['name']}</b>\n"
            text += f"📊 Stok lama: <b>{old_stock} unit</b>\n"
            text += f"➕ Ditambahkan: <b>{len(stock_units)} unit</b>\n"
            text += f"📊 Stok baru: <b>{new_stock} unit</b>\n\n"
            text += f"<b>Preview stok yang ditambahkan (5 pertama):</b>\n"
            
            for i, unit in enumerate(stock_units[:5]):
                text += f"• <code>{unit[:50]}{'...' if len(unit) > 50 else ''}</code>\n"
            
            if len(stock_units) > 5:
                text += f"• ... dan {len(stock_units) - 5} unit lainnya\n"
            
            keyboard = InlineKeyboardBuilder()
            keyboard.row(InlineKeyboardButton(text="➕ Tambah Lagi", callback_data=f"add_more_stock_{product_id}"))
            keyboard.row(InlineKeyboardButton(text="📋 Lihat Produk", callback_data="admin_list_products"))
            keyboard.row(InlineKeyboardButton(text="🔐 Menu Admin", callback_data="admin_menu"))
            
            await message.answer(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
        else:
            await message.answer("❌ Gagal menambahkan stok! Terjadi kesalahan pada database.")
            
    except Exception as e:
        logger.error(f"Error adding stock: {e}")
        await message.answer("❌ Gagal menambahkan stok! Terjadi kesalahan pada database.")
    
    await state.clear()

# Callback Query Handlers
@admin_router.callback_query(F.data == "admin_menu")
@admin_required_callback
async def cb_admin_menu(callback: types.CallbackQuery):
    """Show admin menu"""
    text = f"🔐 <b>Panel Admin</b>\n\n"
    text += f"<b>Menu Admin:</b>\n"
    text += f"🛍️ Kelola Produk - Tambah, lihat, hapus produk\n"
    text += f"💰 Kelola Saldo - Cari user, ubah saldo\n"
    text += f"📊 Monitoring - Top-up dan penjualan\n"
    text += f"📈 Statistik - Data statistik toko"
    
    await callback.message.edit_text(
        text,
        reply_markup=create_admin_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@admin_router.callback_query(F.data == "admin_products")
@admin_required_callback
async def cb_admin_products(callback: types.CallbackQuery):
    """Show product management menu"""
    await show_admin_products(callback.message, is_callback=True)
    await callback.answer()

@admin_router.callback_query(F.data == "admin_balance")
@admin_required_callback
async def cb_admin_balance(callback: types.CallbackQuery):
    """Show balance management menu"""
    text = f"💰 <b>Kelola Saldo User</b>\n\n"
    text += f"<b>Command yang tersedia:</b>\n"
    text += f"• <code>/caripengguna [USER_ID]</code> - Info user\n"
    text += f"• <code>/ubahsaldo [USER_ID] [NOMINAL]</code> - Ubah saldo\n\n"
    text += f"<b>Contoh:</b>\n"
    text += f"• <code>/caripengguna 123456789</code>\n"
    text += f"• <code>/ubahsaldo 123456789 50000</code>\n"
    text += f"• <code>/ubahsaldo 123456789 -25000</code> (kurangi)"
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="🔍 Cari User", callback_data="search_user_input"))
    keyboard.row(InlineKeyboardButton(text="🔐 Menu Admin", callback_data="admin_menu"))
    
    await callback.message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
    await callback.answer()

@admin_router.callback_query(F.data == "admin_monitoring")
@admin_required_callback
async def cb_admin_monitoring(callback: types.CallbackQuery):
    """Show monitoring menu"""
    text = f"📊 <b>Monitoring Transaksi</b>\n\n"
    text += f"Pilih jenis monitoring:"
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(text="💳 Top-up Masuk", callback_data="monitor_topups"),
        InlineKeyboardButton(text="🛍️ Penjualan", callback_data="monitor_sales")
    )
    keyboard.row(InlineKeyboardButton(text="🔐 Menu Admin", callback_data="admin_menu"))
    
    await callback.message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
    await callback.answer()

@admin_router.callback_query(F.data == "admin_stats")
@admin_required_callback
async def cb_admin_stats(callback: types.CallbackQuery):
    """Show statistics"""
    await show_admin_statistics(callback.message, is_callback=True)
    await callback.answer()

@admin_router.callback_query(F.data == "admin_channels")
@admin_required_callback
async def cb_admin_channels(callback: types.CallbackQuery):
    """Show channel management menu"""
    text = f"🏦 <b>Kelola Payment Channel</b>\n\n"
    text += f"<b>Fitur yang tersedia:</b>\n"
    text += f"• Set channel aktif untuk user\n"
    text += f"• Lihat daftar channel saat ini\n"
    text += f"• Set default channel\n\n"
    text += f"Pilih menu di bawah:"
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(text="🏦 Set Channel", callback_data="set_channels_menu"),
        InlineKeyboardButton(text="📋 Lihat Channel", callback_data="list_channels")
    )
    keyboard.row(
        InlineKeyboardButton(text="🎯 Set Default", callback_data="set_default_menu"),
        InlineKeyboardButton(text="🔐 Menu Admin", callback_data="admin_menu")
    )
    
    await callback.message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
    await callback.answer()

@admin_router.callback_query(F.data == "set_channels_menu")
@admin_required_callback
async def cb_set_channels_menu(callback: types.CallbackQuery, state: FSMContext):
    """Trigger set channels flow"""
    # Reuse the logic from cmd_set_channels
    text = f"🏦 <b>Mengatur Channel Pembayaran</b>\n\n"
    text += f"Sedang mengambil daftar channel dari Tripay..."
    
    await callback.message.edit_text(text, parse_mode="HTML")
    
    try:
        # Get all available channels from Tripay
        all_channels = await tripay.get_payment_channels()
        
        if not all_channels or not all_channels.get("success"):
            # Cek error konfigurasi
            if all_channels and all_channels.get("error"):
                text = f"❌ <b>{all_channels['error']}</b>\n\nPastikan konfigurasi Tripay API sudah benar."
            else:
                text = "❌ <b>Gagal mengambil data channel!</b>\n\nPastikan konfigurasi Tripay API sudah benar."
            keyboard = InlineKeyboardBuilder()
            keyboard.row(InlineKeyboardButton(text="🔐 Menu Admin", callback_data="admin_menu"))
            await callback.message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
            return
        
        channels_data = all_channels.get("data", [])
        if not channels_data:
            text = "❌ Tidak ada channel pembayaran yang tersedia."
            keyboard = InlineKeyboardBuilder()
            keyboard.row(InlineKeyboardButton(text="🔐 Menu Admin", callback_data="admin_menu"))
            await callback.message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
            return
        
        # Get currently active channels
        active_channels = await db.get_active_channels()
        
        text = f"🏦 <b>Pilih Channel Pembayaran Aktif</b>\n\n"
        text += f"<b>Channel yang tersedia dari Tripay:</b>\n\n"
        
        keyboard = InlineKeyboardBuilder()
        
        for channel in channels_data:
            code = channel.get("code", "")
            name = channel.get("name", "")
            is_active = code in active_channels
            
            status_icon = "✅" if is_active else "⬜"
            text += f"{status_icon} <b>{name}</b> ({code})\n"
            
            callback_data = f"toggle_channel_{code}"
            button_text = f"{'✅' if is_active else '⬜'} {name}"
            
            keyboard.row(InlineKeyboardButton(
                text=button_text, 
                callback_data=callback_data
            ))
        
        keyboard.row(
            InlineKeyboardButton(text="💾 Simpan", callback_data="save_channels"),
            InlineKeyboardButton(text="❌ Batal", callback_data="admin_channels")
        )
        
        await callback.message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
        await state.set_state(AdminStates.set_channels_selection)
        
    except Exception as e:
        logger.error(f"Error in set_channels_menu: {e}")
        text = "❌ <b>Terjadi kesalahan!</b>\n\nSilakan coba lagi nanti."
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(text="🔐 Menu Admin", callback_data="admin_menu"))
        await callback.message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
    
    await callback.answer()

@admin_router.callback_query(F.data == "monitor_topups")
@admin_required_callback
async def cb_monitor_topups(callback: types.CallbackQuery):
    """Show top-up monitoring"""
    await show_topup_monitoring(callback.message, is_callback=True)
    await callback.answer()

@admin_router.callback_query(F.data == "monitor_sales")
@admin_required_callback
async def cb_monitor_sales(callback: types.CallbackQuery):
    """Show sales monitoring"""
    await show_sales_monitoring(callback.message, is_callback=True)
    await callback.answer()

@admin_router.callback_query(F.data == "add_product")
@admin_required_callback
async def cb_add_product(callback: types.CallbackQuery, state: FSMContext):
    """Start add product conversation"""
    text = f"➕ <b>Tambah Produk Baru</b>\n\n"
    text += f"Masukkan nama produk:"
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="❌ Batal", callback_data="admin_products"))
    
    await callback.message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
    await state.set_state(AdminStates.add_product_name)
    await callback.answer()

@admin_router.callback_query(F.data == "admin_list_products")
@admin_required_callback
async def cb_list_products(callback: types.CallbackQuery):
    """List products callback"""
    await show_admin_products(callback.message, is_callback=True)
    await callback.answer()

@admin_router.callback_query(F.data.startswith("delete_product_"))
@admin_required_callback
async def cb_delete_product(callback: types.CallbackQuery):
    """Delete product callback"""
    product_id = int(callback.data.split("_")[2])
    await delete_product_by_id(callback.message, product_id, is_callback=True)
    await callback.answer()

@admin_router.callback_query(F.data.startswith("add_stock_"))
@admin_required_callback
async def cb_add_stock(callback: types.CallbackQuery, state: FSMContext):
    """Add stock callback"""
    product_id = int(callback.data.split("_")[2])
    
    # Check if product exists
    product = await db.get_product(product_id)
    if not product:
        await callback.answer("❌ Produk tidak ditemukan!", show_alert=True)
        return
    
    await state.update_data(product_id=product_id)
    
    current_stock = await db.get_available_stock_count(product_id)
    
    text = f"📦 <b>Tambah Stok Produk</b>\n\n"
    text += f"🆔 ID: <b>{product_id}</b>\n"
    text += f"📦 Nama: <b>{product['name']}</b>\n"
    text += f"💰 Harga: <b>{format_currency(product['price'])}</b>\n"
    text += f"📊 Stok saat ini: <b>{current_stock} unit</b>\n\n"
    text += f"<b>Masukkan stok tambahan:</b>\n"
    text += f"• Format: 1 baris = 1 unit stok\n"
    text += f"• Contoh: <code>email:password</code>\n"
    text += f"• Atau upload file .txt"
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="📁 Upload File", callback_data="upload_addstock_file"))
    keyboard.row(InlineKeyboardButton(text="❌ Batal", callback_data="admin_products"))
    
    await callback.message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
    await state.set_state(AdminStates.add_stock_units)
    await callback.answer()

@admin_router.callback_query(F.data.startswith("add_more_stock_"))
@admin_required_callback
async def cb_add_more_stock(callback: types.CallbackQuery, state: FSMContext):
    """Add more stock callback"""
    product_id = int(callback.data.split("_")[3])
    
    # Reuse the add stock logic
    await state.update_data(product_id=product_id)
    
    product = await db.get_product(product_id)
    current_stock = await db.get_available_stock_count(product_id)
    
    text = f"📦 <b>Tambah Stok Lagi</b>\n\n"
    text += f"🆔 ID: <b>{product_id}</b>\n"
    text += f"📦 Nama: <b>{product['name']}</b>\n"
    text += f"📊 Stok saat ini: <b>{current_stock} unit</b>\n\n"
    text += f"Masukkan stok tambahan:"
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="📁 Upload File", callback_data="upload_addstock_file"))
    keyboard.row(InlineKeyboardButton(text="❌ Batal", callback_data="admin_products"))
    
    await callback.message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
    await state.set_state(AdminStates.add_stock_units)
    await callback.answer()

# Channel Management Callbacks
@admin_router.callback_query(F.data.startswith("toggle_channel_"))
@admin_required_callback
async def cb_toggle_channel(callback: types.CallbackQuery, state: FSMContext):
    """Toggle channel active status"""
    channel_code = callback.data.split("toggle_channel_")[1]
    
    try:
        # Get current active channels
        active_channels = await db.get_active_channels()
        
        # Toggle channel status
        if channel_code in active_channels:
            active_channels.remove(channel_code)
        else:
            active_channels.append(channel_code)
        
        # Update state data
        await state.update_data(selected_channels=active_channels)
        
        # Refresh the interface
        all_channels = await tripay.get_payment_channels()
        if not all_channels or not all_channels.get("success"):
            await callback.answer("❌ Gagal mengambil data channel!", show_alert=True)
            return
        
        channels_data = all_channels.get("data", [])
        
        text = f"🏦 <b>Pilih Channel Pembayaran Aktif</b>\n\n"
        text += f"<b>Channel yang tersedia dari Tripay:</b>\n\n"
        
        keyboard = InlineKeyboardBuilder()
        
        for channel in channels_data:
            code = channel.get("code", "")
            name = channel.get("name", "")
            is_active = code in active_channels
            
            status_icon = "✅" if is_active else "⬜"
            text += f"{status_icon} <b>{name}</b> ({code})\n"
            
            callback_data = f"toggle_channel_{code}"
            button_text = f"{'✅' if is_active else '⬜'} {name}"
            
            keyboard.row(InlineKeyboardButton(
                text=button_text, 
                callback_data=callback_data
            ))
        
        keyboard.row(
            InlineKeyboardButton(text="💾 Simpan", callback_data="save_channels"),
            InlineKeyboardButton(text="❌ Batal", callback_data="admin_menu")
        )
        
        await callback.message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error toggling channel: {e}")
        await callback.answer("❌ Terjadi kesalahan!", show_alert=True)

@admin_router.callback_query(F.data == "save_channels")
@admin_required_callback
async def cb_save_channels(callback: types.CallbackQuery, state: FSMContext):
    """Save selected channels"""
    try:
        data = await state.get_data()
        selected_channels = data.get('selected_channels', [])
        
        if not selected_channels:
            await callback.answer("❌ Pilih minimal satu channel!", show_alert=True)
            return
        
        # Save to database
        success = await db.set_active_channels(selected_channels)
        
        if success:
            # Get channel names for display
            channel_names = []
            for code in selected_channels:
                channel_info = await tripay.get_channel_info(code)
                if channel_info:
                    name = channel_info.get("name", code)
                    channel_names.append(f"{name} ({code})")
                else:
                    channel_names.append(code)
            
            text = f"✅ <b>Channel Berhasil Disimpan!</b>\n\n"
            text += f"<b>Channel aktif ({len(selected_channels)}):</b>\n"
            for name in channel_names:
                text += f"• {name}\n"
            
            keyboard = InlineKeyboardBuilder()
            keyboard.row(InlineKeyboardButton(text="🎯 Set Default", callback_data="set_default_menu"))
            keyboard.row(InlineKeyboardButton(text="🔐 Menu Admin", callback_data="admin_menu"))
            
            await callback.message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
            await state.clear()
        else:
            await callback.answer("❌ Gagal menyimpan channel!", show_alert=True)
            
    except Exception as e:
        logger.error(f"Error saving channels: {e}")
        await callback.answer("❌ Terjadi kesalahan!", show_alert=True)

@admin_router.callback_query(F.data.startswith("set_default_"))
@admin_required_callback
async def cb_set_default_channel(callback: types.CallbackQuery):
    """Set default channel callback"""
    channel_code = callback.data.split("set_default_")[1]
    
    try:
        success = await db.set_default_channel(channel_code)
        
        if success:
            channel_info = await tripay.get_channel_info(channel_code)
            channel_name = channel_info.get("name", channel_code) if channel_info else channel_code
            
            text = f"✅ <b>Default Channel Diset!</b>\n\n"
            text += f"🎯 Channel default: <b>{channel_name}</b> ({channel_code})\n\n"
            text += f"Channel ini akan digunakan jika user tidak memilih channel saat top-up."
            
            keyboard = InlineKeyboardBuilder()  
            keyboard.row(InlineKeyboardButton(text="📋 Lihat Channel", callback_data="list_channels"))
            keyboard.row(InlineKeyboardButton(text="🔐 Menu Admin", callback_data="admin_menu"))
            
            await callback.message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
        else:
            await callback.answer("❌ Gagal menyimpan setting!", show_alert=True)
            
    except Exception as e:
        logger.error(f"Error setting default channel: {e}")
        await callback.answer("❌ Terjadi kesalahan!", show_alert=True)

@admin_router.callback_query(F.data == "set_default_menu")
@admin_required_callback
async def cb_set_default_menu(callback: types.CallbackQuery):
    """Show set default channel menu"""
    try:
        active_channels = await db.get_active_channels()
        
        if not active_channels:
            await callback.answer("❌ Belum ada channel aktif!", show_alert=True)
            return
        
        text = f"🎯 <b>Set Default Channel</b>\n\n"
        text += f"Pilih channel default untuk top-up:\n\n"
        
        keyboard = InlineKeyboardBuilder()
        
        for channel_code in active_channels:
            channel_info = await tripay.get_channel_info(channel_code)
            if channel_info:
                name = channel_info.get("name", channel_code)
                keyboard.row(InlineKeyboardButton(
                    text=f"🎯 {name} ({channel_code})",
                    callback_data=f"set_default_{channel_code}"
                ))
        
        keyboard.row(InlineKeyboardButton(text="❌ Batal", callback_data="admin_menu"))
        
        await callback.message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Error in set_default_menu: {e}")
        await callback.answer("❌ Terjadi kesalahan!", show_alert=True)

@admin_router.callback_query(F.data == "list_channels")
@admin_required_callback
async def cb_list_channels(callback: types.CallbackQuery):
    """List channels callback"""
    await show_active_channels(callback.message, is_callback=True)
    await callback.answer()

@admin_router.message(Command("tripayconfig"))
@admin_required
async def cmd_tripay_config(message: types.Message):
    """Show current Tripay configuration (admin only)"""
    api_key = await db.get_setting("tripay_api_key")
    private_key = await db.get_setting("tripay_private_key")
    merchant_code = await db.get_setting("tripay_merchant_code")
    mode = await db.get_setting("tripay_mode")

    def mask(val):
        if not val:
            return '<i>Belum diatur</i>'
        if len(val) <= 8:
            return val
        return val[:4] + '...' + val[-4:]

    text = (
        "<b>🔑 Konfigurasi Tripay Saat Ini</b>\n\n"
        f"<b>API Key:</b> <code>{mask(api_key)}</code>\n"
        f"<b>Private Key:</b> <code>{mask(private_key)}</code>\n"
        f"<b>Merchant Code:</b> <code>{mask(merchant_code)}</code>\n"
        f"<b>Mode:</b> <code>{mode or 'sandbox'}</code>\n\n"
        "Gunakan /setapikey, /setprivatekey, /setmerchantcode, /settripaymode untuk mengubah."
    )
    await message.answer(text, parse_mode="HTML")

@admin_router.message(Command("setapikey"))
@admin_required
async def cmd_set_api_key(message: types.Message, state: FSMContext):
    await message.answer("Kirimkan API Key Tripay baru:")
    await state.set_state(TripayConfigStates.set_api_key)

@admin_router.message(StateFilter(TripayConfigStates.set_api_key))
@admin_required
async def process_set_api_key(message: types.Message, state: FSMContext):
    api_key = message.text.strip()
    await db.set_setting("tripay_api_key", api_key)
    await message.answer("✅ API Key berhasil disimpan!")
    await state.clear()

@admin_router.message(Command("setprivatekey"))
@admin_required
async def cmd_set_private_key(message: types.Message, state: FSMContext):
    await message.answer("Kirimkan Private Key Tripay baru:")
    await state.set_state(TripayConfigStates.set_private_key)

@admin_router.message(StateFilter(TripayConfigStates.set_private_key))
@admin_required
async def process_set_private_key(message: types.Message, state: FSMContext):
    private_key = message.text.strip()
    await db.set_setting("tripay_private_key", private_key)
    await message.answer("✅ Private Key berhasil disimpan!")
    await state.clear()

@admin_router.message(Command("setmerchantcode"))
@admin_required
async def cmd_set_merchant_code(message: types.Message, state: FSMContext):
    await message.answer("Kirimkan Merchant Code Tripay baru:")
    await state.set_state(TripayConfigStates.set_merchant_code)

@admin_router.message(StateFilter(TripayConfigStates.set_merchant_code))
@admin_required
async def process_set_merchant_code(message: types.Message, state: FSMContext):
    merchant_code = message.text.strip()
    await db.set_setting("tripay_merchant_code", merchant_code)
    await message.answer("✅ Merchant Code berhasil disimpan!")
    await state.clear()

@admin_router.message(Command("settripaymode"))
@admin_required
async def cmd_set_tripay_mode(message: types.Message):
    text = "<b>Pilih mode Tripay:</b>"
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(text="Sandbox", callback_data="tripaymode_sandbox"),
        InlineKeyboardButton(text="Production", callback_data="tripaymode_production")
    )
    await message.answer(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")

@admin_router.callback_query(F.data.startswith("tripaymode_"))
@admin_required_callback
async def cb_set_tripay_mode(callback: types.CallbackQuery):
    mode = callback.data.split("_")[1]
    await db.set_setting("tripay_mode", mode)
    await callback.message.edit_text(f"✅ Mode Tripay di-set ke <b>{mode}</b>", parse_mode="HTML")
    await callback.answer("Mode Tripay diubah!")

# Helper Functions
async def show_admin_products(message: types.Message, is_callback: bool = False):
    """Show admin products list"""
    products = await db.get_products(active_only=False)
    
    text = f"🛍️ <b>Daftar Produk</b>\n\n"
    
    if not products:
        text += "Belum ada produk dalam database."
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(text="➕ Tambah Produk", callback_data="add_product"))
        keyboard.row(InlineKeyboardButton(text="🔐 Menu Admin", callback_data="admin_menu"))
    else:
        for product in products:
            status = "✅" if product['is_active'] else "❌"
            # Get actual stock count from stock_units if available
            try:
                stock_units = json.loads(product.get('stock_units', '[]'))
                stock_count = len(stock_units)
                stock_text = f"{stock_count} unit"
            except:
                stock_text = f"{product['stock']}" if product['stock'] != -1 else "∞"
            
            text += f"{status} <b>ID {product['id']}: {product['name']}</b>\n"
            text += f"💰 {format_currency(product['price'])} | 📦 Stok: {stock_text}\n"
            text += f"📝 {product['description'][:50]}{'...' if len(product['description']) > 50 else ''}\n\n"
        
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(text="➕ Tambah Produk", callback_data="add_product"))
        
        # Add stock and delete buttons for each product
        for product in products[:4]:  # Limit to first 4 products to avoid keyboard overflow
            keyboard.row(
                InlineKeyboardButton(text=f"📦 Stok ID {product['id']}", callback_data=f"add_stock_{product['id']}"),
                InlineKeyboardButton(text=f"🗑️ Hapus ID {product['id']}", callback_data=f"delete_product_{product['id']}")
            )
        
        keyboard.row(InlineKeyboardButton(text="🔐 Menu Admin", callback_data="admin_menu"))
    
    if is_callback:
        await message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")

async def delete_product_by_id(message: types.Message, product_id: int, is_callback: bool = False):
    """Delete product by ID"""
    product = await db.get_product(product_id)
    
    if not product:
        text = f"❌ <b>Produk tidak ditemukan!</b>\n\nProduk dengan ID {product_id} tidak ada dalam database."
    else:
        try:
            # Delete product from database
            async with db._connect() as conn:
                cursor = await conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
                await conn.commit()
                
                if cursor.rowcount > 0:
                    text = f"✅ <b>Produk Berhasil Dihapus!</b>\n\n"
                    text += f"🆔 ID: <b>{product_id}</b>\n"
                    text += f"📦 Nama: <b>{product['name']}</b>\n"
                    text += f"💰 Harga: <b>{format_currency(product['price'])}</b>"
                else:
                    text = f"❌ <b>Gagal menghapus produk!</b>\n\nTerjadi kesalahan pada database."
                    
        except Exception as e:
            logger.error(f"Error deleting product: {e}")
            text = f"❌ <b>Gagal menghapus produk!</b>\n\nTerjadi kesalahan pada database."
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="📋 Lihat Produk", callback_data="admin_products"))
    keyboard.row(InlineKeyboardButton(text="🔐 Menu Admin", callback_data="admin_menu"))
    
    if is_callback:
        await message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")

async def show_user_info(message: types.Message, user_id: int):
    """Show user information"""
    user = await db.get_user(user_id)
    
    if not user:
        text = f"❌ <b>User tidak ditemukan!</b>\n\nUser dengan ID {user_id} tidak ada dalam database."
    else:
        # Get user transactions
        transactions = await db.get_user_transactions(user_id, limit=5)
        
        text = f"👤 <b>Info Pengguna</b>\n\n"
        text += f"🆔 ID: <code>{user['user_id']}</code>\n"
        text += f"👤 Username: @{user['username'] or 'N/A'}\n"
        text += f"📝 Nama: <b>{user['first_name']}</b>\n"
        text += f"💰 Saldo: <b>{format_currency(user['balance'])}</b>\n"
        text += f"📅 Bergabung: {user['created_at']}\n\n"
        
        if transactions:
            text += f"📊 <b>5 Transaksi Terakhir:</b>\n"
            for txn in transactions:
                icon = "💳" if txn['transaction_type'] == 'topup' else "🛍️"
                amount_text = f"+{format_currency(txn['amount'])}" if txn['transaction_type'] == 'topup' else f"-{format_currency(txn['amount'])}"
                text += f"{icon} {amount_text} - {txn['description'][:30]}...\n"
        else:
            text += f"📊 <b>Belum ada transaksi</b>"
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="💰 Ubah Saldo", callback_data=f"change_balance_{user_id}"))
    keyboard.row(InlineKeyboardButton(text="🔐 Menu Admin", callback_data="admin_menu"))
    
    await message.answer(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")

async def change_user_balance(message: types.Message, user_id: int, amount: int):
    """Change user balance"""
    user = await db.get_user(user_id)
    
    if not user:
        text = f"❌ <b>User tidak ditemukan!</b>\n\nUser dengan ID {user_id} tidak ada dalam database."
        await message.answer(text, parse_mode="HTML")
        return
    
    try:
        # Update balance
        success = await db.update_user_balance(user_id, amount)
        
        if success:
            # Create transaction record
            txn_type = "topup" if amount > 0 else "deduction"
            await db.create_transaction(
                user_id=user_id,
                transaction_type=txn_type,
                amount=abs(amount),
                description=f"Manual {txn_type} oleh admin",
                reference_id=f"ADMIN{int(datetime.now().timestamp())}"
            )
            
            new_balance = await db.get_user_balance(user_id)
            
            text = f"✅ <b>Saldo Berhasil Diubah!</b>\n\n"
            text += f"👤 User: <b>{user['first_name']}</b>\n"
            text += f"🆔 ID: <code>{user_id}</code>\n"
            text += f"💰 Perubahan: <b>{'+' if amount > 0 else ''}{format_currency(amount)}</b>\n"
            text += f"💳 Saldo Baru: <b>{format_currency(new_balance)}</b>"
        else:
            text = f"❌ <b>Gagal mengubah saldo!</b>\n\nTerjadi kesalahan pada database."
            
    except Exception as e:
        logger.error(f"Error changing balance: {e}")
        text = f"❌ <b>Gagal mengubah saldo!</b>\n\nTerjadi kesalahan pada database."
    
    await message.answer(text, parse_mode="HTML")

async def show_topup_monitoring(message: types.Message, is_callback: bool = False):
    """Show top-up monitoring"""
    text = f"💳 <b>Monitoring Top-up</b>\n\n"
    
    try:
        # Get recent Tripay transactions
        async with db._connect() as conn:
            conn.row_factory = db._Row
            cursor = await conn.execute("""
                SELECT t.*, u.username, u.first_name 
                FROM tripay_transactions t
                JOIN users u ON t.user_id = u.user_id
                ORDER BY t.created_at DESC
                LIMIT 10
            """)
            tripay_transactions = await cursor.fetchall()
        
        if not tripay_transactions:
            text += "Belum ada top-up yang tercatat."
        else:
            for txn in tripay_transactions:
                status_icon = "✅" if txn['status'] == 'PAID' else "⏳" if txn['status'] == 'UNPAID' else "❌"
                
                text += f"{status_icon} <b>{txn['status']}</b>\n"
                text += f"👤 {txn['first_name']} (@{txn['username'] or 'N/A'})\n"
                text += f"💰 {format_currency(txn['amount'])}\n"
                text += f"📋 <code>{txn['reference']}</code>\n"
                text += f"📅 {txn['created_at']}\n\n"
    
    except Exception as e:
        logger.error(f"Error getting topup monitoring: {e}")
        text += "❌ Terjadi kesalahan saat mengambil data."
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="🔄 Refresh", callback_data="monitor_topups"))
    keyboard.row(InlineKeyboardButton(text="📊 Monitoring", callback_data="admin_monitoring"))
    
    if is_callback:
        await message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")

async def show_sales_monitoring(message: types.Message, is_callback: bool = False):
    """Show sales monitoring"""
    text = f"🛍️ <b>Monitoring Penjualan</b>\n\n"
    
    try:
        # Get recent purchase transactions
        async with db._connect() as conn:
            conn.row_factory = db._Row
            cursor = await conn.execute("""
                SELECT t.*, u.username, u.first_name 
                FROM transactions t
                JOIN users u ON t.user_id = u.user_id
                WHERE t.transaction_type = 'purchase' AND t.status = 'completed'
                ORDER BY t.created_at DESC
                LIMIT 10
            """)
            purchases = await cursor.fetchall()
        
        if not purchases:
            text += "Belum ada penjualan yang tercatat."
        else:
            for purchase in purchases:
                text += f"🛍️ <b>Pembelian</b>\n"
                text += f"👤 {purchase['first_name']} (@{purchase['username'] or 'N/A'})\n"
                text += f"💰 {format_currency(purchase['amount'])}\n"
                text += f"📝 {purchase['description']}\n"
                text += f"📅 {purchase['created_at']}\n\n"
    
    except Exception as e:
        logger.error(f"Error getting sales monitoring: {e}")
        text += "❌ Terjadi kesalahan saat mengambil data."
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="🔄 Refresh", callback_data="monitor_sales"))
    keyboard.row(InlineKeyboardButton(text="📊 Monitoring", callback_data="admin_monitoring"))
    
    if is_callback:
        await message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")

async def show_admin_statistics(message: types.Message, is_callback: bool = False):
    """Show admin statistics"""
    text = f"📈 <b>Statistik Toko</b>\n\n"
    
    try:
        async with db._connect() as conn:
            # Total users
            cursor = await conn.execute("SELECT COUNT(*) FROM users")
            total_users = (await cursor.fetchone())[0]
            
            # Active products
            cursor = await conn.execute("SELECT COUNT(*) FROM products WHERE is_active = 1")
            active_products = (await cursor.fetchone())[0]
            
            # Total revenue
            cursor = await conn.execute("""
                SELECT SUM(amount) FROM transactions 
                WHERE transaction_type = 'purchase' AND status = 'completed'
            """)
            total_revenue = (await cursor.fetchone())[0] or 0
            
            # Total top-ups
            cursor = await conn.execute("""
                SELECT SUM(amount) FROM transactions 
                WHERE transaction_type = 'topup' AND status = 'completed'
            """)
            total_topups = (await cursor.fetchone())[0] or 0
            
            # Pending top-ups
            cursor = await conn.execute("""
                SELECT COUNT(*) FROM tripay_transactions 
                WHERE status = 'UNPAID'
            """)
            pending_topups = (await cursor.fetchone())[0]
            
            # Today's sales
            cursor = await conn.execute("""
                SELECT COUNT(*), COALESCE(SUM(amount), 0) FROM transactions 
                WHERE transaction_type = 'purchase' AND status = 'completed'
                AND date(created_at) = date('now')
            """)
            today_sales = await cursor.fetchone()
            
            text += f"👥 <b>Total User:</b> {total_users}\n"
            text += f"🛍️ <b>Produk Aktif:</b> {active_products}\n"
            text += f"💰 <b>Total Pendapatan:</b> {format_currency(total_revenue)}\n"
            text += f"💳 <b>Total Top-up:</b> {format_currency(total_topups)}\n"
            text += f"⏳ <b>Top-up Pending:</b> {pending_topups}\n\n"
            text += f"📅 <b>Hari Ini:</b>\n"
            text += f"🛍️ Penjualan: {today_sales[0]} transaksi\n"
            text += f"💰 Pendapatan: {format_currency(today_sales[1])}"
            
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        text += "❌ Terjadi kesalahan saat mengambil data."
    
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="🔄 Refresh", callback_data="admin_stats"))
    keyboard.row(InlineKeyboardButton(text="🔐 Menu Admin", callback_data="admin_menu"))
    
    if is_callback:
        await message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")

async def show_active_channels(message: types.Message, is_callback: bool = False):
    """Show active payment channels"""
    try:
        active_channels = await db.get_active_channels()
        default_channel = await db.get_default_channel()
        
        text = f"🏦 <b>Channel Pembayaran Aktif</b>\n\n"
        
        if not active_channels:
            text += "❌ Belum ada channel aktif yang diset.\n\n"
            text += "Gunakan /setchannel untuk mengatur channel aktif."
        else:
            text += f"<b>Channel aktif ({len(active_channels)}):</b>\n"
            
            for channel_code in active_channels:
                # Get channel info from Tripay
                channel_info = await tripay.get_channel_info(channel_code)
                if channel_info:
                    name = channel_info.get("name", channel_code)
                    is_default = "🎯" if channel_code == default_channel else "•"
                    text += f"{is_default} <b>{name}</b> ({channel_code})\n"
                else:
                    is_default = "🎯" if channel_code == default_channel else "•"
                    text += f"{is_default} {channel_code}\n"
            
            text += f"\n🎯 = Channel default\n"
            text += f"📝 Default channel: <b>{default_channel}</b>"
        
        keyboard = InlineKeyboardBuilder()
        keyboard.row(
            InlineKeyboardButton(text="🏦 Set Channel", callback_data="set_channels_menu"),
            InlineKeyboardButton(text="🎯 Set Default", callback_data="set_default_menu")
        )
        keyboard.row(InlineKeyboardButton(text="🔐 Menu Admin", callback_data="admin_menu"))
        
        if is_callback:
            await message.edit_text(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
        else:
            await message.answer(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
            
    except Exception as e:
        logger.error(f"Error showing active channels: {e}")
        error_text = "❌ Terjadi kesalahan saat mengambil data channel."
        
        keyboard = InlineKeyboardBuilder()
        keyboard.row(InlineKeyboardButton(text="🔐 Menu Admin", callback_data="admin_menu"))
        
        if is_callback:
            await message.edit_text(error_text, reply_markup=keyboard.as_markup())
        else:
            await message.answer(error_text, reply_markup=keyboard.as_markup())

# Fix database connection method
async def init_db_connection():
    """Initialize database connection method for admin handlers"""
    import aiosqlite
    
    def _connect():
        return aiosqlite.connect(db.db_path)
    
    db._connect = _connect
    db._Row = aiosqlite.Row 