import aiosqlite
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
import config

class Database:
    def __init__(self, db_path: str = config.DATABASE_PATH):
        self.db_path = db_path

    async def init_db(self):
        """Initialize database tables"""
        async with aiosqlite.connect(self.db_path) as db:
            # Users table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    balance INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Products table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    price INTEGER NOT NULL,
                    stock INTEGER DEFAULT -1,
                    stock_units TEXT DEFAULT '[]',
                    is_active BOOLEAN DEFAULT 1,
                    product_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Transactions table (for top-ups and purchases)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    transaction_type TEXT NOT NULL,
                    amount INTEGER NOT NULL,
                    description TEXT,
                    reference_id TEXT,
                    stock_data TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            # Tripay transactions table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS tripay_transactions (
                    reference TEXT PRIMARY KEY,
                    user_id INTEGER,
                    amount INTEGER,
                    status TEXT DEFAULT 'UNPAID',
                    checkout_url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    paid_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            # Settings table for bot configuration
            await db.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await db.commit()
            
            # Add stock_units column if it doesn't exist (for backward compatibility)
            try:
                await db.execute("ALTER TABLE products ADD COLUMN stock_units TEXT DEFAULT '[]'")
                await db.commit()
            except:
                pass  # Column already exists
            
            # Add stock_data column to transactions if it doesn't exist
            try:
                await db.execute("ALTER TABLE transactions ADD COLUMN stock_data TEXT")
                await db.commit()
            except:
                pass  # Column already exists
            
            # Initialize default payment channels if not exists
            await self._init_default_channels(db)
            
            # Insert sample products if none exist
            await self._insert_sample_products(db)

    async def _insert_sample_products(self, db):
        """Insert sample products if products table is empty"""
        cursor = await db.execute("SELECT COUNT(*) FROM products")
        count = await cursor.fetchone()
        
        if count[0] == 0:
            sample_products = [
                ("Netflix Premium 1 Bulan", "Akun Netflix Premium untuk 1 bulan", 50000, 0, "[]", 1, json.dumps({"type": "digital", "delivery": "auto"})),
                ("Spotify Premium 1 Bulan", "Akun Spotify Premium untuk 1 bulan", 25000, 0, "[]", 1, json.dumps({"type": "digital", "delivery": "auto"})),
                ("Steam Wallet $10", "Steam Wallet senilai $10", 150000, 0, "[]", 1, json.dumps({"type": "digital", "delivery": "manual"})),
                ("Google Play Gift Card 100k", "Google Play Gift Card Rp 100.000", 110000, 0, "[]", 1, json.dumps({"type": "digital", "delivery": "manual"})),
            ]
            
            await db.executemany("""
                INSERT INTO products (name, description, price, stock, stock_units, is_active, product_data)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, sample_products)
            await db.commit()

    async def _init_default_channels(self, db):
        """Initialize default payment channels if not exists"""
        cursor = await db.execute("SELECT value FROM settings WHERE key = 'active_channels'")
        result = await cursor.fetchone()
        
        if not result:
            # Default active channels
            default_channels = ["QRIS", "BCAVA", "DANABALANCE"]
            await db.execute("""
                INSERT INTO settings (key, value) 
                VALUES ('active_channels', ?)
            """, (json.dumps(default_channels),))
            
            # Default channel (fallback if user doesn't choose)
            await db.execute("""
                INSERT INTO settings (key, value) 
                VALUES ('default_channel', 'QRIS')
            """)
            await db.commit()

    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM users WHERE user_id = ?", (user_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def create_user(self, user_id: int, username: str = None, first_name: str = None) -> bool:
        """Create new user"""
        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute(
                    "INSERT INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
                    (user_id, username, first_name)
                )
                await db.commit()
                return True
            except aiosqlite.IntegrityError:
                return False

    async def update_user_balance(self, user_id: int, amount: int) -> bool:
        """Update user balance (positive to add, negative to subtract)"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "UPDATE users SET balance = balance + ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                (amount, user_id)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def get_user_balance(self, user_id: int) -> int:
        """Get user current balance"""
        user = await self.get_user(user_id)
        return user['balance'] if user else 0

    async def get_products(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get all products"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            query = "SELECT * FROM products"
            params = ()
            
            if active_only:
                query += " WHERE is_active = 1"
            
            query += " ORDER BY id"
            
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_product(self, product_id: int) -> Optional[Dict[str, Any]]:
        """Get product by ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM products WHERE id = ?", (product_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def create_transaction(self, user_id: int, transaction_type: str, amount: int, 
                               description: str, reference_id: str = None, status: str = 'completed', stock_data: str = None) -> int:
        """Create new transaction record"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO transactions (user_id, transaction_type, amount, description, reference_id, stock_data, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, transaction_type, amount, description, reference_id, stock_data, status))
            await db.commit()
            return cursor.lastrowid

    async def get_user_transactions(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get user transaction history"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM transactions 
                WHERE user_id = ? AND status = 'completed'
                ORDER BY created_at DESC 
                LIMIT ?
            """, (user_id, limit))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def create_tripay_transaction(self, reference: str, user_id: int, amount: int, 
                                      checkout_url: str) -> bool:
        """Create Tripay transaction record"""
        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute("""
                    INSERT INTO tripay_transactions (reference, user_id, amount, checkout_url)
                    VALUES (?, ?, ?, ?)
                """, (reference, user_id, amount, checkout_url))
                await db.commit()
                return True
            except aiosqlite.IntegrityError:
                return False

    async def update_tripay_transaction_status(self, reference: str, status: str) -> bool:
        """Update Tripay transaction status"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                UPDATE tripay_transactions 
                SET status = ?, paid_at = CASE WHEN ? = 'PAID' THEN CURRENT_TIMESTAMP ELSE paid_at END
                WHERE reference = ?
            """, (status, status, reference))
            await db.commit()
            return cursor.rowcount > 0

    async def get_tripay_transaction(self, reference: str) -> Optional[Dict[str, Any]]:
        """Get Tripay transaction by reference"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM tripay_transactions WHERE reference = ?", (reference,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def update_product_stock(self, product_id: int, quantity: int) -> bool:
        """Update product stock (subtract quantity)"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                UPDATE products 
                SET stock = stock - ? 
                WHERE id = ? AND (stock >= ? OR stock = -1)
            """, (quantity, product_id, quantity))
            await db.commit()
            return cursor.rowcount > 0

    async def update_product_price(self, product_id: int, new_price: int) -> bool:
        """Update product price"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                UPDATE products 
                SET price = ?
                WHERE id = ?
            """, (new_price, product_id))
            await db.commit()
            return cursor.rowcount > 0

    async def add_stock_units(self, product_id: int, stock_units: List[str]) -> bool:
        """Add stock units to a product"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            # Get current stock units
            cursor = await db.execute("SELECT stock_units FROM products WHERE id = ?", (product_id,))
            row = await cursor.fetchone()
            
            if not row:
                return False
            
            # Parse current stock units
            current_units = json.loads(row['stock_units'] or '[]')
            
            # Add new units
            current_units.extend(stock_units)
            
            # Update database
            cursor = await db.execute("""
                UPDATE products 
                SET stock_units = ?, stock = ?
                WHERE id = ?
            """, (json.dumps(current_units), len(current_units), product_id))
            
            await db.commit()
            return cursor.rowcount > 0

    async def get_available_stock_count(self, product_id: int) -> int:
        """Get available stock count for a product"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT stock_units FROM products WHERE id = ?", (product_id,))
            row = await cursor.fetchone()
            
            if not row:
                return 0
            
            stock_units = json.loads(row['stock_units'] or '[]')
            return len(stock_units)

    async def consume_stock_unit(self, product_id: int) -> Optional[str]:
        """Consume one stock unit and return it"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            # Get current stock units
            cursor = await db.execute("SELECT stock_units FROM products WHERE id = ?", (product_id,))
            row = await cursor.fetchone()
            
            if not row:
                return None
            
            # Parse current stock units
            stock_units = json.loads(row['stock_units'] or '[]')
            
            if not stock_units:
                return None  # No stock available
            
            # Take first unit
            consumed_unit = stock_units.pop(0)
            
            # Update database
            cursor = await db.execute("""
                UPDATE products 
                SET stock_units = ?, stock = ?
                WHERE id = ?
            """, (json.dumps(stock_units), len(stock_units), product_id))
            
            await db.commit()
            return consumed_unit

    async def create_product_with_stock(self, name: str, description: str, price: int, 
                                      stock_units: List[str], is_active: bool = True, 
                                      product_data: str = None) -> int:
        """Create new product with stock units"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO products (name, description, price, stock, stock_units, is_active, product_data)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (name, description, price, len(stock_units), json.dumps(stock_units), is_active, product_data))
            await db.commit()
            return cursor.lastrowid

    async def get_product_stock_units(self, product_id: int) -> List[str]:
        """Get all stock units for a product"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT stock_units FROM products WHERE id = ?", (product_id,))
            row = await cursor.fetchone()
            
            if not row:
                return []
            
            return json.loads(row['stock_units'] or '[]')

    async def get_setting(self, key: str) -> Optional[str]:
        """Get setting value by key"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = await cursor.fetchone()
            return row['value'] if row else None

    async def set_setting(self, key: str, value: str) -> bool:
        """Set setting value"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT OR REPLACE INTO settings (key, value, updated_at) 
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (key, value))
            await db.commit()
            return cursor.rowcount > 0

    async def get_active_channels(self) -> List[str]:
        """Get list of active payment channels"""
        channels_json = await self.get_setting('active_channels')
        if channels_json:
            try:
                return json.loads(channels_json)
            except:
                pass
        return ["QRIS", "BCAVA", "DANABALANCE"]  # Default fallback

    async def set_active_channels(self, channels: List[str]) -> bool:
        """Set active payment channels"""
        return await self.set_setting('active_channels', json.dumps(channels))

    async def get_default_channel(self) -> str:
        """Get default payment channel"""
        channel = await self.get_setting('default_channel')
        return channel if channel else "QRIS"

    async def set_default_channel(self, channel: str) -> bool:
        """Set default payment channel"""
        return await self.set_setting('default_channel', channel)

    async def deduct_balance_if_sufficient(self, user_id: int, amount: int) -> bool:
        """Atomically deduct balance only if user has sufficient funds"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                UPDATE users 
                SET balance = balance - ?, updated_at = CURRENT_TIMESTAMP 
                WHERE user_id = ? AND balance >= ?
            """, (amount, user_id, amount))
            await db.commit()
            return cursor.rowcount > 0

    async def get_user_profile_stats(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get comprehensive user profile statistics"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            # Get user basic info
            user = await self.get_user(user_id)
            if not user:
                return None
            
            # Get purchase statistics
            cursor = await db.execute("""
                SELECT 
                    COUNT(*) as total_purchases,
                    COALESCE(SUM(amount), 0) as total_spent
                FROM transactions 
                WHERE user_id = ? AND transaction_type = 'purchase' AND status = 'completed'
            """, (user_id,))
            purchase_stats = await cursor.fetchone()
            
            # Get top-up statistics from tripay_transactions (PAID status)
            cursor = await db.execute("""
                SELECT 
                    COUNT(*) as total_topups,
                    COALESCE(SUM(amount), 0) as total_topup_amount
                FROM tripay_transactions 
                WHERE user_id = ? AND status = 'PAID'
            """, (user_id,))
            topup_stats = await cursor.fetchone()
            
            # Get total transactions from transactions table (for additional topups)
            cursor = await db.execute("""
                SELECT 
                    COUNT(*) as manual_topups,
                    COALESCE(SUM(amount), 0) as manual_topup_amount
                FROM transactions 
                WHERE user_id = ? AND transaction_type = 'topup' AND status = 'completed'
            """, (user_id,))
            manual_topup_stats = await cursor.fetchone()
            
            return {
                'user_info': user,
                'total_purchases': purchase_stats['total_purchases'],
                'total_spent': purchase_stats['total_spent'],
                'total_topups': topup_stats['total_topups'] + manual_topup_stats['manual_topups'],
                'total_topup_amount': topup_stats['total_topup_amount'] + manual_topup_stats['manual_topup_amount']
            }

    async def get_user_by_id_detailed(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed user information including statistics"""
        return await self.get_user_profile_stats(user_id)

    async def migrate_balance_to_current_user(self, current_user_id: int, username: str, first_name: str) -> bool:
        """Migrate balance from duplicate users with the same username/first_name to the current user_id."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            # Find other users with the same username or first_name, but different user_id
            cursor = await db.execute(
                "SELECT user_id, balance FROM users WHERE (username = ? OR first_name = ?) AND user_id != ? AND balance > 0",
                (username, first_name, current_user_id)
            )
            rows = await cursor.fetchall()
            migrated = False
            for row in rows:
                other_user_id = row['user_id']
                other_balance = row['balance']
                if other_balance > 0:
                    # Transfer balance
                    await db.execute(
                        "UPDATE users SET balance = balance - ? WHERE user_id = ?",
                        (other_balance, other_user_id)
                    )
                    await db.execute(
                        "UPDATE users SET balance = balance + ? WHERE user_id = ?",
                        (other_balance, current_user_id)
                    )
                    # Log transaction for both users
                    await db.execute(
                        "INSERT INTO transactions (user_id, transaction_type, amount, description, reference_id, status) VALUES (?, ?, ?, ?, ?, 'completed')",
                        (other_user_id, 'deduction', other_balance, f'Migrasi saldo ke user_id {current_user_id}', f'MIGRATE{current_user_id}')
                    )
                    await db.execute(
                        "INSERT INTO transactions (user_id, transaction_type, amount, description, reference_id, status) VALUES (?, ?, ?, ?, ?, 'completed')",
                        (current_user_id, 'topup', other_balance, f'Migrasi saldo dari user_id {other_user_id}', f'MIGRATE{other_user_id}')
                    )
                    migrated = True
            await db.commit()
            return migrated

# Global database instance
db = Database() 