#!/bin/bash

#See https://alex-ber.medium.com/converting-prof-files-to-callgrind-f6ae56fae0d3 for more details.
# Define default values
DEFAULT_INPUT="my_program.prof"  # Default input profile file
DEFAULT_OUTPUT="my_program.callgrind"  # Default output callgrind file
DEFAULT_PROJECT_DIR="/mnt/c/dev/work/scrapyFW/public"  # Default project directory
DEFAULT_APP_DIR="AlexBerUtils"  # Default application directory

# Function to display help
function display_help() {
    echo "Usage: $0 [INPUT_FILE] [OUTPUT_FILE] [PROJECT_DIR] [APP_DIR]"
    echo
    echo "Arguments:"
    echo "  INPUT_FILE    The input .prof file (default: $DEFAULT_INPUT)"
    echo "  OUTPUT_FILE   The output .callgrind file (default: $DEFAULT_OUTPUT)"
    echo "  PROJECT_DIR   The project directory (default: $DEFAULT_PROJECT_DIR)"
    echo "  APP_DIR       The application directory (default: $DEFAULT_APP_DIR)"
    echo
    echo "Example:"
    echo "  $0 my_program.prof my_program.callgrind /path/to/your/workspace AlexBerUtils"
    echo
    echo "If no arguments are provided, the script will use the default values."
}

# Check for help option
if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    display_help
    exit 0
fi

# Use provided arguments or default values
INPUT_FILE=${1:-$DEFAULT_INPUT}
OUTPUT_FILE=${2:-$DEFAULT_OUTPUT}
PROJECT_DIR=${3:-$DEFAULT_PROJECT_DIR}
APP_DIR=${4:-$DEFAULT_APP_DIR}

# Navigate to the working directory
cd "$PROJECT_DIR/$APP_DIR"

# Pull the Docker image
docker pull alexberkovich/alex_ber_utils:latest

# Run the Docker command to convert the .prof file to callgrind format
docker run --rm \
    -v "$PROJECT_DIR:/opt/project" \
    alexberkovich/alex_ber_utils:latest \
    python /opt/project/$APP_DIR/alexber/utils/prof_to_callgrind.py /opt/project/$APP_DIR/$INPUT_FILE /opt/project/$APP_DIR/$OUTPUT_FILE