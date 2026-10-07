#!/bin/bash

# Configuration
MACHINES_JSON="machines.json"

show_help() {
    echo "Distributed Processing Master Script"
    echo "======================================"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  distribute         Distribute input files across all machines"
    echo "  send-base-all      Send base files to all machines"
    echo "  send-input-all     Send input files to all machines"
    echo "  send-all           Send base + input files to all machines"
    echo "  run-all            Start processing on all machines"
    echo "  check-all          Check processing status on all machines"
    echo "  retrieve-all       Retrieve output from all machines"
    echo "  clean-all          Clean workspace on all machines"
    echo "  full-run           Execute complete workflow (distribute + send + run)"
    echo ""
    echo "Individual machine operations:"
    echo "  send-base <id>     Send base files to specific machine"
    echo "  send-input <id>    Send input files to specific machine"
    echo "  send <id>          Send base + input to specific machine"
    echo "  run <id>           Run processing on specific machine"
    echo "  check <id>         Check status on specific machine"
    echo "  retrieve <id>      Retrieve output from specific machine"
    echo "  clean <id>         Clean workspace on specific machine"
    echo ""
    echo "Examples:"
    echo "  $0 distribute           # Distribute input files"
    echo "  $0 send-base-all       # Send base files to all machines"
    echo "  $0 send-input-all      # Send input files to all machines"
    echo "  $0 send-all            # Send everything to all machines"
    echo "  $0 run-all             # Start processing on all"
    echo "  $0 check-all           # Check all machines"
    echo "  $0 retrieve-all        # Get results from all"
    echo "  $0 clean-all           # Clean all machines"
    echo "  $0 full-run            # Complete automated workflow"
    echo ""
    echo "  $0 send-base 3         # Send base files only to machine 3"
    echo "  $0 send-input 3        # Send input files only to machine 3"
    echo "  $0 send 3              # Send both to machine 3"
    echo "  $0 run 5               # Run only on machine 5"
    echo "  $0 clean 2             # Clean workspace on machine 2"
    echo ""
}

# Get number of machines
get_num_machines() {
    if [ ! -f "$MACHINES_JSON" ]; then
        echo "0"
        return
    fi
    python3 -c "import json; print(len(json.load(open('$MACHINES_JSON'))))"
}

# Distribute input files
distribute() {
    echo "=============================================================="
    echo "STEP 1: Distributing input files"
    echo "=============================================================="
    echo ""
    
    python3 scripts/distribute_input.py
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "[OK] Distribution completed successfully"
        return 0
    else
        echo "[ERROR] Distribution failed"
        return 1
    fi
}

# Send base files to all machines
send_base_all() {
    local num_machines=$(get_num_machines)
    
    echo "=============================================================="
    echo "Sending BASE files to all $num_machines machines"
    echo "=============================================================="
    echo ""
    
    for i in $(seq 1 $num_machines); do
        echo "--- Machine $i ---"
        bash scripts/transfer.sh $i --send-base
        
        if [ $? -eq 0 ]; then
            echo "[OK] Machine $i: Base files sent successfully"
        else
            echo "[ERROR] Machine $i: Failed to send base files"
        fi
        echo ""
    done
    
    echo "Base files sent to all machines"
}

# Send input files to all machines
send_input_all() {
    local num_machines=$(get_num_machines)
    
    echo "=============================================================="
    echo "Sending INPUT files to all $num_machines machines"
    echo "=============================================================="
    echo ""
    
    for i in $(seq 1 $num_machines); do
        echo "--- Machine $i ---"
        bash scripts/transfer.sh $i --send-input
        
        if [ $? -eq 0 ]; then
            echo "[OK] Machine $i: Input files sent successfully"
        else
            echo "[ERROR] Machine $i: Failed to send input files"
        fi
        echo ""
    done
    
    echo "Input files sent to all machines"
}

# Send both base and input to all machines
send_all() {
    send_base_all
    echo ""
    send_input_all
}

# Run on all machines
run_all() {
    local num_machines=$(get_num_machines)
    
    echo "=============================================================="
    echo "Starting processing on all $num_machines machines"
    echo "=============================================================="
    echo ""
    
    for i in $(seq 1 $num_machines); do
        echo "--- Machine $i ---"
        bash scripts/remote_execute.sh $i --run &
        echo ""
    done
    
    echo "Processing started on all machines"
}

# Check all machines
check_all() {
    local num_machines=$(get_num_machines)
    
    echo "=============================================================="
    echo "Checking status on all $num_machines machines"
    echo "=============================================================="
    echo ""
    
    local finished=0
    local running=0
    
    for i in $(seq 1 $num_machines); do
        bash scripts/remote_execute.sh $i --check > /dev/null 2>&1
        
        if [ $? -eq 0 ]; then
            echo "Machine $i: [FINISHED]"
            ((finished++))
        else
            echo "Machine $i: [RUNNING]"
            ((running++))
        fi
    done
    
    echo ""
    echo "=============================================================="
    echo "Finished: $finished"
    echo "Running: $running"
    echo "Total: $num_machines"
    echo "=============================================================="
}

