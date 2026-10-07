import os
import json
import glob
import subprocess
import tempfile
from pathlib import Path
from binarytest import Wrapper, diff_io, _get_tmp_path, _run_command, _get_host_process_id
from jsonl_reader import load_jsonl_dataset

_ROOT_PATH_FOR_JSON_HPP = os.path.join(os.path.dirname(__file__), "binarytest")

class BinaryWrapper:
    """Wrapper to execute precompiled .o binaries"""
    
    def __init__(self, binary_path, func_c_signature, cpp_wrapper):
        self.binary_path = binary_path
        self.func_c_signature = func_c_signature
        self.cpp_wrapper = cpp_wrapper
        self._compiled_exe_path = self._compile_with_binary()
    
    def _compile_with_binary(self):
        """Compile the cpp_wrapper linking with the .o binary"""
        with _get_tmp_path(content=None, suffix='.x', delete=False) as executable_path:
            # Clean the cpp_wrapper by removing invalid includes and extern "C" blocks
            cleaned_cpp_wrapper = self._clean_cpp_wrapper(self.cpp_wrapper)
            
            # Create C++ wrapper that includes the external declaration
            extern_declaration = f'extern "C" {{\n{self.func_c_signature};\n}}\n'
            full_cpp_wrapper = extern_declaration + cleaned_cpp_wrapper
            
            with _get_tmp_path(content=full_cpp_wrapper, suffix='.cpp') as cpp_path:
                # Compile linking with the .o binary, including nlohmann path
                cmd = f'g++ -fpermissive -O0 -o {executable_path} {cpp_path} {self.binary_path} -I.. -I {_ROOT_PATH_FOR_JSON_HPP} -I.'
                stdout, stderr = _run_command(cmd)
                
                if stderr:
                    print(f"Compilation warnings/errors: {stderr}")
        
        return Path(executable_path)
    
    def _clean_cpp_wrapper(self, cpp_wrapper):
        """Clean the cpp_wrapper by removing problematic includes and extern blocks"""
        import re
        
        # Remove extern "C" blocks that include temporary files
        cpp_wrapper = re.sub(r'extern\s+"C"\s*\{\s*#include\s+"[^"]*\.c"\s*\}', '', cpp_wrapper)
        
        # Remove standalone #include statements for .c files  
        cpp_wrapper = re.sub(r'#include\s+"[^"]*\.c"', '', cpp_wrapper)
        
        # Remove any remaining references to /tmp/ files
        cpp_wrapper = re.sub(r'#include\s+"[^"]*(/tmp/[^"]*)"', '', cpp_wrapper)
        
        return cpp_wrapper
    
    def __call__(self, inp, return_stdout_and_stderr=False):
        """Execute the binary with JSON input"""
        executable = self._compiled_exe_path
        
        with _get_tmp_path(content=None, suffix='.json') as input_tmp_json_path:
            output_file = ''.join(input_tmp_json_path.split(".")[:1]) + '-out.json'
            
            with open(input_tmp_json_path, 'w') as f:
                json.dump(inp, f)
            
            stdout, stderr = _run_command(f'{executable} {input_tmp_json_path} {output_file}')
            
            with open(output_file, 'r') as f:
                output = json.load(f)
            os.remove(output_file)
        
        if return_stdout_and_stderr:
            return output, stdout, stderr
        
        return output


def scan_input_directory(input_dir):
    """Scan the input directory and return a list of tuples (binary_path, binary_id, relative_path)"""
    binaries = []
    
    if not os.path.exists(input_dir):
        print(f"ERROR: Directory {input_dir} does not exist")
        return binaries
    
    print(f"Scanning directory: {os.path.abspath(input_dir)}")
    
    # Using Path.rglob (based on working code)
    input_path = Path(input_dir)
    
    for binary_file in input_path.rglob("*.o"):
        # Extract the ID from the filename (without extension)
        filename = binary_file.stem
        
        # Get relative path from input directory
        relative_path = binary_file.relative_to(input_path)
        
        # Validate that filename is numeric
        try:
            binary_id = int(filename)
            binaries.append((str(binary_file), binary_id, str(relative_path)))
        except ValueError:
            print(f"WARNING: Skipping {binary_file} - filename '{filename}' is not a valid ID")
    
    print(f"Found {len(binaries)} binary files in {input_dir}")
    
    if len(binaries) == 0:
        print("DEBUG: No .o files found. Directory structure:")
        # Show directory structure for debugging
        for item in input_path.rglob("*"):
            if item.is_file():
                relative_path = item.relative_to(input_path)
                print(f"  FILE: {relative_path}")
            elif item.is_dir() and item != input_path:
                relative_path = item.relative_to(input_path)
                print(f"  DIR:  {relative_path}/")
    
    return binaries


