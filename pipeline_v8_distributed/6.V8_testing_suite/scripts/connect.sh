#!/bin/bash

# Configuration file
MACHINES_JSON="machines.json"
REMOTE_USER="user"
REMOTE_PORT="12345"

# Function to display help
show_help() {
    echo "Usage: $0 <machine_id>"
    echo ""
    echo "Arguments:"
    echo "  machine_id    ID of the machine (1-8) from machines.json"
    echo ""
    echo "Examples:"
    echo "  $0 1    # Connect to machine 1"
    echo "  $0 5    # Connect to machine 5"
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

# Main
if [ $# -eq 0 ]; then
    show_help
    exit 1
fi

# Check for help flag
if [ "$1" == "-h" ] || [ "$1" == "--help" ]; then
    show_help
    exit 0
fi

MACHINE_ID=$1

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

echo "Connecting to machine $MACHINE_ID ($REMOTE_IP)..."
echo ""

# Connect via SSH
ssh -p "$REMOTE_PORT" "${REMOTE_USER}@${REMOTE_IP}"