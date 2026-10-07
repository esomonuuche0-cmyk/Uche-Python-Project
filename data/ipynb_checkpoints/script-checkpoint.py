# Import library
import pandas as pd
from pathlib import Path
from datetime import datetime

# project paths
BASE_DIR = Path.cwd()

RAW_FOLDER = BASE_DIR / "data" / "raw"
CLEAN_FOLDER = BASE_DIR / "data" / "cleaned"
COMBINED_FOLDER = BASE_DIR / "data" / "combined"
LOG_FOLDER = BASE_DIR / "logs"

PROCESSED_FILE = BASE_DIR / "processed_files.txt"
MASTER_FILE = COMBINED_FOLDER / "master_data.csv"

#CREATE FOLDERS IF THEY DON'T EXIST 
RAW_FOLDER.mkdir(parents=True, exist_ok=True)
CLEAN_FOLDER.mkdir(parents=True, exist_ok=True)
COMBINED_FOLDER.mkdir(parents=True, exist_ok=True)
LOG_FOLDER.mkdir(parents=True, exist_ok=True)

# Date and logging
today = datetime.now().strftime('%Y-%m-%d')

log_file = LOG_FOLDER/ f'pipeline_{today}.log'

def log(message):
    time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    message = f"[{time}] {message}"

    print(message)

    with open(log_file, "a", encoding="utf-8") as file:
        file.write(message + "\n")

# LOAD PROCESSED FILES
if PROCESSED_FILE.exists():

    with open(PROCESSED_FILE, "r", encoding="utf-8") as file:
        processed_files = set(file.read().splitlines())

else:

    processed_files = set()

# 4. FIND NEW CSV FILES

all_files = list(RAW_FOLDER.glob("*.csv"))

new_files = [
    file for file in all_files
    if file.name not in processed_files
]


if not new_files:

    log("No new files found.")
    exit()


log(f"Found {len(new_files)} new file(s).")


# 5. PROCESS EACH FILE

cleaned_data = []


for file in new_files:

    try:

        log(f"Processing {file.name}")

        # Read CSV
        df = pd.read_csv(file)


        # ----------------------------------
        # Clean column names
        # ----------------------------------

        df.columns = (
            df.columns
            .str.strip()
            .str.lower()
            .str.replace(" ", "_")
        )


        # ----------------------------------
        # Remove duplicate rows
        # ----------------------------------

        before = len(df)

        df = df.drop_duplicates()

        after = len(df)

        log(
            f"{file.name}: "
            f"removed {before - after} duplicates"
        )


        # ----------------------------------
        # Remove completely empty rows
        # ----------------------------------

        df = df.dropna(how="all")

        # ----------------------------------
        # Convert all text date value to lowercase
        # ----------------------------------
        
        str_dtype = df.select_dtypes(include=['object'])
        for column in str_dtype.columns:
            if column == "sku_code":
                df[column] = df[column].str.upper().str.strip()
            else: 
                df[column] = df[column].str.lower().str.strip()


        # ----------------------------------
        # Fix the issue with the Sku-code
        # ----------------------------------
        def fix_sku_code(data):
            string = data[0:3] +"-" + data[-3: ]
            return string
            
        df['sku_code'] = df['sku_code'].apply(fix_sku_code)
        # ----------------------------------
        # Convert date column
        # ----------------------------------

        if "date" in df.columns:

            df["date"] = pd.to_datetime(
                df["date"],
                errors="coerce",
                format='mixed'
            )
        


        # ----------------------------------
        # Add source file
        # ----------------------------------

        df["source_file"] = file.name


        # ----------------------------------
        # Add processing date
        # ----------------------------------

        df["processed_date"] = today


        cleaned_data.append(df)


    except Exception as e:

        log(
            f"ERROR processing {file.name}: {e}"
        )

# 6. STOP IF NOTHING WAS PROCESSED

if not cleaned_data:

    log("No files were successfully processed.")
    exit()

# 7. COMBINE NEW DATA
# ==========================================

new_data = pd.concat(
    cleaned_data,
    ignore_index=True
)

log(
    f"New records processed: {len(new_data)}"
)


# 8. LOAD EXISTING MASTER DATA


if MASTER_FILE.exists():

    master_data = pd.read_csv(
        MASTER_FILE
    )

    log(
        f"Existing master records: "
        f"{len(master_data)}"
    )

else:

    master_data = pd.DataFrame()

    log("Master dataset does not exist. Creating it.")

# 9. COMBINE OLD + NEW DATA


if not master_data.empty:

    master_data = pd.concat(
        [master_data, new_data],
        ignore_index=True
    )

else:

    master_data = new_data


# 10. REMOVE DUPLICATES

before = len(master_data)

master_data = master_data.drop_duplicates()

after = len(master_data)

log(
    f"Master duplicates removed: "
    f"{before - after}"
)

)

# 11. SAVE DAILY CLEANED FILE


daily_file = (
    CLEAN_FOLDER /
    f"cleaned_data_{today}.csv"
)

new_data.to_csv(
    daily_file,
    index=False
)

log(
    f"Daily cleaned file saved: "
    f"{daily_file.name}"
)

# 12. SAVE MASTER DATASET


master_data.to_csv(
    MASTER_FILE,
    index=False
)

log(
    f"Master dataset saved."
)

# 13. MARK FILES AS PROCESSED

with open(
    PROCESSED_FILE,
    "a",
    encoding="utf-8"
) as file:

    for processed in new_files:

        file.write(
            processed.name + "\n"
        )

# 14. FINAL SUMMARY


log(
    f"Pipeline completed successfully."
)

log(
    f"Total master records: "
    f"{len(master_data)}"
)