# Retrieve from all machines
retrieve_all() {
    local num_machines=$(get_num_machines)
    
    echo "=============================================================="
    echo "Retrieving output from all $num_machines machines"
    echo "=============================================================="
    echo ""
    
    for i in $(seq 1 $num_machines); do
        echo "--- Machine $i ---"
        bash scripts/transfer.sh $i --retrieve-output
        
        if [ $? -eq 0 ]; then
            echo "[OK] Machine $i: Retrieved successfully"
        else
            echo "[ERROR] Machine $i: Failed"
        fi
        echo ""
    done
    
    echo "Retrieve operation completed for all machines"
}

# Clean all machines
clean_all() {
    local num_machines=$(get_num_machines)
    
    echo "=============================================================="
    echo "Cleaning workspace on all $num_machines machines"
    echo "=============================================================="
    echo ""
    
    for i in $(seq 1 $num_machines); do
        echo "--- Machine $i ---"
        bash scripts/transfer.sh $i --clean
        
        if [ $? -eq 0 ]; then
            echo "[OK] Machine $i: Cleaned successfully"
        else
            echo "[ERROR] Machine $i: Clean failed"
        fi
        echo ""
    done
    
    echo "Clean operation completed for all machines"
}

# Full automated run
full_run() {
    echo "=============================================================="
    echo "FULL AUTOMATED RUN"
    echo "=============================================================="
    echo ""
    
    # Step 1: Distribute
    distribute
    if [ $? -ne 0 ]; then
        echo "Failed at distribution step"
        return 1
    fi
    
    echo ""
    sleep 2
    
    # Step 2: Send base to all
    send_base_all
    
    echo ""
    sleep 2
    
    # Step 3: Send input to all
    send_input_all
    
    echo ""
    sleep 2
    
    # Step 4: Run on all
    run_all
    
    echo ""
    echo "=============================================================="
    echo "Full run initiated successfully!"
    echo "=============================================================="
    echo ""
    echo "Use '$0 check-all' to monitor progress"
    echo "Use '$0 retrieve-all' to get results when finished"
}

# Individual operations
send_base_one() {
    local machine_id=$1
    echo "Sending base files to machine $machine_id..."
    bash scripts/transfer.sh $machine_id --send-base
}

send_input_one() {
    local machine_id=$1
    echo "Sending input files to machine $machine_id..."
    bash scripts/transfer.sh $machine_id --send-input
}

send_one() {
    local machine_id=$1
    echo "Sending base + input to machine $machine_id..."
    bash scripts/transfer.sh $machine_id --send-base --send-input
}

run_one() {
    local machine_id=$1
    echo "Running on machine $machine_id..."
    bash scripts/remote_execute.sh $machine_id --run
}

check_one() {
    local machine_id=$1
    bash scripts/remote_execute.sh $machine_id --check
}

retrieve_one() {
    local machine_id=$1
    echo "Retrieving from machine $machine_id..."
    bash scripts/transfer.sh $machine_id --retrieve-output
}

clean_one() {
    local machine_id=$1
    echo "Cleaning workspace on machine $machine_id..."
    bash scripts/transfer.sh $machine_id --clean
}

# Main
if [ $# -eq 0 ]; then
    show_help
    exit 0
fi

case "$1" in
    distribute)
        distribute
        ;;
    send-base-all)
        send_base_all
        ;;
    send-input-all)
        send_input_all
        ;;
    send-all)
        send_all
        ;;
    run-all)
        run_all
        ;;
    check-all)
        check_all
        ;;
    retrieve-all)
        retrieve_all
        ;;
    clean-all)
        clean_all
        ;;
    full-run)
        full_run
        ;;
    send-base)
        if [ -z "$2" ]; then
            echo "Error: Machine ID required"
            exit 1
        fi
        send_base_one $2
        ;;
    send-input)
        if [ -z "$2" ]; then
            echo "Error: Machine ID required"
            exit 1
        fi
        send_input_one $2
        ;;
    send)
        if [ -z "$2" ]; then
            echo "Error: Machine ID required"
            exit 1
        fi
        send_one $2
        ;;
    run)
        if [ -z "$2" ]; then
            echo "Error: Machine ID required"
            exit 1
        fi
        run_one $2
        ;;
    check)
        if [ -z "$2" ]; then
            echo "Error: Machine ID required"
            exit 1
        fi
        check_one $2
        ;;
    retrieve)
        if [ -z "$2" ]; then
            echo "Error: Machine ID required"
            exit 1
        fi
        retrieve_one $2
        ;;
    clean)
        if [ -z "$2" ]; then
            echo "Error: Machine ID required"
            exit 1
        fi
        clean_one $2
        ;;
    -h|--help)
        show_help
        ;;
    *)
        echo "Error: Unknown command '$1'"
        echo ""
        show_help
        exit 1
        ;;
esac

exit 0