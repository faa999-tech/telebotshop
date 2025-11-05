# 🤖 Telegram Bot Toko Digital dengan Sistem Saldo

Bot Telegram untuk jualan produk digital dengan sistem saldo dan integrasi pembayaran menggunakan Tripay API.

## ✨ Fitur Utama

### 🏦 Sistem Saldo
- Setiap pengguna memiliki saldo tersendiri
- Top-up saldo melalui Tripay (berbagai metode pembayaran)
- Riwayat transaksi lengkap
- Notifikasi otomatis untuk setiap transaksi

### 💳 Integrasi Tripay & Payment Channels
- **Multi-Channel Support:** QRIS, BCA, BNI, Mandiri, DANA, OVO, GoPay, dll
- **Smart Channel Selection:** User pilih channel saat top-up dengan fee calculator
- **Admin Channel Control:** Admin set channel mana yang aktif untuk user
- **Default Channel System:** Fallback channel jika user tidak memilih
- **Real-time Fee Display:** Tampilkan biaya admin setiap channel
- **Webhook Integration:** Auto-update saldo saat pembayaran confirmed
- **Signature Verification:** Security dengan HMAC SHA256
- **Sandbox Support:** Testing mode untuk development

### 🛍️ Sistem Produk & Stok
- **Stok Units:** Setiap produk memiliki stok berupa list units (email:password, voucher code, dll)
- **Smart Stock Management:** Stok otomatis berkurang saat dibeli, unit dikirim langsung ke pembeli
- **Admin Stock Control:** Tambah stok via text input atau upload file .txt
- **Real-time Stock Display:** Jumlah stok tersedia ditampilkan di semua interface
- **Purchase History:** Riwayat pembelian menyimpan data unit yang dibeli
- **Automatic Delivery:** Produk digital langsung dikirim saat pembelian berhasil

### 🎯 Perintah Bot
- `/start` - Menu utama
- `/saldo` - Cek saldo terkini
- `/topup` - Top-up saldo
- `/produk` - Lihat daftar produk
- `/beli [ID]` - Beli produk
- `/riwayat` - Riwayat transaksi

### 🔐 Perintah Admin
- `/admin` - Panel admin utama
- `/addproduk` - Tambah produk baru (dengan input stok unit)
- `/addstock [ID]` - Tambah stok ke produk existing
- `/listproduk` - Lihat semua produk dengan jumlah stok
- `/hapusproduk [ID]` - Hapus produk
- `/caripengguna [USER_ID]` - Info pengguna
- `/ubahsaldo [USER_ID] [NOMINAL]` - Ubah saldo user
- `/topupmasuk` - Monitor top-up masuk
- `/penjualan` - Monitor penjualan

### 🏦 Payment Channel Management
- `/setchannel` - Set channel pembayaran aktif
- `/listchannel` - Lihat channel aktif saat ini
- `/setdefaultchannel [KODE]` - Set channel default

## 🚀 Instalasi

### 1. Clone Repository
```bash
git clone <repository_url>
cd BOT_TELEGRAM
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Konfigurasi Environment
Salin file `env_template.txt` ke `.env` dan isi dengan data Anda:

```bash
cp env_template.txt .env
```

Edit file `.env`:
```env
# Bot Configuration
BOT_TOKEN=your_telegram_bot_token_here

# Tripay Configuration
TRIPAY_API_KEY=your_tripay_api_key
TRIPAY_PRIVATE_KEY=your_tripay_private_key
TRIPAY_MERCHANT_CODE=your_merchant_code

# Admin Configuration
ADMIN_USER_IDS=123456789,987654321

# Webhook Configuration
WEBHOOK_URL=https://your-domain.com
WEBHOOK_PORT=8080
```

### 4. Konfigurasi Tambahan
Edit file `config.py` untuk menyesuaikan pengaturan:
- `MIN_TOPUP_AMOUNT` - Minimal nominal top-up (default: 10.000)
- `ADMIN_USER_IDS` - List ID admin untuk notifikasi
- `TRIPAY_BASE_URL` - URL API Tripay (sandbox/production)

## 🏃‍♂️ Menjalankan Bot

### Mode Development (Local)
```bash
# Jalankan bot saja
python main.py

