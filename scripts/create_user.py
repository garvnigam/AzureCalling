"""Create a dashboard user. Usage:
    venv/bin/python scripts/create_user.py email@example.com "Full Name" password
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

from services.auth_service import hash_password
from services.database import Database

load_dotenv()


async def main():
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)
    email, name, password = sys.argv[1], sys.argv[2], sys.argv[3]
    if len(password) < 6:
        print("ERROR: password must be at least 6 characters")
        sys.exit(1)
    db = Database()
    existing = await db.get_user_by_email(email)
    if existing:
        print(f"ERROR: user {email} already exists")
        sys.exit(1)
    user_id = await db.create_user(email, name, hash_password(password))
    print(f"Created user: {email} ({name}) id={user_id}")


if __name__ == "__main__":
    asyncio.run(main())