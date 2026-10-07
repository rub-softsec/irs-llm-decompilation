#!/bin/bash

# Configuration
MACHINES_JSON="machines.json"

show_help() {
    echo "V8 Testing Suite - Distributed Processing Master Script"
    echo "========================================================"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  send-base-all          Send base files (v8_dir.zip, main.sh) to all machines"
    echo "  copy-from-5-to-6-all   Copy output from part 1 to input of part 2 on all machines"
    echo "  run-all                Start V8 testing on all machines"
    echo "  check-all              Check testing status on all machines"
    echo "  retrieve-all           Retrieve test results from all machines"
    echo "  clean-all              Clean workspace on all machines"
    echo "  full-run               Execute complete workflow (send-base + copy + run)"
    echo ""
    echo "Individual machine operations:"
    echo "  send-base <id>         Send base files to specific machine"
    echo "  copy-from-5-to-6 <id>  Copy output to input on specific machine"
    echo "  run <id>               Run testing on specific machine"
    echo "  check <id>             Check status on specific machine"
    echo "  retrieve <id>          Retrieve results from specific machine"
    echo "  clean <id>             Clean workspace on specific machine"
    echo ""
    echo "Examples:"
    echo "  $0 send-base-all           # Send base files to all machines"
    echo "  $0 copy-from-5-to-6-all    # Copy outputs to inputs on all machines"
    echo "  $0 run-all                 # Start testing on all"
    echo "  $0 check-all               # Check all machines"
    echo "  $0 retrieve-all            # Get results from all"
    echo "  $0 clean-all               # Clean workspace on all machines"
    echo "  $0 full-run                # Complete automated workflow"
    echo ""
    echo "  $0 send-base 3             # Send base files only to machine 3"
    echo "  $0 copy-from-5-to-6 5      # Copy output to input on machine 5"
    echo "  $0 run 2                   # Run only on machine 2"
    echo "  $0 clean 4                 # Clean workspace on machine 4"
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
        if [ $? -eq 0 ]; then
            echo "[OK] Machine $i: Base files sent successfully"
        else
            echo "[ERROR] Machine $i: Failed to send base files"
        fi
        echo ""
    done
    
    echo "Base files sent to all machines"
}

# Copy output from part 1 to input of part 2 on all machines
copy_from_5_to_6_all() {
    local num_machines=$(get_num_machines)
    
    echo "=============================================================="
    echo "Copying output from part 1 to input of part 2 on all $num_machines machines"
    echo "=============================================================="
    echo ""
    
    for i in $(seq 1 $num_machines); do
        echo "--- Machine $i ---"
        bash scripts/transfer.sh $i --copy-from-5-to-6
        
        if [ $? -eq 0 ]; then
        if [ $? -eq 0 ]; then
            echo "[OK] Machine $i: Copy completed successfully"
        else
            echo "[ERROR] Machine $i: Failed to copy"
        fi
        echo ""
    done
    
    echo "Copy operation completed on all machines"
}

# Run on all machines
run_all() {
    local num_machines=$(get_num_machines)
    
    echo "=============================================================="
    echo "Starting V8 testing on all $num_machines machines"
    echo "=============================================================="
    echo ""
    
    for i in $(seq 1 $num_machines); do
        echo "--- Machine $i ---"
        bash scripts/remote_execute.sh $i --run &
        echo ""
    done
    
    wait
    echo "Testing started on all machines"
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
    echo "Retrieving test results from all $num_machines machines"
    echo "=============================================================="
    echo ""
    
    for i in $(seq 1 $num_machines); do
        echo "--- Machine $i ---"
        bash scripts/transfer.sh $i --retrieve-output
        
        if [ $? -eq 0 ]; then
        if [ $? -eq 0 ]; then
            echo "[OK] Machine $i: Retrieved successfully"
        else
            echo "[ERROR] Machine $i: Failed"
        fi
        echo ""
    done
    
    echo "Retrieve operation completed for all machines"
}

# Clean workspace on all machines
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
        if [ $? -eq 0 ]; then
            echo "[OK] Machine $i: Cleaned successfully"
        else
            echo "[ERROR] Machine $i: Failed to clean"
        fi
        echo ""
    done
    
    echo "Clean operation completed on all machines"
}

# Full automated run
full_run() {
    echo "=============================================================="
    echo "FULL AUTOMATED RUN - V8 TESTING SUITE"
    echo "=============================================================="
    echo ""
    
    # Step 1: Send base files
    send_base_all
    if [ $? -ne 0 ]; then
        echo "Failed at send base step"
        return 1
    fi
    
    echo ""
    sleep 2
    
    # Step 2: Copy from part 1 to part 2
    copy_from_5_to_6_all
    if [ $? -ne 0 ]; then
        echo "Failed at copy step"
        return 1
    fi
    
    echo ""
    sleep 2
    
    # Step 3: Run on all
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

copy_from_5_to_6_one() {
    local machine_id=$1
    echo "Copying output to input on machine $machine_id..."
    bash scripts/transfer.sh $machine_id --copy-from-5-to-6
}

run_one() {
    local machine_id=$1
    echo "Running V8 testing on machine $machine_id..."
    bash scripts/remote_execute.sh $machine_id --run
}

check_one() {
    local machine_id=$1
    bash scripts/remote_execute.sh $machine_id --check
}

retrieve_one() {
    local machine_id=$1
    echo "Retrieving results from machine $machine_id..."
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
    send-base-all)
        send_base_all
        ;;
    copy-from-5-to-6-all)
        copy_from_5_to_6_all
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
    copy-from-5-to-6)
        if [ -z "$2" ]; then
            echo "Error: Machine ID required"
            exit 1
        fi
        copy_from_5_to_6_one $2
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