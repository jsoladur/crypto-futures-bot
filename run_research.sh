#!/bin/bash

source .venv/bin/activate

# --- CONFIGURATION ---
# Static list of USDT futures base coins from MEXC
PAIRS=(
    "AAVE"
    "ALICE"
    "ANIME"
    "CLANKER"
    "DOGE"
    "DOT"
    "DYM"
    "FET"
    "GRT"
    "HMSTR"
    "MELANIA"
    "MERL"
    "MILK"
    "MORI"
    "NS"
    "ORDI"
    "PENGU"
    "PNUT"
    "PORTAL"
    "PYTH"
    "RENDER"
    "SOL"
    "TA"
    "TRB"
    "TRUMPOFFICIAL"
    "VELVET"
    "XRP"
    "ZEC"
)
echo "Processing ${#PAIRS[@]} USDT pairs."

# Define the directory where the result logs will be saved.
OUTPUT_DIR="out"
RESULTS_DIR="${OUTPUT_DIR}/results"
PROGRESS_DIR="${OUTPUT_DIR}/progress"

# --- SCRIPT LOGIC ---
echo "🚀 Starting backtesting research for all cryptos..."

# Create the output directories if they don't exist.
mkdir -p "$RESULTS_DIR"
mkdir -p "$PROGRESS_DIR"
echo "Results will be saved in '$RESULTS_DIR'"
echo "Progress logs will be saved in '$PROGRESS_DIR'"
echo "--------------------------------------------------"

# Loop through each pair in the array.
COUNTER=0
TOTAL=${#PAIRS[@]}
START_TIME=$(date +%s)

for crypto_currency in "${PAIRS[@]}"; do
    COUNTER=$((COUNTER + 1))

    # Calculate estimated time remaining
    if [ $COUNTER -gt 1 ]; then
        CURRENT_TIME=$(date +%s)
        ELAPSED_TOTAL=$((CURRENT_TIME - START_TIME))
        PROCESSED=$((COUNTER - 1))

        # Calculate average time per item (integer division)
        if [ $PROCESSED -gt 0 ]; then
            AVG_TIME=$((ELAPSED_TOTAL / PROCESSED))
        else
            AVG_TIME=0
        fi

        ITEMS_LEFT=$((TOTAL - PROCESSED))
        EST_SECONDS_LEFT=$((AVG_TIME * ITEMS_LEFT))

        # Format time
        H=$((EST_SECONDS_LEFT / 3600))
        M=$(( (EST_SECONDS_LEFT % 3600) / 60 ))
        S=$((EST_SECONDS_LEFT % 60))

        TIME_MSG=" | Est. remaining: ${H}h ${M}m ${S}s"
    else
        TIME_MSG=" | Est. remaining: Calculating..."
    fi

    echo "[${COUNTER}/${TOTAL}] Processing crypto: ${crypto_currency}${TIME_MSG}"

    # 2. Prepare the log file names.
    filename_symbol=$(echo "$crypto_currency" | sed 's/\//_/g')
    log_file="${RESULTS_DIR}/${filename_symbol}_research.log"
    progress_file="${PROGRESS_DIR}/${filename_symbol}_progress.log"

    echo "   -> Running research... Log file: ${log_file}, Error file: ${progress_file}"

    # 3. Execute the 'research' command, passing the exchange.
    #    Redirect stdout to log_file and stderr to progress_file.
    cli research --currency="$crypto_currency" "$@" > "$log_file" 2> "$progress_file"

    echo "✅ Finished research for ${crypto_currency}."
    echo "--------------------------------------------------"
done

echo "🎉 All backtesting research is complete."
