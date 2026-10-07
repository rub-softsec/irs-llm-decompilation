import json
import re
import math
import os
import argparse
from pathlib import Path

def calculate_halstead_metrics(code):
    """Calculate Halstead metrics for given C code"""
    
    # C operators (including keywords as operators)
    operators = [
        # Arithmetic
        r'\+\+', r'--', r'\+', r'-', r'\*', r'/', r'%',
        # Assignment
        r'=', r'\+=', r'-=', r'\*=', r'/=', r'%=',
        # Comparison
        r'==', r'!=', r'<=', r'>=', r'<', r'>',
        # Logical
        r'&&', r'\|\|', r'!',
        # Bitwise
        r'&', r'\|', r'\^', r'~', r'<<', r'>>',
        # Other
        r'\?', r':', r';', r',', r'\(', r'\)', r'\{', r'\}', r'\[', r'\]'
    ]
    
    # C keywords (also counted as operators in Halstead)
    keywords = [
        'auto', 'break', 'case', 'char', 'const', 'continue', 'default', 'do',
        'double', 'else', 'enum', 'extern', 'float', 'for', 'goto', 'if',
        'int', 'long', 'register', 'return', 'short', 'signed', 'sizeof',
        'static', 'struct', 'switch', 'typedef', 'union', 'unsigned', 'void',
        'volatile', 'while'
    ]
    
    # Clean code: remove comments and strings
    clean_code = re.sub(r'//.*', '', code)  # Remove single-line comments
    clean_code = re.sub(r'/\*.*?\*/', '', clean_code, flags=re.DOTALL)  # Remove multi-line comments
    clean_code = re.sub(r'"[^"]*"', '""', clean_code)  # Replace string literals
    clean_code = re.sub(r"'[^']*'", "''", clean_code)  # Replace char literals
    
    # Count operators (symbols)
    operator_counts = {}
    for op_pattern in operators:
        matches = re.findall(op_pattern, clean_code)
        if matches:
            operator_counts[op_pattern] = len(matches)
    
    # Count keywords (also operators in Halstead)
    keyword_counts = {}
    for keyword in keywords:
        pattern = r'\b' + keyword + r'\b'
        matches = re.findall(pattern, clean_code)
        if matches:
            keyword_counts[keyword] = len(matches)
    
    # Count operands (identifiers, constants)
    # 1. Find all identifiers (variables, functions, etc.)
    identifier_pattern = r'\b[a-zA-Z_][a-zA-Z0-9_]*\b'
    all_identifiers = re.findall(identifier_pattern, clean_code)
    
    # Remove keywords from identifiers (keywords are operators, not operands)
    identifiers = [id for id in all_identifiers if id not in keywords]
    
    # 2. Find numeric constants
    number_pattern = r'\b\d+(?:\.\d+)?\b'
    numbers = re.findall(number_pattern, clean_code)
    
    # 3. Find string/char constants (already cleaned but count them)
    string_pattern = r'""'
    char_pattern = r"''"
    strings = re.findall(string_pattern, clean_code)
    chars = re.findall(char_pattern, clean_code)
    
    # Count all operands and their frequencies
    operand_counts = {}
    
    # Count identifiers
    for identifier in identifiers:
        operand_counts[identifier] = operand_counts.get(identifier, 0) + 1
    
    # Count numeric constants
    for number in numbers:
        operand_counts[number] = operand_counts.get(number, 0) + 1
    
    # Count string constants (treat each as generic string operand)
    if strings:
        operand_counts['string_literal'] = len(strings)
    
    # Count char constants (treat each as generic char operand)  
    if chars:
        operand_counts['char_literal'] = len(chars)
    
    # Calculate basic Halstead measures
    n1 = len(operator_counts) + len(keyword_counts)  # Number of distinct operators
    n2 = len(operand_counts)  # Number of distinct operands
    N1 = sum(operator_counts.values()) + sum(keyword_counts.values())  # Total operators
    N2 = sum(operand_counts.values())  # Total operands
    
    # Calculate derived measures
    vocabulary = n1 + n2  # n = n1 + n2
    length = N1 + N2  # N = N1 + N2
    
    # Avoid mathematical errors
    if vocabulary <= 1:
        volume = 0
    else:
        volume = length * math.log2(vocabulary)  # V = N * log2(n)
    
    if n2 == 0:
        difficulty = 0
    else:
        difficulty = (n1 / 2) * (N2 / n2)  # D = (n1/2) * (N2/n2)
    
    effort = difficulty * volume  # E = D * V
    
    return {
        'n1': n1,
        'N1': N1,
        'n2': n2,
        'N2': N2,
        'vocabulary': vocabulary,
        'length': length,
        'volume': round(volume, 6),
        'difficulty': round(difficulty, 6),
        'effort': round(effort, 6)
    }


