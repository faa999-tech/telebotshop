#!/usr/bin/env python3
"""
Test script untuk menguji sistem stok produk bot Telegram
"""

import asyncio
import sys
import json
from database import db
import config

async def test_stock_system():
    """Test stock system functionality"""
    print("🧪 Testing Stock System...")
    print("=" * 50)
    
    # Initialize database
    await db.init_db()
    print("✅ Database initialized")
    
    # Test 1: Create product with stock units
    print("\n📝 Test 1: Creating product with stock units...")
    
    stock_units = [
        "user1@gmail.com:password123",
        "user2@gmail.com:password456", 
        "user3@gmail.com:password789",
        "user4@gmail.com:password101",
        "user5@gmail.com:password202"
    ]
    
    product_id = await db.create_product_with_stock(
        name="Test Netflix Account",
        description="Test account for stock system",
        price=50000,
        stock_units=stock_units,
        is_active=True,
        product_data=json.dumps({"type": "digital", "delivery": "auto"})
    )
    
    print(f"✅ Product created with ID: {product_id}")
    print(f"✅ Stock units added: {len(stock_units)}")
    
    # Test 2: Check stock count
    print("\n📝 Test 2: Checking stock count...")
    stock_count = await db.get_available_stock_count(product_id)
    print(f"✅ Available stock: {stock_count} units")
    
    # Test 3: Get stock units
    print("\n📝 Test 3: Getting stock units...")
    all_units = await db.get_product_stock_units(product_id)
    print(f"✅ Retrieved {len(all_units)} stock units:")
    for i, unit in enumerate(all_units[:3]):
        print(f"   {i+1}. {unit}")
    if len(all_units) > 3:
        print(f"   ... and {len(all_units) - 3} more")
    
    # Test 4: Consume stock unit
    print("\n📝 Test 4: Consuming stock units...")
    for i in range(3):
        consumed = await db.consume_stock_unit(product_id)
        if consumed:
            print(f"✅ Consumed unit {i+1}: {consumed}")
        else:
            print(f"❌ Failed to consume unit {i+1}")
    
    # Check remaining stock
    remaining_stock = await db.get_available_stock_count(product_id)
    print(f"✅ Remaining stock: {remaining_stock} units")
    
    # Test 5: Add more stock units
    print("\n📝 Test 5: Adding more stock units...")
    additional_units = [
        "user6@gmail.com:password303",
        "user7@gmail.com:password404"
    ]
    
    success = await db.add_stock_units(product_id, additional_units)
    if success:
        print(f"✅ Added {len(additional_units)} additional units")
        final_stock = await db.get_available_stock_count(product_id)
        print(f"✅ Final stock count: {final_stock} units")
    else:
        print("❌ Failed to add additional units")
    
    # Test 6: Create test user and transaction
    print("\n📝 Test 6: Creating test transaction...")
    
    user_id = 999888777
    await db.create_user(
        user_id=user_id,
        username="test_buyer",
        first_name="Test Buyer"
    )
    
    # Add balance to user
    await db.update_user_balance(user_id, 100000)
    print(f"✅ Created test user with ID: {user_id} and balance: Rp 100,000")
    
    # Simulate purchase
    stock_unit = await db.consume_stock_unit(product_id)
    if stock_unit:
        await db.create_transaction(
            user_id=user_id,
            transaction_type="purchase",
            amount=50000,
            description="Test purchase with stock",
            reference_id="TEST123",
            stock_data=stock_unit
        )
        
        await db.update_user_balance(user_id, -50000)
        print(f"✅ Purchase transaction created with stock data: {stock_unit}")
    else:
        print("❌ No stock available for purchase")
    
    # Test 7: Get transaction history with stock data
    print("\n📝 Test 7: Getting transaction history...")
    transactions = await db.get_user_transactions(user_id)
    
    for txn in transactions:
        print(f"📄 Transaction: {txn['description']}")
        print(f"   💰 Amount: Rp {txn['amount']:,}")
        print(f"   📦 Stock Data: {txn.get('stock_data', 'N/A')}")
        print(f"   📅 Date: {txn['created_at']}")
    
    # Test 8: Try to consume more stock than available
    print("\n📝 Test 8: Testing stock exhaustion...")
    current_stock = await db.get_available_stock_count(product_id)
    print(f"Current stock: {current_stock}")
    
    # Try to consume all remaining stock
    consumed_count = 0
    while True:
        unit = await db.consume_stock_unit(product_id)
        if unit:
            consumed_count += 1
            print(f"   Consumed unit {consumed_count}: {unit[:20]}...")
        else:
            break
    
    final_stock = await db.get_available_stock_count(product_id)
    print(f"✅ Consumed {consumed_count} units, remaining: {final_stock}")
    
    # Try to consume when stock is empty
    empty_unit = await db.consume_stock_unit(product_id)
    if empty_unit:
        print("❌ ERROR: Should not be able to consume from empty stock!")
    else:
        print("✅ Correctly returned None for empty stock")
    
    print("\n✅ All stock system tests completed!")
    print("\n📋 Summary:")
    print(f"- Product created with ID: {product_id}")
    print(f"- Initial stock: {len(stock_units)} units")
    print(f"- Additional stock added: {len(additional_units)} units")
    print(f"- Total consumed: {consumed_count + 1} units")
    print(f"- Final remaining: {final_stock} units")
    print(f"- Test user purchases: 1 transaction")
    
    print("\n🎯 Next steps:")
    print("1. Update .env with your bot token and admin IDs")
    print("2. Test admin commands like /addproduk and /addstock")
    print("3. Test user purchase flow with stock system")

async def setup_test_environment():
    """Setup test environment with sample data"""
    print("🔧 Setting up stock system test environment...")
    
    # Fix database connection for testing
    import aiosqlite
    
    async def _connect():
        return aiosqlite.connect(db.db_path)
    
    db._connect = _connect
    
    await test_stock_system()

if __name__ == "__main__":
    print("🤖 Telegram Bot Stock System Test")
    print("=" * 50)
    
    try:
        asyncio.run(setup_test_environment())
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 