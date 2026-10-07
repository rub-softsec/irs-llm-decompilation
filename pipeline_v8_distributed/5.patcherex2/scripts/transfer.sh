#!/bin/bash

# Configuration file
MACHINES_JSON="machines.json"
REMOTE_USER="user"
REMOTE_PORT="12345"
REMOTE_WORKSPACE="workspace/5.patcherex2"

# Base files to send
BASE_FILES=("main.py" "main.sh" "d8" "init.sh" "selected.json")

# Function to display help message
show_help() {
    echo "Usage: $0 <machine_id> [OPTIONS]"
    echo ""
    echo "Arguments:"
    echo "  machine_id         ID of the machine (1-8) from machines.json"
    echo ""
    echo "Options:"
    echo "  --send-base        Send base files (main.py, main.sh, d8, init.sh, selected.json) to remote workspace"
    echo "  --send-input       Send content from local 'input_dist/<machine_id>/' to remote 'workspace/input'"
    echo "  --retrieve-output  Retrieve content from remote 'workspace/output' to local 'output/<machine_id>/'"
    echo "  --clean            Clean remote workspace (removes done.txt, error.txt, input/, logs/, main_output.log, output/)"
    echo ""
    echo "Examples:"
    echo "  $0 1 --send-base"
    echo "  $0 3 --send-input"
    echo "  $0 5 --retrieve-output"
    echo "  $0 2 --send-base --send-input"
    echo "  $0 4 --clean"
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
    
    scp -P "$REMOTE_PORT" "${BASE_FILES[@]}" "${REMOTE_USER}@${remote_ip}:${REMOTE_WORKSPACE}/"
    
    if [ $? -eq 0 ]; then
        echo "Base files sent successfully to machine $machine_id"
        return 0
    else
        echo "Error sending base files to machine $machine_id"
        return 1
    fi
}

