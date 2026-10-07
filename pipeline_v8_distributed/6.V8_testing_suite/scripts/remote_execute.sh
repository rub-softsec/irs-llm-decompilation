#!/bin/bash

# Configuration file
MACHINES_JSON="machines.json"
REMOTE_USER="user"
REMOTE_PORT="12345"
REMOTE_DIR="workspace/6.V8_testing_suite"
DONE_FILE="done.txt"

# Function to display help
show_help() {
    echo "Usage: $0 <machine_id> [--run|--check]"
    echo ""
    echo "Arguments:"
    echo "  machine_id    ID of the machine (1-8) from machines.json"
    echo ""
    echo "Options:"
    echo "  --run     Execute main.sh on remote server and disconnect"
    echo "  --check   Check if main.sh has finished execution"
    echo ""
    echo "Examples:"
    echo "  $0 1 --run      # Run V8 testing on machine 1"
    echo "  $0 3 --check    # Check status on machine 3"
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

# Function to execute the script remotely
run_remote() {
    local machine_id=$1
    local remote_ip=$2
    local ssh_host="${REMOTE_USER}@${remote_ip}"
    
    echo "=============================================================="
    echo "Starting remote execution on machine $machine_id"
    echo "=============================================================="
    echo ""
    
    # Remove done.txt if it exists (for a clean new execution)
    echo "Cleaning up previous execution..."
    ssh -p "$REMOTE_PORT" "$ssh_host" "cd $REMOTE_DIR && rm -f $DONE_FILE"
    
    echo "Starting main.sh in background..."
    
    # Execute the script in background using nohup
    ssh -p "$REMOTE_PORT" "$ssh_host" "cd $REMOTE_DIR && nohup bash main.sh > main_output.log 2>&1 &"
    
    if [ $? -eq 0 ]; then
        echo ""
        echo ""
        echo "[OK] Script started successfully on machine $machine_id!"
        echo "The process is now running in the background on the remote server"
        echo "Use '$0 $machine_id --check' to verify if it has finished"
        echo ""
    else
        echo ""
        echo ""
        echo "[ERROR] Failed to start script on machine $machine_id"
        echo ""
        exit 1
    fi
}

# Function to check if execution has finished
check_remote() {
    local machine_id=$1
    local remote_ip=$2
    local ssh_host="${REMOTE_USER}@${remote_ip}"
    
    echo "=============================================================="
    echo "Checking execution status on machine $machine_id"
    echo "=============================================================="
    echo ""
    
    # Check if done.txt exists
    ssh -p "$REMOTE_PORT" "$ssh_host" "[ -f $REMOTE_DIR/$DONE_FILE ]"
    
    if [ $? -eq 0 ]; then
        echo "[FINISHED] Execution has FINISHED on machine $machine_id"
        echo "The file $DONE_FILE exists on the remote server"
        echo ""
        return 0
    else
        echo "[RUNNING] Execution is still RUNNING on machine $machine_id (or not started yet)"
        echo "The file $DONE_FILE does not exist yet"
        echo ""
        return 1
    fi
}

# Main
if [ $# -eq 0 ]; then
    show_help
    exit 1
fi

# First argument must be machine_id
MACHINE_ID=$1
shift

# Check for help flag
if [ "$MACHINE_ID" == "-h" ] || [ "$MACHINE_ID" == "--help" ]; then
    show_help
    exit 0
fi

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

if [ $# -eq 0 ]; then
    show_help
    exit 1
fi

case "$1" in
    --run)
        run_remote "$MACHINE_ID" "$REMOTE_IP"
        ;;
    --check)
        check_remote "$MACHINE_ID" "$REMOTE_IP"
        ;;
    --help|-h)
        show_help
        ;;
    *)
        echo "Error: Unknown option '$1'"
        echo ""
        show_help
        exit 1
        ;;
esac

exit 0