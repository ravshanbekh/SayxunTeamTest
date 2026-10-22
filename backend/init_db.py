# Database initialization script
import asyncio
from app.database import init_db

# Import all models to register them with Base
from app.models import user, admin, test, session, result, offline, payment

async def main():
    print("Creating database tables...")
    await init_db()
    print("Database initialized successfully!")

if __name__ == "__main__":
    asyncio.run(main())
