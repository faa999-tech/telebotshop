#!/usr/bin/env python3
"""
Test script untuk memverifikasi perbaikan fitur edit harga
"""

import asyncio
import sys
from database import db
from admin_handlers import init_db_connection

async def test_edit_price_fix():
    """Test edit price fix (tanpa updated_at column)"""
    print("🔧 Testing Edit Price Fix...")
    print("=" * 50)
    
    try:
        # Initialize database and admin connection
        await db.init_db()
        await init_db_connection()
        print("✅ Database initialized")
        
        # Create test product
        print("\n📝 Creating test product...")
        async with db._connect() as conn:
            cursor = await conn.execute("""
                INSERT INTO products (name, description, price, stock, is_active)
                VALUES (?, ?, ?, ?, ?)
            """, ("Test Product Fix", "Test for edit price fix", 15000, 10, True))
            await conn.commit()
            test_product_id = cursor.lastrowid
            
        print(f"✅ Test product created with ID: {test_product_id}")
        
        # Get original product
        original_product = await db.get_product(test_product_id)
        original_price = original_product['price']
        print(f"   Original price: Rp {original_price:,}")
        
        # Test update price (this should work now)
        new_price = 25000
        print(f"\n🔄 Updating price to Rp {new_price:,}...")
        
        success = await db.update_product_price(test_product_id, new_price)
        
        if success:
            # Verify the update
            updated_product = await db.get_product(test_product_id)
            updated_price = updated_product['price']
            
            if updated_price == new_price:
                print(f"✅ SUCCESS! Price updated: Rp {original_price:,} -> Rp {updated_price:,}")
                
                # Test another update to make sure it works consistently
                final_price = 30000
                success2 = await db.update_product_price(test_product_id, final_price)
                
                if success2:
                    final_product = await db.get_product(test_product_id)
                    print(f"✅ Second update successful: Rp {updated_price:,} -> Rp {final_product['price']:,}")
                else:
                    print("❌ Second update failed")
            else:
                print(f"❌ Price not updated correctly. Expected {new_price}, got {updated_price}")
                return False
        else:
            print("❌ Database method failed: update_product_price returned False")
            return False
        
        # Test with invalid product ID
        print("\n🧪 Testing with invalid product ID...")
        invalid_result = await db.update_product_price(999999, 50000)
        if not invalid_result:
            print("✅ Invalid product ID handled correctly")
        else:
            print("❌ Invalid product ID should return False")
        
        # Cleanup
        print("\n🧹 Cleaning up test product...")
        async with db._connect() as conn:
            await conn.execute("DELETE FROM products WHERE id = ?", (test_product_id,))
            await conn.commit()
        print("✅ Test product cleaned up")
        
        print("\n🎉 Edit price fix successful!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function"""
    print("🚀 Testing Edit Price Fix")
    print("=" * 40)
    
    success = await test_edit_price_fix()
    
    if success:
        print("\n✅ Edit Price Feature is now working!")
        print("\n📋 What was fixed:")
        print("• ❌ Removed 'updated_at' column reference (doesn't exist)")
        print("• ✅ Database method now works properly")
        print("• ✅ Admin command /editharga should work")
        print("\n🎯 Ready to test with actual bot!")
    else:
        print("\n❌ Fix unsuccessful - still has issues")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 