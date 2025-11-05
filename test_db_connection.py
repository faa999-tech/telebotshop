#!/usr/bin/env python3
"""
Test script untuk memverifikasi database connection fix
"""

import asyncio
import sys
from database import db
from admin_handlers import init_db_connection

async def test_db_connection():
    """Test database connection after fix"""
    print("🧪 Testing database connection fix...")
    print("=" * 50)
    
    try:
        # Initialize database
        await db.init_db()
        print("✅ Database initialized")
        
        # Initialize admin connection method
        await init_db_connection()
        print("✅ Admin database connection method initialized")
        
        # Test connection usage (similar to admin handlers)
        async with db._connect() as conn:
            conn.row_factory = db._Row
            
            # Simple test query
            cursor = await conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = await cursor.fetchall()
            
            print(f"✅ Database connection successful!")
            print(f"📊 Found {len(tables)} tables:")
            for table in tables:
                print(f"   • {table[0]}")
        
        # Test a more complex query (like in admin handlers)
        async with db._connect() as conn:
            conn.row_factory = db._Row
            cursor = await conn.execute("""
                SELECT COUNT(*) as count 
                FROM tripay_transactions 
                WHERE status = 'UNPAID'
            """)
            result = await cursor.fetchone()
            unpaid_count = result[0] if result else 0
            
            print(f"✅ Complex query successful!")
            print(f"💳 Unpaid transactions: {unpaid_count}")
        
        print("\n🎉 All database connection tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Database connection test failed: {e}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function"""
    success = await test_db_connection()
    
    if success:
        print("\n✅ Database connection fix is working properly!")
        print("🚀 Bot should now work without database errors.")
    else:
        print("\n❌ Database connection fix needs more work.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 