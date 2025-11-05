#!/usr/bin/env python3
"""
Test script untuk menguji fungsi admin bot Telegram
"""

import asyncio
import sys
from database import db
import config

async def test_admin_functions():
    """Test admin database functions"""
    print("🧪 Testing Admin Functions...")
    print("=" * 50)
    
    # Initialize database
    await db.init_db()
    print("✅ Database initialized")
    
    # Test 1: Add sample admin user
    print("\n📝 Test 1: Creating sample admin user...")
    admin_id = config.ADMIN_USER_IDS[0] if config.ADMIN_USER_IDS else 123456789
    
    await db.create_user(
        user_id=admin_id,
        username="admin_test",
        first_name="Admin Test"
    )
    print(f"✅ Admin user created with ID: {admin_id}")
    
    # Test 2: Add sample regular user
    print("\n📝 Test 2: Creating sample regular user...")
    user_id = 555666777
    
    await db.create_user(
        user_id=user_id,
        username="test_user",
        first_name="Test User"
    )
    
    # Add some balance to the user
    await db.update_user_balance(user_id, 100000)
    print(f"✅ Regular user created with ID: {user_id} and balance: Rp 100,000")
    
    # Test 3: Add sample products
    print("\n📝 Test 3: Adding sample products...")
    products = await db.get_products()
    print(f"✅ Found {len(products)} existing products")
    
    # Test 4: Create sample transactions
    print("\n📝 Test 4: Creating sample transactions...")
    
    # Top-up transaction
    await db.create_transaction(
        user_id=user_id,
        transaction_type="topup",
        amount=50000,
        description="Manual top-up oleh admin",
        reference_id="ADMIN123"
    )
    
    # Purchase transaction
    if products:
        await db.create_transaction(
            user_id=user_id,
            transaction_type="purchase",
            amount=products[0]['price'],
            description=f"Pembelian {products[0]['name']}",
            reference_id="PUR123"
        )
        print(f"✅ Sample transactions created")
    
    # Test 5: Show admin info
    print("\n📝 Test 5: Admin info...")
    print(f"Admin User IDs: {config.ADMIN_USER_IDS}")
    print(f"Bot Token: {'*' * 20 + config.BOT_TOKEN[-10:] if len(config.BOT_TOKEN) > 20 else 'Not configured'}")
    print(f"Tripay API: {'Configured' if config.TRIPAY_API_KEY != 'YOUR_TRIPAY_API_KEY' else 'Not configured'}")
    
    # Test 6: Database statistics
    print("\n📊 Database Statistics:")
    
    async with db._connect() as conn:
        # Total users
        cursor = await conn.execute("SELECT COUNT(*) FROM users")
        total_users = (await cursor.fetchone())[0]
        
        # Total products
        cursor = await conn.execute("SELECT COUNT(*) FROM products")
        total_products = (await cursor.fetchone())[0]
        
        # Total transactions
        cursor = await conn.execute("SELECT COUNT(*) FROM transactions")
        total_transactions = (await cursor.fetchone())[0]
        
        print(f"👥 Total Users: {total_users}")
        print(f"🛍️ Total Products: {total_products}")
        print(f"💳 Total Transactions: {total_transactions}")
    
    print("\n✅ All tests completed successfully!")
    print("\n📋 Next steps:")
    print("1. Update .env file with your bot token and admin user IDs")
    print("2. Run: python main.py or python run_bot.py")
    print("3. Send /admin to your bot as an admin user")
    print("4. Test admin commands like /addproduk, /listproduk, etc.")

async def setup_test_environment():
    """Setup test environment with sample data"""
    print("🔧 Setting up test environment...")
    
    # Fix database connection for testing
    import aiosqlite
    
    async def _connect():
        return aiosqlite.connect(db.db_path)
    
    db._connect = _connect
    
    await test_admin_functions()

if __name__ == "__main__":
    print("🤖 Telegram Bot Admin System Test")
    print("=" * 50)
    
    try:
        asyncio.run(setup_test_environment())
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1) 