# Atau jalankan dengan webhook handler
python webhook_handler.py
```

### Mode Production
1. Deploy aplikasi ke server (VPS/Cloud)
2. Setup reverse proxy (Nginx) untuk webhook
3. Konfigurasi SSL certificate untuk HTTPS
4. Setup domain/subdomain untuk webhook URL

### Contoh Setup Nginx
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location /webhook/tripay {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /payment-return {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 📋 Konfigurasi Tripay

### 1. Daftar Akun Tripay
- Kunjungi [Tripay.co.id](https://tripay.co.id)
- Daftar merchant account
- Dapatkan API Key, Private Key, dan Merchant Code

### 2. Setup Webhook di Dashboard Tripay
- URL Callback: `https://your-domain.com/webhook/tripay`
- URL Return: `https://your-domain.com/payment-return`

### 3. Mode Testing
Untuk testing, gunakan sandbox:
```python
TRIPAY_BASE_URL = 'https://tripay.co.id/api-sandbox'
```

## 💾 Database

Bot menggunakan SQLite dengan struktur tabel:

### Users
- `user_id` - ID Telegram user
- `username` - Username Telegram
- `first_name` - Nama depan
- `balance` - Saldo user
- `created_at`, `updated_at` - Timestamp

### Products
- `id` - ID produk
- `name` - Nama produk
- `description` - Deskripsi
- `price` - Harga (dalam IDR)
- `stock` - Stok (-1 untuk unlimited)
- `is_active` - Status aktif
- `product_data` - Data tambahan (JSON)

### Transactions
- `id` - ID transaksi
- `user_id` - ID user
- `transaction_type` - Jenis (topup/purchase)
- `amount` - Nominal
- `description` - Deskripsi
- `reference_id` - Reference ID
- `status` - Status transaksi

### Tripay Transactions
- `reference` - Reference Tripay
- `user_id` - ID user
- `amount` - Nominal
- `status` - Status pembayaran
- `checkout_url` - URL pembayaran

## 🛠️ Manajemen Produk

### Menambah Produk Manual
Edit file `database.py` di fungsi `_insert_sample_products()` atau tambahkan langsung ke database:

```python
sample_products = [
    ("Nama Produk", "Deskripsi", harga, stok, 1, json.dumps({"type": "digital", "delivery": "auto"})),
]
```

### Jenis Pengiriman
- `auto` - Otomatis (untuk produk yang bisa dikirim otomatis)
- `manual` - Manual (admin akan mengirim secara manual)

## 📦 Sistem Stok Unit

### Konsep Stok Unit
Bot ini menggunakan sistem **stok unit** dimana setiap produk memiliki daftar item individual yang bisa dijual:
- **Format:** 1 baris = 1 unit stok
- **Contoh Akun:** `email@domain.com:password123`
- **Contoh Voucher:** `VOUCHER-CODE-ABC123`
- **Contoh Game Item:** `ItemID:12345|Quantity:10`

### Admin: Mengelola Stok

#### 1. Tambah Produk dengan Stok (/addproduk)
```
Admin: /addproduk
Bot: Masukkan nama produk:
Admin: Netflix Premium Account
Bot: Masukkan harga produk:
Admin: 50000
Bot: Masukkan deskripsi:
Admin: Akun Netflix Premium aktif 1 bulan
Bot: Masukkan stok produk:
Admin: 
user1@gmail.com:pass123
user2@gmail.com:pass456
user3@gmail.com:pass789
Bot: ✅ Produk berhasil ditambahkan dengan 3 unit stok!
```

#### 2. Tambah Stok ke Produk Existing (/addstock)
```
Admin: /addstock 1
Bot: Info produk ID 1, stok saat ini: 2 unit
     Masukkan stok tambahan:
Admin: 
user4@gmail.com:pass101
user5@gmail.com:pass202
Bot: ✅ Berhasil menambah 2 unit, total stok: 4 unit
```

