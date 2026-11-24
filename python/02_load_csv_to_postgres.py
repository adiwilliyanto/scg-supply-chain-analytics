
from pathlib import Path
import csv
import os

import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv


# ==========================================
# 1. PROJECT CONFIGURATION
# ==========================================

PROJECT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_DIR / "data" / "raw"

# Load environment variables from project root
load_dotenv(dotenv_path=PROJECT_DIR / ".env")

FOLDERS = [
    "master_data",
    "transaction_data",
    "planning_data"
]


# ==========================================
# 2. DATABASE CONNECTION CONFIGURATION
# ==========================================

DB_CONFIG = {
    "host": os.getenv("PGHOST", "localhost"),
    "database": os.getenv("PGDATABASE", "scg_supply_chain"),
    "user": os.getenv("PGUSER", "postgres"),
    "password": os.getenv("PGPASSWORD"),
    "port": int(os.getenv("PGPORT", "5432"))
}

if not DB_CONFIG["password"]:
    raise ValueError(
        "Database password not found. "
        "Please configure PGPASSWORD in your .env file."
    )


# ==========================================
# 3. CONNECT AND IMPORT CSV FILES
# ==========================================

conn = None

try:

    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False

    with conn.cursor() as cur:

        # Create raw schema
        cur.execute("""
            CREATE SCHEMA IF NOT EXISTS raw;
        """)

        # ==================================
        # 4. DISCOVER CSV FILES
        # ==================================

        for folder_name in FOLDERS:

            folder_path = RAW_DIR / folder_name

            if not folder_path.exists():
                raise FileNotFoundError(
                    f"Folder not found: {folder_path}"
                )

            csv_files = sorted(folder_path.glob("*.csv"))

            for file_path in csv_files:

                table_name = file_path.stem

                print(f"\nImporting: {table_name}")

                # Read CSV header
                with open(
                    file_path,
                    "r",
                    encoding="utf-8-sig",
                    newline=""
                ) as file:

                    reader = csv.reader(file)
                    headers = next(reader)

                # ==================================
                # 5. CREATE RAW TABLE
                # ==================================

                columns = [
                    sql.SQL("{} TEXT").format(
                        sql.Identifier(column)
                    )
                    for column in headers
                ]

                create_table_query = sql.SQL("""
                    CREATE TABLE raw.{} (
                        {}
                    )
                """).format(
                    sql.Identifier(table_name),
                    sql.SQL(", ").join(columns)
                )

                # Rebuild table during each import
                cur.execute(
                    sql.SQL("DROP TABLE IF EXISTS raw.{}").format(
                        sql.Identifier(table_name)
                    )
                )

                cur.execute(create_table_query)

                # ==================================
                # 6. LOAD CSV USING COPY
                # ==================================

                copy_query = sql.SQL("""
                    COPY raw.{} ({})
                    FROM STDIN
                    WITH (
                        FORMAT CSV,
                        HEADER TRUE,
                        NULL ''
                    )
                """).format(
                    sql.Identifier(table_name),
                    sql.SQL(", ").join(
                        sql.Identifier(column)
                        for column in headers
                    )
                )

                with open(
                    file_path,
                    "r",
                    encoding="utf-8-sig",
                    newline=""
                ) as file:

                    cur.copy_expert(
                        copy_query.as_string(conn),
                        file
                    )

                # ==================================
                # 7. VERIFY IMPORTED ROWS
                # ==================================

                cur.execute(
                    sql.SQL("SELECT COUNT(*) FROM raw.{}").format(
                        sql.Identifier(table_name)
                    )
                )

                imported_rows = cur.fetchone()[0]

                print(
                    f"Imported successfully: "
                    f"{imported_rows:,} rows"
                )

    # ==========================================
    # 8. COMMIT TRANSACTION
    # ==========================================

    conn.commit()

    print("\n" + "=" * 50)
    print("ALL CSV FILES IMPORTED SUCCESSFULLY")
    print("=" * 50)

except Exception as error:

    if conn is not None:
        conn.rollback()

    print("\nIMPORT FAILED")
    print("Transaction rolled back.")
    print(error)

    raise

finally:

    if conn is not None:
        conn.close()
        print("\nDatabase connection closed.")
