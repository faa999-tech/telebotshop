import json
import asyncio
from datetime import datetime
from aiohttp import web, ClientSession
from aiohttp.web_request import Request

import config
from database import db
from tripay import tripay
from main import bot

async def handle_tripay_callback(request: Request):
    """Handle Tripay payment callback"""
    try:
        # Get raw body and signature
        raw_body = await request.text()
        callback_signature = request.headers.get('X-Callback-Signature', '')
        
        # Verify signature
        if not tripay.verify_callback_signature(callback_signature, raw_body):
            print("Invalid callback signature")
            return web.Response(status=400, text="Invalid signature")
        
        # Parse callback data
        callback_data = json.loads(raw_body)
        
        # Extract transaction info
        reference = callback_data.get('reference')
        status = callback_data.get('status')
        
        if not reference or not status:
            print("Missing reference or status in callback")
            return web.Response(status=400, text="Missing data")
        
        # Get transaction from database
        transaction = await db.get_tripay_transaction(reference)
        
        if not transaction:
            print(f"Transaction not found: {reference}")
            return web.Response(status=404, text="Transaction not found")
        
        # Update transaction status
        await db.update_tripay_transaction_status(reference, status)
        
        # If payment is successful, add balance to user
        if status == 'PAID':
            # Add balance to user account
            success = await db.update_user_balance(transaction['user_id'], transaction['amount'])
            
            if success:
                # Create transaction record
                await db.create_transaction(
                    user_id=transaction['user_id'],
                    transaction_type="topup",
                    amount=transaction['amount'],
                    description=f"Top Up via Tripay - {reference}",
                    reference_id=reference
                )
                
                # Notify user
                try:
                    text = f"✅ <b>Top Up Berhasil!</b>\n\n"
                    text += f"💰 Nominal: <b>{format_currency(transaction['amount'])}</b>\n"
                    text += f"📋 Reference: <code>{reference}</code>\n"
                    text += f"⏰ Waktu: <b>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</b>\n\n"
                    text += f"💳 Saldo telah ditambahkan ke akun Anda!"
                    
                    await bot.send_message(
                        transaction['user_id'], 
                        text, 
                        parse_mode="HTML"
                    )
                except Exception as e:
                    print(f"Failed to notify user {transaction['user_id']}: {e}")
        
        elif status in ['EXPIRED', 'FAILED']:
            # Notify user about failed/expired payment
            try:
                if status == 'EXPIRED':
                    text = f"⏰ <b>Pembayaran Kedaluwarsa</b>\n\n"
                    text += f"📋 Reference: <code>{reference}</code>\n"
                    text += f"💰 Nominal: <b>{format_currency(transaction['amount'])}</b>\n\n"
                    text += f"Pembayaran telah kedaluwarsa. Silakan buat transaksi baru jika masih diperlukan."
                else:
                    text = f"❌ <b>Pembayaran Gagal</b>\n\n"
                    text += f"📋 Reference: <code>{reference}</code>\n"
                    text += f"💰 Nominal: <b>{format_currency(transaction['amount'])}</b>\n\n"
                    text += f"Pembayaran gagal diproses. Silakan coba lagi atau hubungi admin."
                
                await bot.send_message(
                    transaction['user_id'],
                    text,
                    parse_mode="HTML"
                )
            except Exception as e:
                print(f"Failed to notify user {transaction['user_id']}: {e}")
        
        return web.Response(status=200, text="OK")
        
    except Exception as e:
        print(f"Error handling callback: {e}")
        return web.Response(status=500, text="Internal server error")

async def handle_payment_return(request: Request):
    """Handle payment return from Tripay"""
    try:
        # Get reference from query parameters
        reference = request.query.get('reference')
        
        if not reference:
            return web.Response(
                status=400, 
                text="Missing reference parameter",
                content_type="text/html"
            )
        
        # Get transaction details from Tripay
        transaction_detail = await tripay.get_transaction_detail(reference)
        
        if not transaction_detail:
            return web.Response(
                status=404,
                text="Transaction not found",
                content_type="text/html"
            )
        
        # Generate return page
        status = transaction_detail.get('status', 'UNKNOWN')
        amount = transaction_detail.get('amount', 0)
        
        if status == 'PAID':
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Pembayaran Berhasil</title>
                <style>
                    body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                    .success {{ color: #28a745; }}
                    .container {{ max-width: 500px; margin: 0 auto; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1 class="success">✅ Pembayaran Berhasil!</h1>
                    <p>Reference: <strong>{reference}</strong></p>
                    <p>Nominal: <strong>{format_currency(amount)}</strong></p>
                    <p>Saldo telah ditambahkan ke akun Telegram Anda.</p>
                    <p>Silakan kembali ke bot untuk melanjutkan.</p>
                </div>
            </body>
            </html>
            """
        elif status == 'UNPAID':
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Menunggu Pembayaran</title>
                <style>
                    body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                    .pending {{ color: #ffc107; }}
                    .container {{ max-width: 500px; margin: 0 auto; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1 class="pending">⏳ Menunggu Pembayaran</h1>
                    <p>Reference: <strong>{reference}</strong></p>
                    <p>Nominal: <strong>{format_currency(amount)}</strong></p>
                    <p>Pembayaran Anda sedang diproses.</p>
                    <p>Saldo akan otomatis ditambahkan setelah pembayaran dikonfirmasi.</p>
                </div>
            </body>
            </html>
            """
        else:
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Status Pembayaran</title>
                <style>
                    body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                    .error {{ color: #dc3545; }}
                    .container {{ max-width: 500px; margin: 0 auto; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1 class="error">❌ Pembayaran Tidak Berhasil</h1>
                    <p>Reference: <strong>{reference}</strong></p>
                    <p>Status: <strong>{status}</strong></p>
                    <p>Silakan coba lagi atau hubungi admin jika ada masalah.</p>
                </div>
            </body>
            </html>
            """
        
        return web.Response(
            text=html_content,
            content_type="text/html"
        )
        
    except Exception as e:
        print(f"Error handling payment return: {e}")
        return web.Response(
            status=500,
            text="Internal server error",
            content_type="text/html"
        )

def format_currency(amount: int) -> str:
    """Format amount to IDR currency"""
    return f"Rp {amount:,}".replace(',', '.')

async def create_webhook_app():
    """Create webhook application"""
    app = web.Application()
    
    # Add routes
    app.router.add_post('/webhook/tripay', handle_tripay_callback)
    app.router.add_get('/payment-return', handle_payment_return)
    
    # Health check endpoint
    app.router.add_get('/health', lambda request: web.Response(text="OK"))
    
    return app

async def run_webhook_server():
    """Run webhook server"""
    app = await create_webhook_app()
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, '0.0.0.0', config.WEBHOOK_PORT)
    await site.start()
    
    print(f"Webhook server started on port {config.WEBHOOK_PORT}")
    
    # Keep the server running
    try:
        while True:
            await asyncio.sleep(3600)  # Sleep for 1 hour
    except KeyboardInterrupt:
        print("Shutting down webhook server...")
    finally:
        await runner.cleanup()

if __name__ == "__main__":
    asyncio.run(run_webhook_server()) 