#### 3. Upload File Stok (.txt)
```
Admin: /addstock 1
Bot: [Tombol "📁 Upload File"]
Admin: [Upload file stock.txt]
Content file:
user6@gmail.com:pass303
user7@gmail.com:pass404
user8@gmail.com:pass505
Bot: ✅ Berhasil menambah 3 unit dari file
```

### User: Pembelian Otomatis

#### Flow Pembelian
1. **User:** `/produk` - Melihat produk dengan stok tersedia
2. **User:** Klik "🛒 Beli Netflix Premium" 
3. **Bot:** Cek saldo & stok → Potong saldo → Ambil 1 unit stok
4. **Bot:** Kirim unit stok langsung ke user:
   ```
   ✅ Pembelian Berhasil!
   🛍️ Produk: Netflix Premium Account
   💰 Harga: Rp 50,000
   💳 Saldo tersisa: Rp 25,000
   
   📦 Data Produk Anda:
   user3@gmail.com:pass789
   
   🎉 Produk telah dikirim otomatis!
   ```

### Fitur Keamanan Stok

#### Stock Race Condition Protection
- Stok di-consume atomically sebelum payment
- Jika payment gagal, stok dikembalikan otomatis
- Tidak ada overselling meski banyak user beli bersamaan

#### Stock Validation
- Real-time stock count di semua tampilan
- Button "Beli" otomatis jadi "Habis" jika stok 0
- Pembelian ditolak jika stok habis saat proses

#### Transaction Logging
- Setiap pembelian menyimpan unit stok yang dibeli
- Riwayat lengkap untuk audit & customer service
- Admin dapat melihat unit mana yang terjual ke siapa

### Database Schema

#### Products Table (Updated)
```sql
CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    price INTEGER NOT NULL,
    stock INTEGER DEFAULT 0,        -- count of available units
    stock_units TEXT DEFAULT '[]',  -- JSON array of stock units
    is_active BOOLEAN DEFAULT 1,
    product_data TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Transactions Table (Updated)
```sql
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    transaction_type TEXT NOT NULL,
    amount INTEGER NOT NULL,
    description TEXT,
    reference_id TEXT,
    stock_data TEXT,               -- unit yang dibeli
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Testing Stock System
```bash
# Test all stock functions
python test_stock_system.py

# Expected output:
✅ Product created with ID: 6
✅ Stock units added: 5
✅ Available stock: 5 units
✅ Consumed unit 1: user1@gmail.com:password123
✅ Added 2 additional units
✅ Purchase transaction created with stock data
✅ All stock system tests completed!
```

## 🏦 Sistem Payment Channels

### Konsep Multi-Channel Payment
Bot ini mendukung **multiple payment channels** dari Tripay dimana admin dapat mengontrol channel mana yang tersedia untuk user, dan user dapat memilih channel sesuai preferensi mereka.

### Admin: Kelola Payment Channels

#### 1. Set Channel Aktif (/setchannel)
```
Admin: /setchannel
Bot: [Menampilkan daftar channel dari Tripay API]
     ⬜ QRIS
     ✅ BCA Virtual Account  
     ⬜ BNI Virtual Account
     ✅ DANA Balance
     [Tombol toggle untuk each channel]
Admin: [Toggle channel yang diinginkan]
Bot: ✅ Channel berhasil disimpan!
     Active channels: BCAVA, DANABALANCE
```

#### 2. Lihat Channel Aktif (/listchannel)
```
Admin: /listchannel
Bot: 🏦 Channel Pembayaran Aktif

     • BCA Virtual Account (BCAVA)
     🎯 DANA Balance (DANABALANCE) 
     • QRIS (QRIS)
     
     🎯 = Channel default
     Default channel: DANABALANCE
```

#### 3. Set Default Channel (/setdefaultchannel)
```
# Option 1: Direct command
Admin: /setdefaultchannel QRIS
Bot: ✅ Default channel diset ke QRIS

# Option 2: Interactive selection
Admin: /setdefaultchannel
Bot: [Menampilkan pilihan dari active channels]
Admin: [Pilih channel]
Bot: ✅ Default channel berhasil diset!
```