def process_functions_with_map(input_dir, map_file, output_file):
    """Process C functions using address mapping and calculate Halstead metrics"""
    
    # Create output directory if it doesn't exist
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Load map file
    print(f"Loading map file: {map_file}")
    try:
        with open(map_file, 'r', encoding='utf-8') as f:
            map_data = json.load(f)
    except Exception as e:
        print(f"Error loading map file: {e}")
        return
    
    total_records = len(map_data)
    processed_records = []
    excluded_count = 0
    
    print(f"Total records in map: {total_records}")
    print("Processing functions...\n")
    
    for idx, entry in enumerate(map_data, 1):
        name = entry.get('name', '')
        addr = entry.get('addr', '')
        
        # Build the file path based on address
        # The .c files are expected to be named "0xADDR.c"
        c_file_path = Path(input_dir) / f"{addr}.c"
        
        if not c_file_path.exists():
            # Try without 0x prefix if default fails
            c_file_path_alt = Path(input_dir) / f"{addr.replace('0x', '')}.c"
            if c_file_path_alt.exists():
                c_file_path = c_file_path_alt
            else:
                # print(f"[{idx}/{total_records}]  File not found: {c_file_path} (excluding)")
                excluded_count += 1
                continue
        
        try:
            # Read the C function code
            with open(c_file_path, 'r', encoding='utf-8') as f:
                func_code = f.read()
            
            # Calculate Halstead metrics
            halstead_metrics = calculate_halstead_metrics(func_code)
            
            # Create new entry with Halstead metrics
            new_entry = {
                'name': name,
                'addr': addr,
                'halstead': halstead_metrics
            }
            
            processed_records.append(new_entry)
            # print(f"[{idx}/{total_records}] Processed: {addr} ({name})")
            
        except Exception as e:
            print(f"[{idx}/{total_records}] Error processing {addr}: {e}")
            excluded_count += 1
    
    # Save results
    print(f"\nSaving results to: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(processed_records, f, indent=2)
    
    # Print statistics
    processed_count = len(processed_records)
    print("\n" + "="*60)
    print("STATISTICS")
    print("="*60)
    print(f"Total records in map:     {total_records}")
    print(f"Successfully processed:   {processed_count}")
    print(f"Excluded (not found):     {excluded_count}")
    percentage = (processed_count/total_records*100) if total_records > 0 else 0
    print(f"Success rate:             {percentage:.2f}%")
    print("="*60)


# Main execution
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calculate Halstead metrics for extracted Pseudo-C functions.")
    
    # Default paths based on pipeline structure
    default_input_dir = os.path.join('..', '5.obtain_functions_v8', 'output')
    default_map_file = os.path.join('..', '4.analyze_logs', 'map_covered.json')
    default_output_file = "output/metrics.json"
    
    parser.add_argument('--input_dir', default=default_input_dir,
                        help=f"Directory containing .c files (default: {default_input_dir})")
    parser.add_argument('--map_file', default=default_map_file,
                        help=f"JSON map of functions to process (default: {default_map_file})")
    parser.add_argument('--output_file', default=default_output_file,
                        help=f"Output JSON file for metrics (default: {default_output_file})")
    
    args = parser.parse_args()
    
    process_functions_with_map(args.input_dir, args.map_file, args.output_file)
    print("\nProcess completed!")