def create_output_structure_from_relative(relative_path, output_dir):
    """Create directory structure in output using relative path"""
    # Change extension from .o to .txt
    rel_path_txt = os.path.splitext(relative_path)[0] + '.txt'
    
    # Create full path in output
    output_path = os.path.join(output_dir, rel_path_txt)
    
    # Create parent directories if they don't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    return output_path


def test_binary_with_json_data(binary_path, json_row, output_path):
    """Test a specific binary with JSON data"""
    # Handle different JSON structures
    if 'text' in json_row:
        row = json_row['text']
    else:
        row = json_row
    
    print(f"Testing function: {row['fname']} (Binary: {binary_path})")
    
    try:
        # Create wrapper for the binary
        binary_wrapper = BinaryWrapper(
            binary_path=binary_path,
            func_c_signature=row['func_head_types'],
            cpp_wrapper=row['real_exe_wrapper']
        )
        
        # Test all input/output pairs
        io_pairs_count = len(row['real_io_pairs'])
        successes = 0
        failed_tests = []
        
        for i in range(io_pairs_count):
            input_data = row['real_io_pairs'][i]['input']
            expected_output = row['real_io_pairs'][i]['output']
            
            try:
                observed_output = binary_wrapper(input_data)
                is_correct = diff_io(observed_output=observed_output, 
                                   expected_output=expected_output)
                
                if is_correct:
                    successes += 1
                else:
                    failed_tests.append(f"Test {i+1}: Expected {expected_output}, Got {observed_output}")
            
            except Exception as e:
                failed_tests.append(f"Test {i+1}: Exception - {str(e)}")
        
        # Write result to output file
        with open(output_path, 'w') as f:
            f.write(f"Function: {row['fname']}\n")
            f.write(f"Binary: {binary_path}\n")
            f.write(f"Tests: {successes}/{io_pairs_count} passed ({(successes/io_pairs_count*100) if io_pairs_count > 0 else 0:.1f}%)\n")
            
            if successes == io_pairs_count:
                f.write("Status: ALL TESTS PASSED ✓\n")
            else:
                f.write("Status: SOME TESTS FAILED ✗\n")
                f.write("\nFailed tests:\n")
                for failed in failed_tests:
                    f.write(f"  - {failed}\n")
        
        print(f"Results written to: {output_path}")
        return successes == io_pairs_count
        
    except Exception as e:
        # Write error to output file
        with open(output_path, 'w') as f:
            f.write(f"Function: {row['fname']}\n")
            f.write(f"Binary: {binary_path}\n")
            f.write(f"Status: COMPILATION/EXECUTION ERROR ✗\n")
            f.write(f"Error: {str(e)}\n")
        
        print(f"ERROR testing {binary_path}: {str(e)}")
        return False


def main():
    input_dir = "input"
    output_dir = "output"
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Scan input directory to find binaries
    binaries = scan_input_directory(input_dir)
    
    if not binaries:
        print("No binary files found. Exiting.")
        return
    
    # 2. Load JSON dataset
    dataset = load_jsonl_dataset("json/selected.jsonl")
    
    # Create dictionary of ID -> JSON data for quick access
    json_data = {}
    for row in dataset:
        # Use the 'id' field from JSON to match with binary filename
        if 'id' in row:
            json_data[row['id']] = row
        else:
            # Fallback to enumeration if no 'id' field
            print(f"WARNING: No 'id' field found in JSON row, using enumeration")
            for i, row in enumerate(dataset):
                json_data[i] = row
            break
    
    # 3. Process each binary
    total_binaries = len(binaries)
    successful_binaries = 0
    
    for binary_path, binary_id, relative_path in binaries:
        print(f"\n{'='*60}")
        print(f"Processing binary: {relative_path} (ID: {binary_id})")
        print(f"Full path: {binary_path}")
        print(f"{'='*60}")
        
        # Check if corresponding JSON exists
        if binary_id not in json_data:
            print(f"WARNING: No JSON data found for binary ID {binary_id}")
            continue
        
        # Create output structure using relative path
        output_path = create_output_structure_from_relative(relative_path, output_dir)
        
        # Test the binary
        success = test_binary_with_json_data(binary_path, json_data[binary_id], output_path)
        
        if success:
            successful_binaries += 1
    
    # 4. Final summary
    print(f"\n{'='*60}")
    print(f"FINAL SUMMARY")
    print(f"{'='*60}")
    print(f"Total binaries processed: {total_binaries}")
    print(f"Successful binaries: {successful_binaries}")
    print(f"Failed binaries: {total_binaries - successful_binaries}")
    print(f"Success rate: {(successful_binaries/total_binaries*100) if total_binaries > 0 else 0:.1f}%")
    print(f"Results saved to: {output_dir}")


if __name__ == '__main__':
    main()