#!/bin/bash

# Configuration file
MACHINES_JSON="machines.json"
REMOTE_USER="user"
REMOTE_PORT="12345"
REMOTE_WORKSPACE="workspace/6.V8_testing_suite"
REMOTE_WORKSPACE_PART1="workspace/5.patcherex2"

# Base files to send
BASE_FILES=("main.sh") # "v8_dir.zip")

# Function to display help message
show_help() {
    echo "Usage: $0 <machine_id> [OPTIONS]"
    echo ""
    echo "Arguments:"
    echo "  machine_id              ID of the machine (1-8) from machines.json"
    echo ""
    echo "Options:"
    echo "  --send-base             Send base files (v8_dir.zip, main.sh) to remote workspace"
    echo "  --copy-from-5-to-6      Copy output from part 1 to input of part 2 (remote operation)"
    echo "  --retrieve-output       Retrieve main_output.log from remote workspace to local 'output/<machine_id>/'"
    echo "  --clean                 Clean specific files and directories from remote workspace"
    echo ""
    echo "Examples:"
    echo "  $0 1 --send-base"
    echo "  $0 3 --copy-from-5-to-6"
    echo "  $0 5 --retrieve-output"
    echo "  $0 7 --clean"
    echo "  $0 2 --send-base --copy-from-5-to-6"
    echo ""
}

# Function to get IP from machines.json
get_machine_ip() {
    local machine_id=$1
    
    if [ ! -f "$MACHINES_JSON" ]; then
        echo "Error: $MACHINES_JSON not found"
        return 1
    fi
    
    # Extract IP using python
    local ip=$(python3 -c "import json; machines = json.load(open('$MACHINES_JSON')); print([m['ip'] for m in machines if m['id'] == $machine_id][0] if any(m['id'] == $machine_id for m in machines) else '')")
    
    if [ -z "$ip" ]; then
        echo "Error: Machine ID $machine_id not found in $MACHINES_JSON"
        return 1
    fi
    
    echo "$ip"
}

# Function to send base files
send_base() {
    local machine_id=$1
    local remote_ip=$2
    
    echo "Sending base files to machine $machine_id ($remote_ip)..."
    
    for file in "${BASE_FILES[@]}"; do
        if [ ! -f "$file" ]; then
            echo "Error: File '$file' not found"
            return 1
        fi
    done
    
    # Create remote workspace if it doesn't exist
    ssh -p "$REMOTE_PORT" "${REMOTE_USER}@${remote_ip}" "mkdir -p ${REMOTE_WORKSPACE}"
    
    scp -P "$REMOTE_PORT" "${BASE_FILES[@]}" "${REMOTE_USER}@${remote_ip}:${REMOTE_WORKSPACE}/"
    
    if [ $? -eq 0 ]; then
        echo "Base files sent successfully to machine $machine_id"
        return 0
    else
        echo "Error sending base files to machine $machine_id"
        return 1
    fi
}

# Function to copy output from part 1 to input of part 2 (remote operation)
copy_from_5_to_6() {
    local machine_id=$1
    local remote_ip=$2
    
    echo "Copying output from part 1 to input of part 2 on machine $machine_id ($remote_ip)..."
    
    # Execute remote copy command
    ssh -p "$REMOTE_PORT" "${REMOTE_USER}@${remote_ip}" "mkdir -p ${REMOTE_WORKSPACE}/input && cp -r ${REMOTE_WORKSPACE_PART1}/output/* ${REMOTE_WORKSPACE}/input/"
    
    if [ $? -eq 0 ]; then
        echo "Successfully copied output to input on machine $machine_id"
        return 0
    else
        echo "Error copying output to input on machine $machine_id"
        return 1
    fi
}

# Function to retrieve main_output.log file
retrieve_output() {
    local machine_id=$1
    local remote_ip=$2
    local output_dir="output/$machine_id"
    
    echo "Retrieving main_output.log from machine $machine_id ($remote_ip)..."
    
    # Create local output directory
    mkdir -p "$output_dir"
    
    # Download main_output.log directly
    scp -P "$REMOTE_PORT" "${REMOTE_USER}@${remote_ip}:${REMOTE_WORKSPACE}/main_output.log" "$output_dir/"
    
    if [ $? -eq 0 ]; then
        echo "main_output.log retrieved and saved to $output_dir/main_output.log"
        return 0
    else
        echo "Error downloading main_output.log from machine $machine_id"
        return 1
    fi
}

# Function to clean specific files and directories from remote workspace
clean_workspace() {
    local machine_id=$1
    local remote_ip=$2
    
    echo "Cleaning workspace on machine $machine_id ($remote_ip)..."
    
    # List of files and directories to remove
    local items_to_remove=(
        "done.txt"
        "error.txt"
        "input"
        "logs"
        "main_output.log"
        "output"
    )
    
    # Build the rm command for all items
    local rm_command="cd ${REMOTE_WORKSPACE} && rm -rf"
    for item in "${items_to_remove[@]}"; do
        rm_command="$rm_command $item"
    done
    
    # Execute remote clean command
    ssh -p "$REMOTE_PORT" "${REMOTE_USER}@${remote_ip}" "$rm_command"
    
    if [ $? -eq 0 ]; then
        echo "Successfully cleaned workspace on machine $machine_id"
        return 0
    else
        echo "Error cleaning workspace on machine $machine_id"
        return 1
    fi
}

# Main script logic
if [ $# -eq 0 ]; then
    show_help
    exit 0
fi

# First argument must be machine_id
MACHINE_ID=$1
shift

# Validate machine_id is a number
if ! [[ "$MACHINE_ID" =~ ^[0-9]+$ ]]; then
    echo "Error: Machine ID must be a number"
    show_help
    exit 1
fi

# Get machine IP
REMOTE_IP=$(get_machine_ip "$MACHINE_ID")
if [ $? -ne 0 ]; then
    exit 1
fi

echo "Using machine $MACHINE_ID with IP: $REMOTE_IP"
echo ""

# Parse command line arguments
if [ $# -eq 0 ]; then
    show_help
    exit 0
fi

while [[ $# -gt 0 ]]; do
    case $1 in
        --send-base)
            send_base "$MACHINE_ID" "$REMOTE_IP"
            shift
            ;;
        --copy-from-5-to-6)
            copy_from_5_to_6 "$MACHINE_ID" "$REMOTE_IP"
            shift
            ;;
        --retrieve-output)
            retrieve_output "$MACHINE_ID" "$REMOTE_IP"
            shift
            ;;
        --clean)
            clean_workspace "$MACHINE_ID" "$REMOTE_IP"
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "Error: Unknown option '$1'"
            show_help
            exit 1
            ;;
    esac
done