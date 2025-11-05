#!/usr/bin/env python3
"""
Database management utility for Telegram Bot
"""

import asyncio
import json
import sys
from datetime import datetime
from database import db

class DatabaseManager:
    def __init__(self):
        self.db = db
    
    async def init_database(self):
        """Initialize database"""
        await self.db.init_db()
        print("✅ Database initialized successfully!")
    
    async def show_users(self):
        """Show all users"""
        print("\n👥 Users in database:")
        print("-" * 50)
        
        async with self.db._aiosqlite.connect(self.db.db_path) as conn:
            conn.row_factory = self.db._aiosqlite.Row
            cursor = await conn.execute("SELECT * FROM users ORDER BY created_at DESC")
            users = await cursor.fetchall()
            
            if not users:
                print("No users found.")
                return
            
            for user in users:
                print(f"ID: {user['user_id']}")
                print(f"Username: @{user['username'] or 'N/A'}")
                print(f"Name: {user['first_name']}")
                print(f"Balance: Rp {user['balance']:,}")
                print(f"Joined: {user['created_at']}")
                print("-" * 30)
    
    async def show_products(self):
        """Show all products"""
        products = await self.db.get_products(active_only=False)
        
        print("\n🛍️ Products in database:")
        print("-" * 50)
        
        if not products:
            print("No products found.")
            return
        
        for product in products:
            status = "✅ Active" if product['is_active'] else "❌ Inactive"
            stock = f"{product['stock']}" if product['stock'] != -1 else "Unlimited"
            
            print(f"ID: {product['id']}")
            print(f"Name: {product['name']}")
            print(f"Price: Rp {product['price']:,}")
            print(f"Stock: {stock}")
            print(f"Status: {status}")
            print(f"Description: {product['description']}")
            print("-" * 30)
    
    async def show_transactions(self, limit=20):
        """Show recent transactions"""
        print(f"\n💳 Recent {limit} transactions:")
        print("-" * 60)
        
        async with self.db._aiosqlite.connect(self.db.db_path) as conn:
            conn.row_factory = self.db._aiosqlite.Row
            cursor = await conn.execute("""
                SELECT t.*, u.username, u.first_name 
                FROM transactions t 
                JOIN users u ON t.user_id = u.user_id 
                ORDER BY t.created_at DESC 
                LIMIT ?
            """, (limit,))
            transactions = await cursor.fetchall()
            
            if not transactions:
                print("No transactions found.")
                return
            
            for txn in transactions:
                icon = "💳" if txn['transaction_type'] == 'topup' else "🛍️"
                amount_str = f"+Rp {txn['amount']:,}" if txn['transaction_type'] == 'topup' else f"-Rp {txn['amount']:,}"
                
                print(f"{icon} {txn['transaction_type'].title()}")
                print(f"User: {txn['first_name']} (@{txn['username'] or 'N/A'})")
                print(f"Amount: {amount_str}")
                print(f"Description: {txn['description']}")
                print(f"Status: {txn['status']}")
                print(f"Date: {txn['created_at']}")
                print("-" * 40)
    
    async def add_product(self):
        """Interactive product addition"""
        print("\n➕ Add New Product")
        print("-" * 30)
        
        try:
            name = input("Product name: ").strip()
            if not name:
                print("❌ Product name is required!")
                return
            
            description = input("Description: ").strip()
            
            price = int(input("Price (IDR): "))
            if price <= 0:
                print("❌ Price must be positive!")
                return
            
            stock_input = input("Stock (-1 for unlimited): ").strip()
            stock = int(stock_input) if stock_input else -1
            
            delivery = input("Delivery type (auto/manual) [auto]: ").strip().lower()
            delivery = delivery if delivery in ['auto', 'manual'] else 'auto'
            
            product_data = json.dumps({
                "type": "digital",
                "delivery": delivery
            })
            
            # Insert product
            async with self.db._aiosqlite.connect(self.db.db_path) as conn:
                cursor = await conn.execute("""
                    INSERT INTO products (name, description, price, stock, is_active, product_data)
                    VALUES (?, ?, ?, ?, 1, ?)
                """, (name, description, price, stock, product_data))
                await conn.commit()
                product_id = cursor.lastrowid
            
            print(f"✅ Product added successfully with ID: {product_id}")
            
        except ValueError:
            print("❌ Invalid input! Please enter valid numbers.")
        except Exception as e:
            print(f"❌ Error adding product: {e}")
    
    async def update_user_balance(self):
        """Update user balance"""
        print("\n💰 Update User Balance")
        print("-" * 30)
        
        try:
            user_id = int(input("User ID: "))
            amount = int(input("Amount to add (negative to subtract): "))
            description = input("Description: ").strip()
            
            # Update balance
            success = await self.db.update_user_balance(user_id, amount)
            
            if success:
                # Create transaction record
                txn_type = "topup" if amount > 0 else "deduction"
                await self.db.create_transaction(
                    user_id=user_id,
                    transaction_type=txn_type,
                    amount=abs(amount),
                    description=description or f"Manual {txn_type} by admin",
                    reference_id=f"ADMIN{int(datetime.now().timestamp())}"
                )
                
                new_balance = await self.db.get_user_balance(user_id)
                print(f"✅ Balance updated successfully!")
                print(f"New balance: Rp {new_balance:,}")
            else:
                print("❌ Failed to update balance. User might not exist.")
                
        except ValueError:
            print("❌ Invalid input! Please enter valid numbers.")
        except Exception as e:
            print(f"❌ Error updating balance: {e}")
    
    async def show_stats(self):
        """Show database statistics"""
        print("\n📊 Database Statistics")
        print("-" * 40)
        
        async with self.db._aiosqlite.connect(self.db.db_path) as conn:
            # Users count
            cursor = await conn.execute("SELECT COUNT(*) FROM users")
            users_count = (await cursor.fetchone())[0]
            
            # Products count
            cursor = await conn.execute("SELECT COUNT(*) FROM products WHERE is_active = 1")
            active_products = (await cursor.fetchone())[0]
            
            # Total transactions
            cursor = await conn.execute("SELECT COUNT(*) FROM transactions WHERE status = 'completed'")
            total_transactions = (await cursor.fetchone())[0]
            
            # Total revenue
            cursor = await conn.execute("SELECT SUM(amount) FROM transactions WHERE transaction_type = 'purchase' AND status = 'completed'")
            total_revenue = (await cursor.fetchone())[0] or 0
            
            # Total top-ups
            cursor = await conn.execute("SELECT SUM(amount) FROM transactions WHERE transaction_type = 'topup' AND status = 'completed'")
            total_topups = (await cursor.fetchone())[0] or 0
            
            print(f"👥 Total Users: {users_count}")
            print(f"🛍️ Active Products: {active_products}")
            print(f"💳 Total Transactions: {total_transactions}")
            print(f"💰 Total Revenue: Rp {total_revenue:,}")
            print(f"💵 Total Top-ups: Rp {total_topups:,}")

