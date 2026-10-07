#!/usr/bin/env python3
"""
Script to analyze V8 testing logs and classify functions.

This script processes the execution logs from the previous step (3.V8_testing)
to determine which functions caused V8 test failures (Critical) and which did not
(Non-Critical). It outputs two JSON maps: one for passed functions and one for failed functions.
"""

import os
import sys
import json
import argparse

def parse_logs(log_directory):
    """
    Parses log files in the directory to find failed tests.
    
    Args:
        log_directory (str): Path to the directory containing .log files.
        
    Returns:
        set: A set of function addresses (or identifiers) that failed the tests.
    """
    failed_funcs = set()
    passed_funcs = set()
    
    if not os.path.exists(log_directory):
        print(f"Error: Log directory '{log_directory}' not found.")
        return failed_funcs, passed_funcs
        
    print(f"Scanning logs in: {log_directory}")
    
    # Walk through directory to handle potential subdirectories
    for root, dirs, files in os.walk(log_directory):
        for filename in files:
            if not filename.endswith('.log'):
                continue
                
            filepath = os.path.join(root, filename)
            
            # The filename is usually '0xADDR.log' or 'NAME.log'. 
            # We assume the identifier corresponds to the filename without extension.
            identifier = os.path.splitext(filename)[0]
            
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                    # Check for explicit failure markers from run_tests.sh
                    if "FAILED" in content:
                        failed_funcs.add(identifier)
                    elif "SUCCESS" in content:
                        passed_funcs.add(identifier)
                    else:
                        print(f"Warning: ambiguous result in {filename}")
            except Exception as e:
                print(f"Error reading {filename}: {e}")
                
    return failed_funcs, passed_funcs

def classify_functions(input_map_path, failed_ids, passed_ids, output_passed, output_failed):
    """
    Classifies functions from the input map into passed and failed lists.
    
    Args:
        input_map_path (str): Path to the original input map (map_usable.json).
        failed_ids (set): Set of identifiers that failed.
        passed_ids (set): Set of identifiers that passed.
        output_passed (str): Path to save the passed functions map.
        output_failed (str): Path to save the failed functions map.
    """
    try:
        with open(input_map_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error loading input map {input_map_path}: {e}")
        sys.exit(1)
        
    passed_entries = []
    failed_entries = []
    missing_logs = []
    
    for entry in data:
        addr = entry.get('addr')
        # Handle potential 0x prefix consistency. 
        # Check if the addr matches our identifiers directly.
        # Identifiers from filenames likely match the 'addr' field since we named them that way.
        
        # Try exact match
        if addr in failed_ids:
            failed_entries.append(entry)
        elif addr in passed_ids:
            passed_entries.append(entry)
        else:
            # Try matching with/without 0x prefix just in case
            addr_clean = addr.replace("0x", "")
            if addr_clean in failed_ids:
                failed_entries.append(entry)
            elif addr_clean in passed_ids:
                passed_entries.append(entry)
            else:
                missing_logs.append(entry)

    # Save outputs
    with open(output_passed, 'w', encoding='utf-8') as f:
        json.dump(passed_entries, f, indent=2)
        
    with open(output_failed, 'w', encoding='utf-8') as f:
        json.dump(failed_entries, f, indent=2)
        
    print(f"\nClassification Complete:")
    print(f"  Total input entries: {len(data)}")
    print(f"  Not Covered (Passed Tests): {len(passed_entries)} -> Saved to {output_passed}")
    print(f"  Covered (Failed Tests)    : {len(failed_entries)} -> Saved to {output_failed}")
    
    if missing_logs:
        print(f"  Missing logs for {len(missing_logs)} entries (skipping)")

def main():
    parser = argparse.ArgumentParser(
        description="Classify functions based on V8 testing logs."
    )
    
    # Defaults suited for the pipeline structure
    default_logs = os.path.join('..', '3.V8_testing', 'logs')
    default_map = os.path.join('..', '1.get_usable_functions', 'map_usable.json')
    
    parser.add_argument(
        '--log_dir', 
        default=default_logs,
        help=f"Directory containing log files (default: {default_logs})"
    )
    parser.add_argument(
        '--input_map', 
        default=default_map,
        help=f"Input JSON map of functions (default: {default_map})"
    )
    parser.add_argument(
        '--output_uncovered', 
        default='map_uncovered.json',
        help="Output JSON for functions NOT covered by tests (passed dummy check) (default: map_uncovered.json)"
    )
    parser.add_argument(
        '--output_covered', 
        default='map_covered.json',
        help="Output JSON for functions covered by tests (failed dummy check) (default: map_covered.json)"
    )
    
    args = parser.parse_args()
    
    failed_ids, passed_ids = parse_logs(args.log_dir)
    # Note: passed_ids are "Not Covered", failed_ids are "Covered"
    classify_functions(args.input_map, failed_ids, passed_ids, args.output_uncovered, args.output_covered)

if __name__ == "__main__":
    main()