### User: Top-up dengan Channel Selection

#### Flow Top-up Baru
1. **User:** `/topup`
2. **Bot:** "Masukkan nominal..."
3. **User:** `100000`
4. **Bot:** Channel selection dengan fee info:
   ```
   🏦 Pilih Channel Pembayaran
   💰 Nominal: Rp 100,000

   🏦 QRIS (Gratis)
   🏦 BCA Virtual Account (+Rp 2,900)
   🏦 DANA Balance (+Rp 1,500)
   ⚡ Gunakan Default (QRIS)
   ```
5. **User:** [Pilih channel]
6. **Bot:** Generate invoice dengan channel yang dipilih
7. **Bot:** "💳 Invoice Pembayaran
             🏦 Channel: QRIS
             📋 Reference: TR123...
             [Link pembayaran]"

### Database Schema Updates

#### Settings Table (New)
```sql
CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Default data:
INSERT INTO settings VALUES 
('active_channels', '["QRIS","BCAVA","DANABALANCE"]'),
('default_channel', 'QRIS');
```

### API Integration

#### Tripay Channel Methods
```python
# Get all available channels from Tripay
channels = await tripay.get_payment_channels()

# Get filtered active channels only
active_channels = await tripay.get_active_payment_channels(['QRIS', 'BCAVA'])

# Get specific channel info
channel_info = await tripay.get_channel_info('QRIS')

# Calculate fee for specific channel
fee_info = await tripay.get_fee_calculator(amount=100000, method_code='BCAVA')

# Create transaction with specific channel
transaction = await tripay.create_transaction(
    amount=100000, 
    user_id=123456, 
    method='QRIS'
)
```

### Configuration

#### Default Channels
Jika admin belum set channel aktif, bot menggunakan default:
- **QRIS** - QR Code payment
- **BCAVA** - BCA Virtual Account  
- **DANABALANCE** - DANA Balance

#### Fallback System
- Jika admin belum set active channels → gunakan default channels
- Jika user tidak pilih channel → gunakan default channel setting
- Jika Tripay API error → fallback ke channel backup

### Features

#### Smart Fee Display
- **Real-time fee calculation** dari Tripay API
- **Total amount preview** (nominal + fee)
- **Free channel indicator** untuk channel tanpa biaya
- **Fee comparison** antar channel

#### Admin Control
- **Channel whitelist** - hanya channel yang diizinkan admin
- **Default channel** untuk user yang tidak memilih
- **Live channel sync** dengan Tripay API
- **Channel availability** auto-check

#### User Experience  
- **Visual channel selection** dengan inline keyboard
- **Fee transparency** - user tahu biaya sebelum bayar
- **Quick default option** - skip selection dengan default
- **Channel-specific invoice** dengan logo dan instruksi

### Testing Payment Channels

```bash
# Test all channel functions
python test_payment_channels.py

# Expected output:
✅ Retrieved 15 channels from Tripay
✅ Filtered to 3 active channels
✅ QRIS: Fee = Rp 0, Total = Rp 50,000  
✅ BCAVA: Fee = Rp 2,500, Total = Rp 52,500
✅ Channel setting verification passed
✅ Transaction created with reference: TR123...
✅ All payment channels tests completed!
```

## 🔐 Sistem Admin

### Setup Admin
1. **Dapatkan User ID Telegram Anda:**
   - Kirim pesan ke @userinfobot di Telegram
   - Atau gunakan @getmyid_bot
   - Catat User ID yang diberikan

2. **Konfigurasi Admin di .env:**
   ```env
   ADMIN_USER_IDS=123456789,987654321
   ```
   (Pisahkan multiple admin dengan koma)

3. **Test Admin Access:**
   ```bash
   python test_admin.py  # Test environment
   ```

### Fitur Admin

#### 🛍️ Manajemen Produk
- **Tambah Produk:** `/addproduk` - Conversation handler untuk input step-by-step
- **Lihat Produk:** `/listproduk` - Menampilkan semua produk dengan status
- **Hapus Produk:** `/hapusproduk [ID]` - Menghapus produk dari database
- **Panel Produk:** Akses via `/admin` → Kelola Produk

