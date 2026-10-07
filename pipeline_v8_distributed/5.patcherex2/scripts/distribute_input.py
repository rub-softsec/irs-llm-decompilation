#!/usr/bin/env python3
import json
import shutil
from pathlib import Path
from typing import List

def load_machines(json_file: str) -> List[dict]:
    """Loads machine configuration from JSON"""
    with open(json_file, 'r') as f:
        return json.load(f)

def get_all_c_files(input_dir: Path) -> List[Path]:
    """Gets all .c files from input directory"""
    return sorted(list(input_dir.rglob("*.c")))

def distribute_files(c_files: List[Path], num_machines: int, input_dir: Path, output_base: Path):
    """
    Distributes .c files evenly among machines
    maintaining directory hierarchy
    """
    # Calculate how many files per machine
    files_per_machine = len(c_files) // num_machines
    remainder = len(c_files) % num_machines
    
    print(f"Total files: {len(c_files)}")
    print(f"Machines: {num_machines}")
    print(f"Base files per machine: {files_per_machine}")
    print(f"Remainder: {remainder}")
    print("")
    
    # Distribute files
    current_idx = 0
    distribution = {}
    
    for machine_id in range(1, num_machines + 1):
        # The first 'remainder' machines receive an extra file
        num_files = files_per_machine + (1 if machine_id <= remainder else 0)
        
        machine_files = c_files[current_idx:current_idx + num_files]
        distribution[machine_id] = machine_files
        current_idx += num_files
        
        print(f"Machine {machine_id}: {len(machine_files)} files")
    
    print("")
    print("Creating directory structure and copying files...")
    print("")
    
    # Create directory structure and copy files
    for machine_id, files in distribution.items():
        machine_dir = output_base / str(machine_id)
        
        # Clean directory if exists
        if machine_dir.exists():
            shutil.rmtree(machine_dir)
        
        machine_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy each file maintaining hierarchy
        for file_path in files:
            # Get relative path from input_dir
            relative_path = file_path.relative_to(input_dir)
            
            # Create destination path
            dest_path = machine_dir / relative_path
            
            # Create necessary directories
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy file
            shutil.copy2(file_path, dest_path)
        
        print(f"Machine {machine_id}: Created {machine_dir} with {len(files)} files")
    
    print("")
    print("Distribution complete!")
    
    # Create summary
    summary_file = output_base / "distribution_summary.txt"
    with open(summary_file, 'w') as f:
        f.write("File Distribution Summary\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Total files: {len(c_files)}\n")
        f.write(f"Number of machines: {num_machines}\n\n")
        
        for machine_id, files in distribution.items():
            f.write(f"Machine {machine_id}: {len(files)} files\n")
        
        f.write("\n" + "=" * 50 + "\n\n")
        f.write("Detailed file list:\n\n")
        
        for machine_id, files in distribution.items():
            f.write(f"\n--- Machine {machine_id} ---\n")
            for file_path in files:
                relative_path = file_path.relative_to(input_dir)
                f.write(f"  {relative_path}\n")
    
    print(f"Summary saved to: {summary_file}")

def main():
    # Configuration
    machines_json = "machines.json"
    input_dir = Path("input")
    output_base = Path("input_dist")
    
    # Validate input directory exists
    if not input_dir.exists():
        print(f"Error: Directory '{input_dir}' does not exist")
        return 1
    
    # Load machines
    try:
        machines = load_machines(machines_json)
        num_machines = len(machines)
        print(f"Loaded {num_machines} machines from {machines_json}")
        print("")
    except Exception as e:
        print(f"Error loading machines.json: {e}")
        return 1
    
    # Get all .c files
    c_files = get_all_c_files(input_dir)
    
    if not c_files:
        print(f"No .c files found in {input_dir}")
        return 1
    
    # Create base distribution directory
    output_base.mkdir(exist_ok=True)
    
    # Distribute files
    distribute_files(c_files, num_machines, input_dir, output_base)
    
    return 0

if __name__ == "__main__":
    exit(main())