async def main():
    """Main menu"""
    manager = DatabaseManager()
    
    print("🗄️  Telegram Bot Database Manager")
    print("==================================")
    
    while True:
        print("\nSelect an option:")
        print("1. Initialize Database")
        print("2. Show Users")
        print("3. Show Products")
        print("4. Show Transactions")
        print("5. Add Product")
        print("6. Update User Balance")
        print("7. Show Statistics")
        print("0. Exit")
        
        choice = input("\nEnter your choice: ").strip()
        
        try:
            if choice == "1":
                await manager.init_database()
            elif choice == "2":
                await manager.show_users()
            elif choice == "3":
                await manager.show_products()
            elif choice == "4":
                limit = input("Number of transactions to show [20]: ").strip()
                limit = int(limit) if limit.isdigit() else 20
                await manager.show_transactions(limit)
            elif choice == "5":
                await manager.add_product()
            elif choice == "6":
                await manager.update_user_balance()
            elif choice == "7":
                await manager.show_stats()
            elif choice == "0":
                print("👋 Goodbye!")
                break
            else:
                print("❌ Invalid choice!")
                
        except Exception as e:
            print(f"❌ Error: {e}")
        
        input("\nPress Enter to continue...")

if __name__ == "__main__":
    # Fix import issue
    import aiosqlite
    db._aiosqlite = aiosqlite
    
    asyncio.run(main()) 