"""
Main Telegram bot entry point.
"""
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import settings
from api_client import api_client
from handlers import start, registration, test_entry, results, callbacks, payments


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Main bot function."""
    # Initialize bot and dispatcher
    bot = Bot(token=settings.BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Include routers (callbacks first to handle inline buttons)
    dp.include_router(callbacks.router)
    dp.include_router(payments.router)
    dp.include_router(start.router)
    dp.include_router(registration.router)
    dp.include_router(test_entry.router)
    dp.include_router(results.router)
    
    logger.info("🤖 Starting Telegram bot...")
    
    try:
        # Start polling
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        # Cleanup
        await api_client.close()
        await bot.session.close()
        logger.info("👋 Bot stopped")


if __name__ == "__main__":
    asyncio.run(main())
