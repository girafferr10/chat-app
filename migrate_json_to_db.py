import asyncio
import asyncpg
import json
import os

DATABASE_URL = "postgresql://chat_app_db_txr2_user:Eo9iukLinUpgqQ73JGGvFwQFsS5MLQRp@dpg-d9b60557vvec73d86i5g-a.ohio-postgres.render.com/chat_app_db_txr2"

DATA_FOLDER = "other stuff (important)"


async def main():
    conn = await asyncpg.connect(DATABASE_URL)

    print("Connected!")

    with open(os.path.join(DATA_FOLDER, "users.json"), "r", encoding="utf-8") as f:
        users = json.load(f)

    print(f"Importing {len(users)} users...")

    for user in users:

        await conn.execute(
            """
            INSERT INTO users
            (
                username,
                password_hash,
                display_name,
                bio,
                pfp_data,
                email,
                email_verified,
                twofa_enabled,
                role
            )
            VALUES
            ($1,$2,$3,$4,$5,$6,$7,$8,$9)
            ON CONFLICT (username) DO NOTHING
            """,
            user.get("username", ""),
            user.get("password_hash", ""),
            user.get("display_name", ""),
            user.get("bio", ""),
            user.get("pfp_data", ""),
            user.get("email", ""),
            user.get("email_verified", False),
            user.get("twofa_enabled", False),
            user.get("role", "user"),
        )

        print("Imported:", user.get("username"))

    print("\nAll users imported!")

    await conn.close()


asyncio.run(main())