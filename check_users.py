import asyncio
import asyncpg

DATABASE_URL = "postgresql://chat_app_db_txr2_user:Eo9iukLinUpgqQ73JGGvFwQFsS5MLQRp@dpg-d9b60557vvec73d86i5g-a.ohio-postgres.render.com/chat_app_db_txr2"


async def main():
    conn = await asyncpg.connect(DATABASE_URL)

    print("Connected!")

    # Create users table if it does not exist
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(30) UNIQUE NOT NULL,
            password_hash VARCHAR(256) NOT NULL DEFAULT '',
            display_name VARCHAR(30) NOT NULL DEFAULT '',
            bio TEXT DEFAULT '',
            pfp_data TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Add missing columns from server.py migrations
    migrations = [
        ("email", "VARCHAR(120) DEFAULT ''"),
        ("email_verified", "BOOLEAN NOT NULL DEFAULT FALSE"),
        ("twofa_enabled", "BOOLEAN NOT NULL DEFAULT FALSE"),
        ("role", "VARCHAR(10) NOT NULL DEFAULT 'user'")
    ]

    for column, definition in migrations:
        try:
            await conn.execute(
                f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {column} {definition}"
            )
            print(f"Checked column: {column}")
        except Exception as e:
            print(f"Migration error for {column}: {e}")

    print("Users table ready.")

    # Show users + password hashes
    rows = await conn.fetch("""
        SELECT 
            id,
            username,
            password_hash,
            display_name,
            email,
            role,
            twofa_enabled,
            created_at
        FROM users
        ORDER BY id
    """)

    print("\nUsers:")
    if not rows:
        print("No users found.")
    else:
        for row in rows:
            print(dict(row))

    # Show all tables in database
    tables = await conn.fetch("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema='public'
        ORDER BY table_name
    """)

    print("\nTables in database:")
    for t in tables:
        print("-", t["table_name"])

    await conn.close()
    print("\nDone!")


asyncio.run(main())