#### 💰 Manajemen Saldo
- **Cari User:** `/caripengguna [USER_ID]` - Info lengkap user + riwayat
- **Ubah Saldo:** `/ubahsaldo [USER_ID] [NOMINAL]` - Tambah/kurangi saldo
- **Contoh:** `/ubahsaldo 123456789 50000` (tambah) atau `/ubahsaldo 123456789 -25000` (kurangi)

#### 📊 Monitoring & Statistik
- **Top-up Monitor:** `/topupmasuk` - Status pembayaran Tripay real-time
- **Penjualan Monitor:** `/penjualan` - Transaksi pembelian terbaru
- **Statistik:** Akses via `/admin` → Statistik
  - Total users, produk, pendapatan
  - Data harian dan historical

#### 🔒 Autentikasi
- Hanya user dengan ID di `ADMIN_USER_IDS` yang bisa akses
- Otomatis block non-admin dengan pesan error
- Support multiple admin

### Contoh Workflow Admin

1. **Menambah Produk:**
   ```
   /addproduk
   → Nama: Netflix Premium 1 Bulan
   → Harga: 50000
   → Deskripsi: Akun Netflix Premium
   → Stok: 10
   → Pengiriman: Manual
   ```

2. **Monitor Top-up:**
   ```
   /topupmasuk
   → Melihat status PAID/UNPAID/EXPIRED
   → User yang melakukan top-up
   → Nominal dan waktu
   ```

3. **Kelola User:**
   ```
   /caripengguna 123456789
   → Info user, saldo, riwayat
   /ubahsaldo 123456789 100000
   → Menambah Rp 100,000
   ```

## 🔧 Troubleshooting

### Bot Tidak Merespon
1. Pastikan BOT_TOKEN benar
2. Cek koneksi internet
3. Lihat log error di console

### Admin Tidak Bisa Akses
1. Pastikan User ID benar di ADMIN_USER_IDS
2. Restart bot setelah mengubah .env
3. Test dengan `python test_admin.py`

### Pembayaran Tidak Diproses
1. Pastikan webhook URL dapat diakses dari internet
2. Cek signature verification
3. Pastikan database dapat diakses
4. Lihat log di webhook handler

### Error Database
1. Pastikan file database dapat ditulis
2. Cek permission folder
3. Jalankan `await db.init_db()` untuk inisialisasi

## 📞 Dukungan

### Log Sistem
Bot mencatat semua aktivitas penting. Gunakan level logging `INFO` untuk monitoring:

```python
logging.basicConfig(level=logging.INFO)
```

### Monitoring Transaksi
- Semua transaksi dicatat di database
- Admin mendapat notifikasi untuk pembelian manual
- User mendapat notifikasi untuk setiap perubahan saldo

## 🔐 Keamanan

### Signature Verification
- Semua webhook Tripay diverifikasi signature-nya
- Menggunakan HMAC SHA256
- Private key harus dijaga kerahasiaannya

### Database Security
- Gunakan environment variables untuk konfigurasi sensitif
- Jangan commit file `.env` ke repository
- Backup database secara berkala

## 📈 Pengembangan Lanjutan

### Fitur yang Bisa Ditambahkan
- Panel admin via web
- Sistem referral
- Diskon dan promo
- Integrasi payment gateway lain
- Sistem tier membership
- Analytics dan reporting

### API Extensions
- RESTful API untuk manajemen produk
- Integration dengan sistem inventory
- Multi-tenant support
- Advanced reporting

## 📄 Lisensi

Project ini menggunakan lisensi MIT. Silakan gunakan dan modifikasi sesuai kebutuhan.

## 🤝 Kontribusi

Kontribusi selalu diterima! Silakan:
1. Fork repository
2. Buat feature branch
3. Commit perubahan
4. Push ke branch
5. Buat Pull Request

---

**Dibuat dengan ❤️ untuk komunitas developer Indonesia** 