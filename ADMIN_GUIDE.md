# 🔐 Panduan Lengkap Sistem Admin

## 📋 Daftar Isi
1. [Setup Admin](#setup-admin)
2. [Command Reference](#command-reference)
3. [Workflow Examples](#workflow-examples)
4. [Troubleshooting](#troubleshooting)

## 🚀 Setup Admin

### 1. Mendapatkan User ID Telegram
Untuk menjadi admin, Anda perlu mengetahui User ID Telegram Anda:

**Option A: Menggunakan Bot @userinfobot**
1. Buka Telegram
2. Cari @userinfobot
3. Kirim `/start`
4. Bot akan mengirim User ID Anda

**Option B: Menggunakan Bot @getmyid_bot**
1. Cari @getmyid_bot di Telegram
2. Kirim pesan apa saja
3. Bot akan reply dengan User ID

**Option C: Melalui Bot Shop (untuk testing)**
1. Kirim `/start` ke bot shop Anda
2. Lihat log di console, akan muncul:
   ```
   User ID: 123456789 started the bot
   ```

### 2. Konfigurasi Admin
Edit file `.env`:
```env
# Single admin
ADMIN_USER_IDS=123456789

# Multiple admin (pisahkan dengan koma)
ADMIN_USER_IDS=123456789,987654321,555666777
```

### 3. Test Setup
Jalankan test script:
```bash
python test_admin.py
```

Output yang diharapkan:
```
🤖 Telegram Bot Admin System Test
🧪 Testing Admin Functions...
✅ Database initialized
✅ Admin user created with ID: 123456789
✅ Regular user created with ID: 555666777 and balance: Rp 100,000
✅ Found 4 existing products
✅ Sample transactions created
📊 Database Statistics:
👥 Total Users: 2
🛍️ Total Products: 4
💳 Total Transactions: 2
✅ All tests completed successfully!
```

## 📝 Command Reference

### Akses Admin
```
/admin
```
**Output:** Menu utama admin dengan inline keyboard

### Manajemen Produk

#### Tambah Produk
```
/addproduk
```
**Flow:**
1. Bot: "Masukkan nama produk:"
2. User: "Netflix Premium 1 Bulan"
3. Bot: "Masukkan harga produk (dalam IDR):"
4. User: "50000"
5. Bot: "Masukkan deskripsi produk:"
6. User: "Akun Netflix Premium untuk 1 bulan"
7. Bot: "Masukkan jumlah stok:"
8. User: "10" (atau "-1" untuk unlimited)
9. Bot: Pilihan "Otomatis" atau "Manual" untuk pengiriman
10. Bot: "✅ Produk Berhasil Ditambahkan!"

#### Lihat Semua Produk
```
/listproduk
```
**Output:**
```
🛍️ Daftar Produk

✅ ID 1: Netflix Premium 1 Bulan
💰 Rp 50,000 | 📦 Stok: 10
📝 Akun Netflix Premium untuk 1 bulan

✅ ID 2: Spotify Premium 1 Bulan
💰 Rp 25,000 | 📦 Stok: ∞
📝 Akun Spotify Premium untuk 1 bulan
```

#### Hapus Produk
```
/hapusproduk 1
```
**Output:**
```
✅ Produk Berhasil Dihapus!
🆔 ID: 1
📦 Nama: Netflix Premium 1 Bulan
💰 Harga: Rp 50,000
```

### Manajemen Saldo

#### Cari Info User
```
/caripengguna 123456789
```
**Output:**
```
👤 Info Pengguna

🆔 ID: 123456789
👤 Username: @john_doe
📝 Nama: John Doe
💰 Saldo: Rp 75,000
📅 Bergabung: 2024-01-15 10:30:00

📊 5 Transaksi Terakhir:
💳 +Rp 100,000 - Top Up via Tripay - TU123...
🛍️ -Rp 25,000 - Pembelian Spotify Premium...
💳 +Rp 50,000 - Manual topup oleh admin...
```

#### Ubah Saldo User
```
# Menambah saldo
/ubahsaldo 123456789 50000

# Mengurangi saldo
/ubahsaldo 123456789 -25000
```
**Output:**
```
✅ Saldo Berhasil Diubah!
👤 User: John Doe
🆔 ID: 123456789
💰 Perubahan: +Rp 50,000
💳 Saldo Baru: Rp 125,000
```

### Monitoring

#### Monitor Top-up Masuk
```
/topupmasuk
```
**Output:**
```
💳 Monitoring Top-up

✅ PAID
👤 John Doe (@john_doe)
💰 Rp 100,000
📋 TU12345678901234567890
📅 2024-01-15 14:30:00

⏳ UNPAID
👤 Jane Smith (@jane_smith)
💰 Rp 50,000
📋 TU09876543210987654321
📅 2024-01-15 15:00:00
```

#### Monitor Penjualan
```
/penjualan
```
**Output:**
```
🛍️ Monitoring Penjualan

🛍️ Pembelian
👤 John Doe (@john_doe)
💰 Rp 50,000
📝 Pembelian Netflix Premium 1 Bulan
📅 2024-01-15 16:00:00

🛍️ Pembelian
👤 Jane Smith (@jane_smith)
💰 Rp 25,000
📝 Pembelian Spotify Premium 1 Bulan
📅 2024-01-15 16:15:00
```

## 🎯 Workflow Examples

### Scenario 1: Menambah Produk Game
```
Admin: /addproduk
Bot: Masukkan nama produk:
Admin: Steam Wallet $20
Bot: Masukkan harga produk (dalam IDR):
Admin: 300000
Bot: Masukkan deskripsi produk:
Admin: Steam Wallet senilai $20 untuk pembelian game
Bot: Masukkan jumlah stok:
Admin: 5
Bot: Pilih jenis pengiriman: [Otomatis] [Manual]
Admin: [Klik Manual]
Bot: ✅ Produk Berhasil Ditambahkan!
```

### Scenario 2: Handle Komplain User
```
User (via chat): "Saldo saya hilang!"
Admin: /caripengguna 123456789
Bot: [Menampilkan info user dan riwayat]
Admin: [Melihat transaksi terakhir, ternyata user beli produk]
Admin: [Menjelaskan ke user bahwa saldo terpotong untuk pembelian]
```

### Scenario 3: Bonus Saldo Event
```
Admin: /caripengguna 123456789
Bot: [Info user]
Admin: /ubahsaldo 123456789 10000
Bot: ✅ Saldo Berhasil Diubah! ... Saldo Baru: Rp 85,000
Admin: [Kirim pesan manual ke user tentang bonus]
```

### Scenario 4: Monitoring Harian
```
Admin: /admin
Bot: [Panel Admin]
Admin: [Klik "📈 Statistik"]
Bot: 
📈 Statistik Toko
👥 Total User: 45
🛍️ Produk Aktif: 8
💰 Total Pendapatan: Rp 2,450,000
💳 Total Top-up: Rp 3,100,000
⏳ Top-up Pending: 3
📅 Hari Ini:
🛍️ Penjualan: 12 transaksi
💰 Pendapatan: Rp 180,000
```

## 🚨 Error Handling

### Error: "❌ Akses Ditolak!"
**Penyebab:** User bukan admin
**Solusi:** 
1. Pastikan User ID benar di ADMIN_USER_IDS
2. Restart bot setelah edit .env
3. Check dengan `python test_admin.py`

### Error: Database connection failed
**Penyebab:** Database tidak bisa diakses
**Solusi:**
1. Pastikan file database ada dan writable
2. Jalankan `python db_manager.py` → option 1 (Initialize Database)
3. Check permission folder

### Error: "Produk tidak ditemukan"
**Penyebab:** ID produk tidak ada
**Solusi:**
1. Gunakan `/listproduk` untuk cek ID yang valid
2. Pastikan produk belum dihapus

## 💡 Tips & Best Practices

### 1. Keamanan Admin
- Jangan share User ID admin
- Gunakan multiple admin untuk backup
- Monitor aktivitas admin di log

### 2. Manajemen Produk
- Gunakan nama produk yang jelas dan descriptive
- Set stok realistis untuk produk terbatas
- Update harga secara berkala

### 3. Customer Service
- Selalu cek riwayat user sebelum ubah saldo
- Dokumentasikan alasan perubahan saldo
- Respond cepat ke komplain user

### 4. Monitoring
- Cek `/topupmasuk` secara berkala untuk payment yang stuck
- Monitor `/penjualan` untuk trend produk
- Review statistik harian untuk business insight

## 🔧 Advanced Features

### Custom Database Queries
Untuk query custom, gunakan `db_manager.py`:
```bash
python db_manager.py
# Pilih option sesuai kebutuhan
```

### Backup Database
```bash
# Backup database
cp bot_database.db backup_$(date +%Y%m%d).db

# Restore database
cp backup_20240115.db bot_database.db
```

### Export Data
Untuk export data ke CSV atau Excel, bisa extend `db_manager.py` dengan function tambahan.

---

## 📞 Support

Jika mengalami masalah:
1. Check log console untuk error details
2. Jalankan `python test_admin.py` untuk diagnosis
3. Review konfigurasi di `.env`
4. Pastikan bot token dan Tripay API valid

**Happy Administrating! 🎉** 