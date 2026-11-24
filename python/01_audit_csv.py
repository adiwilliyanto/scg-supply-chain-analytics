
from pathlib import Path
import csv

# ==========================================
# 1. PROJECT CONFIGURATION
# ==========================================

PROJECT_DIR = Path(r"D:\SCG_Supply_Chain_Project")
RAW_DIR = PROJECT_DIR / "data" / "raw"
OUTPUT_FILE = PROJECT_DIR / "documentation" / "csv_inventory.csv"

FOLDERS = [
    "master_data",
    "transaction_data",
    "planning_data"
]

EXPECTED_FILES = 17

# ==========================================
# 2. CSV FILE AUDIT
# ==========================================

inventory = []
errors = []

for folder_name in FOLDERS:

    folder_path = RAW_DIR / folder_name

    print(f"\nAuditing: {folder_name}")

    if not folder_path.exists():
        errors.append(f"Folder not found: {folder_path}")
        continue

    csv_files = sorted(folder_path.glob("*.csv"))

    for file_path in csv_files:

        try:
            with open(
                file_path,
                mode="r",
                encoding="utf-8-sig",
                newline=""
            ) as file:

                reader = csv.reader(file)

                header = next(reader, None)

                if header is None:
                    errors.append(f"Empty CSV: {file_path.name}")
                    continue

                row_count = sum(1 for _ in reader)

            inventory.append({
                "category": folder_name,
                "file_name": file_path.name,
                "row_count": row_count,
                "column_count": len(header),
                "columns": " | ".join(header),
                "file_size_kb": round(
                    file_path.stat().st_size / 1024, 2
                )
            })

            print(
                f"  {file_path.name} | "
                f"{row_count:,} rows | "
                f"{len(header)} columns"
            )

        except Exception as error:
            errors.append(
                f"{file_path.name}: {error}"
            )

# ==========================================
# 3. EXPORT CSV INVENTORY
# ==========================================

OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True
)

fieldnames = [
    "category",
    "file_name",
    "row_count",
    "column_count",
    "columns",
    "file_size_kb"
]

with open(
    OUTPUT_FILE,
    mode="w",
    encoding="utf-8-sig",
    newline=""
) as file:

    writer = csv.DictWriter(
        file,
        fieldnames=fieldnames
    )

    writer.writeheader()
    writer.writerows(inventory)

# ==========================================
# 4. AUDIT SUMMARY
# ==========================================

actual_files = len(inventory)

print("\n" + "=" * 50)
print("CSV AUDIT SUMMARY")
print("=" * 50)

print(f"Expected files : {EXPECTED_FILES}")
print(f"Found files    : {actual_files}")
print(f"Missing files  : {EXPECTED_FILES - actual_files}")

if actual_files == EXPECTED_FILES and not errors:
    print("STATUS: FILE COUNT CHECK PASSED")
else:
    print("STATUS: AUDIT NEEDS REVIEW")

if errors:
    print("\nAUDIT ERRORS:")
    for error in errors:
        print(f"- {error}")

print(f"\nInventory saved to:\n{OUTPUT_FILE}")