# Function to send input directory
send_input() {
    local machine_id=$1
    local remote_ip=$2
    local input_dir="input_dist/$machine_id"
    
    echo "Sending input directory to machine $machine_id ($remote_ip)..."
    
    if [ ! -d "$input_dir" ]; then
        echo "Error: Local directory '$input_dir' not found"
        echo "Hint: Run distribute_input.py first to create input_dist directories"
        return 1
    fi
    
    # Compress input directory
    echo "Compressing input directory..."
    local zip_file="input_${machine_id}.zip"
    
    # Create temporary directory structure
    mkdir -p temp_input
    cp -r "$input_dir"/* temp_input/
    
    cd temp_input
    zip -r "../$zip_file" . > /dev/null
    cd ..
    rm -rf temp_input
    
    if [ $? -ne 0 ]; then
        echo "Error compressing input directory"
        return 1
    fi
    
    # Send compressed file
    scp -P "$REMOTE_PORT" "$zip_file" "${REMOTE_USER}@${remote_ip}:${REMOTE_WORKSPACE}/"
    
    if [ $? -ne 0 ]; then
        echo "Error sending $zip_file to machine $machine_id"
        rm -f "$zip_file"
        return 1
    fi
    
    # Decompress on remote and cleanup
    ssh -p "$REMOTE_PORT" "${REMOTE_USER}@${remote_ip}" "cd ${REMOTE_WORKSPACE} && mkdir -p input && cd input && unzip -o ../$zip_file > /dev/null && cd .. && rm $zip_file"
    
    if [ $? -eq 0 ]; then
        echo "Input directory sent and decompressed successfully to machine $machine_id"
        rm -f "$zip_file"
        return 0
    else
        echo "Error decompressing input directory on machine $machine_id"
        rm -f "$zip_file"
        return 1
    fi
}

# Function to retrieve output directory
retrieve_output() {
    local machine_id=$1
    local remote_ip=$2
    local output_dir="output/$machine_id"
    
    echo "Retrieving output directory from machine $machine_id ($remote_ip)..."
    
    # Compress output directory on remote
    echo "Compressing output directory on remote..."
    local zip_file="output_${machine_id}.zip"
    
    ####################
    # Create local output directory
    mkdir -p "$output_dir"
    
    # Copy error.txt as patcherex_error.txt if exist
    ssh -p "$REMOTE_PORT" "${REMOTE_USER}@${remote_ip}" "[ -f ${REMOTE_WORKSPACE}/error.txt ] && cat ${REMOTE_WORKSPACE}/error.txt" >> "$output_dir/pathcherex_error.txt" 2>/dev/null
    return 0
    ####################

    ssh -p "$REMOTE_PORT" "${REMOTE_USER}@${remote_ip}" "cd ${REMOTE_WORKSPACE} && zip -r $zip_file output/ > /dev/null"
    
    if [ $? -ne 0 ]; then
        echo "Error compressing output directory on machine $machine_id"
        return 1
    fi
    
    # Download compressed file
    scp -P "$REMOTE_PORT" "${REMOTE_USER}@${remote_ip}:${REMOTE_WORKSPACE}/$zip_file" .
    
    if [ $? -ne 0 ]; then
        echo "Error downloading $zip_file from machine $machine_id"
        ssh -p "$REMOTE_PORT" "${REMOTE_USER}@${remote_ip}" "rm -f ${REMOTE_WORKSPACE}/$zip_file"
        return 1
    fi
    
    # Create local output directory
    mkdir -p "$output_dir"
    
    # Copy error.txt as patcherex_error.txt if exist
    ssh -p "$REMOTE_PORT" "${REMOTE_USER}@${remote_ip}" "[ -f ${REMOTE_WORKSPACE}/error.txt ] && cat ${REMOTE_WORKSPACE}/error.txt" >> "$output_dir/pathcherex_error.txt" 2>/dev/null

    # Decompress locally
    echo "Decompressing output directory..."
    unzip -o "$zip_file" -d temp_output > /dev/null
    
    if [ $? -eq 0 ]; then
        # Move contents from temp_output/output/ to output/<machine_id>/
        if [ -d "temp_output/output" ]; then
            cp -r temp_output/output/* "$output_dir/"
        fi
        rm -rf temp_output
        
        echo "Output directory retrieved and saved to $output_dir"
        rm -f "$zip_file"
        ssh -p "$REMOTE_PORT" "${REMOTE_USER}@${remote_ip}" "rm -f ${REMOTE_WORKSPACE}/$zip_file"
        return 0
    else
        echo "Error decompressing output directory"
        rm -f "$zip_file"
        rm -rf temp_output
        ssh -p "$REMOTE_PORT" "${REMOTE_USER}@${remote_ip}" "rm -f ${REMOTE_WORKSPACE}/$zip_file"
        return 1
    fi
}

# Function to clean remote workspace
clean_remote() {
    local machine_id=$1
    local remote_ip=$2
    
    echo "Cleaning remote workspace on machine $machine_id ($remote_ip)..."
    
    # Files and directories to remove
    local items_to_remove=("done.txt" "error.txt" "input" "logs" "main_output.log" "output")
    
    # Build removal command
    local remove_cmd="cd ${REMOTE_WORKSPACE} && "
    local first=true
    
    for item in "${items_to_remove[@]}"; do
        if [ "$first" = true ]; then
            first=false
        else
            remove_cmd+=" && "
        fi
        remove_cmd+="(rm -rf $item 2>/dev/null || echo 'Could not remove: $item')"
    done
    
    # Execute removal command on remote
    local result=$(ssh -p "$REMOTE_PORT" "${REMOTE_USER}@${remote_ip}" "$remove_cmd" 2>&1)
    
    # Check if there were any errors
    if echo "$result" | grep -q "Could not remove:"; then
        echo "Warning: Some items could not be removed:"
        echo "$result" | grep "Could not remove:"
    fi
    
    echo "Cleaning completed on machine $machine_id"
    return 0
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
        --send-input)
            send_input "$MACHINE_ID" "$REMOTE_IP"
            shift
            ;;
        --retrieve-output)
            retrieve_output "$MACHINE_ID" "$REMOTE_IP"
            shift
            ;;
        --clean)
            clean_remote "$MACHINE_ID" "$REMOTE_IP"
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