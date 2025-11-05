#!/usr/bin/env python3
"""
Script to run both Telegram bot and webhook handler simultaneously
"""

import asyncio
import logging
import signal
import sys
from concurrent.futures import ThreadPoolExecutor

# Import modules
from main import main as run_bot
from webhook_handler import run_webhook_server
from database import db

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BotRunner:
    def __init__(self):
        self.tasks = []
        self.running = True
        
    async def start(self):
        """Start both bot and webhook server"""
        logger.info("🚀 Starting Telegram Bot with Webhook Handler...")
        
        # Initialize database
        await db.init_db()
        logger.info("✅ Database initialized")
        
        try:
            # Create tasks for bot and webhook
            bot_task = asyncio.create_task(run_bot(), name="telegram-bot")
            webhook_task = asyncio.create_task(run_webhook_server(), name="webhook-server")
            
            self.tasks = [bot_task, webhook_task]
            
            logger.info("✅ Bot and webhook server started successfully!")
            logger.info("📱 Bot is ready to receive messages")
            logger.info("🌐 Webhook server is listening for payment notifications")
            logger.info("🔄 Press Ctrl+C to stop")
            
            # Wait for both tasks
            await asyncio.gather(*self.tasks)
            
        except asyncio.CancelledError:
            logger.info("🛑 Shutting down...")
        except Exception as e:
            logger.error(f"❌ Error running bot: {e}")
            raise
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """Cleanup resources"""
        logger.info("🧹 Cleaning up resources...")
        
        # Cancel all tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        logger.info("✅ Cleanup completed")
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"📡 Received signal {signum}, shutting down gracefully...")
        self.running = False
        
        # Cancel all tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()

def main():
    """Main function"""
    runner = BotRunner()
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, runner.signal_handler)
    signal.signal(signal.SIGTERM, runner.signal_handler)
    
    try:
        # Run the bot
        asyncio.run(runner.start())
    except KeyboardInterrupt:
        logger.info("🛑 Interrupted by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)
    
    logger.info("👋 Bot stopped")

if __name__ == "__main__":
    main() 