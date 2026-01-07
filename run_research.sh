#!/bin/bash

source .venv/bin/activate

# --- CONFIGURATION ---
# Define the "" pairs you want to test.
PAIRS=(
    "DOGE"
    "PENGU"
    "XRP"
    "ZEC"
    "SOL"
    "BNB"
)

# Define the directory where the result logs will be saved.
OUTPUT_DIR="out"

# --- SCRIPT LOGIC ---
echo "🚀 Starting backtesting research for all cryptos..."

# Create the output directory if it doesn't exist.
mkdir -p "$OUTPUT_DIR"
echo "Output will be saved in the '$OUTPUT_DIR' directory."
echo "--------------------------------------------------"

# Loop through each pair in the array.
for crypto_currency in "${PAIRS[@]}"; do
    echo "Processing crypto: ${crypto_currency}"

    # 2. Prepare the log file names.
    filename_symbol=$(echo "$crypto_currency" | sed 's/\//_/g')
    log_file="${OUTPUT_DIR}/${filename_symbol}_research.log"
    progress_file="${OUTPUT_DIR}/${filename_symbol}_progress.log"

    echo "   -> Running research... Log file: ${log_file}, Error file: ${progress_file}"

    # 3. Execute the 'research' command, passing the exchange.
    #    Redirect stdout to log_file and stderr to progress_file.
    cli research --currency="$crypto_currency" "$@" > "$log_file" 2> "$progress_file"

    echo "✅ Finished research for ${crypto_currency}."
    echo "--------------------------------------------------"
done

echo "🎉 All backtesting research is complete."
