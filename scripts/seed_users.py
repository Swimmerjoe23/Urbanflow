"""Seed additional demo user accounts into the real instance database.

Run once from the project root:

    python scripts/seed_users.py

Safe to re-run: usernames that already exist are skipped. All seeded accounts
share the password below (hashed with PBKDF2, same as production sign-ups) —
change it before showing seeded credentials to anyone outside the demo.
"""
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "instance", "urbanflow.db")
SEED_PASSWORD = "Seed@2026"

NEW_ADMINS = [
    "jkamau",
    "awanjiru",
    "smutiso",
]

NEW_PLANNERS = [
    "bomondi",
    "cnjeri",
    "dkiptoo",
    "fwambui",
    "gotieno",
    "hchebet",
    "imwangi",
    "jakinyi",
    "kmusyoka",
    "lnyaga",
    "mwafula",
    "nkamande",
    "ondiba",
    "pkilonzo",
    "qwaweru",
    "rmutua",
    "snduta",
    "tmugo",
    "uwairimu",
    "vkiplagat",
    "wkoech",
    "xmuriuki",
    "ynafula",
    "zonyango",
]


def main():
    if not os.path.exists(DB_PATH):
        print(f"No database found at {DB_PATH}. Run the app once first so it can be initialised.")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    password_hash = generate_password_hash(SEED_PASSWORD, method="pbkdf2:sha256")

    to_insert = [(u, "admin") for u in NEW_ADMINS] + [(u, "planner") for u in NEW_PLANNERS]

    inserted, skipped = [], []
    for username, role in to_insert:
        existing = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if existing:
            skipped.append(username)
            continue
        conn.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            (username, password_hash, role),
        )
        inserted.append((username, role))

    conn.commit()
    total = conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]
    conn.close()

    print(f"Inserted {len(inserted)} new users (shared password: {SEED_PASSWORD}):")
    for username, role in inserted:
        print(f"  {username:<12} [{role}]")
    if skipped:
        print(f"Skipped {len(skipped)} already-existing usernames: {', '.join(skipped)}")
    print(f"Total users in {DB_PATH} now: {total}")


if __name__ == "__main__":
    main()
