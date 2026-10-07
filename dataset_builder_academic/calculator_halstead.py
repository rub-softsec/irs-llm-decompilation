import json
import re
import math
import os

class HalsteadMetricsCalculator:
    """
    Calculates Halstead complexity metrics for C code snippets.
    
    This class implements the standard Halstead complexity measures, which are software metrics 
    introduced by Maurice Howard Halstead in 1977. These metrics are computed statically 
    from the source code and provide quantitative measures of complexity.
    
    The metrics calculated include:
    - Program Vocabulary (n): n1 + n2
    - Program Length (N): N1 + N2
    - Calculated Program Length (N^): n1 * log2(n1) + n2 * log2(n2)
    - Volume (V): N * log2(n)
    - Difficulty (D): (n1 / 2) * (N2 / n2)
    - Effort (E): D * V
    
    Where:
    - n1: Number of distinct operators
    - n2: Number of distinct operands
    - N1: Total number of occurrences of operators
    - N2: Total number of occurrences of operands
    """
    
    def __init__(self):
        """
        Initialize the calculator with Regex patterns for C language tokens.
        
        Defines the sets of patterns used to identify operators and keywords 
        in standard C code.
        """
        # C operators (including keywords as operators in Halstead definition)
        self.operators = [
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
            # Other structural operators
            r'\?', r':', r';', r',', r'\(', r'\)', r'\{', r'\}', r'\[', r'\]'
        ]
        
        # C keywords (traditionally counted as operators in Halstead analysis)
        self.keywords = [
            'auto', 'break', 'case', 'char', 'const', 'continue', 'default', 'do',
            'double', 'else', 'enum', 'extern', 'float', 'for', 'goto', 'if',
            'int', 'long', 'register', 'return', 'short', 'signed', 'sizeof',
            'static', 'struct', 'switch', 'typedef', 'union', 'unsigned', 'void',
            'volatile', 'while'
        ]

    def _clean_code(self, code):
        """
        Remove comments and normalize string/char literals for analysis.
        
        Args:
            code (str): The raw C source code.
            
        Returns:
            str: The cleaned source code string.
        """
        # Remove single-line comments
        clean_code = re.sub(r'//.*', '', code)
        
        # Remove multi-line comments
        clean_code = re.sub(r'/\*.*?\*/', '', clean_code, flags=re.DOTALL)
        
        # Normalize string literals to empty "" to treat them as a single operand class
        clean_code = re.sub(r'"[^"]*"', '""', clean_code)
        
        # Normalize char literals to empty '' to treat them as a single operand class
        clean_code = re.sub(r"'[^']*'", "''", clean_code)
        
        return clean_code

    def calculate_metrics(self, code):
        """
        Calculate Halstead metrics for the given code snippet.
        
        Args:
            code (str): The C source code string to analyze.
            
        Returns:
            dict: A dictionary containing the computed Halstead metrics (n1, N1, n2, N2, 
                  vocabulary, length, volume, difficulty, effort).
        """
        clean_code = self._clean_code(code)
        
        # --- Operator Analysis ---
        operator_counts = {}
        
        # Count symbolic operators
        for op_pattern in self.operators:
            matches = re.findall(op_pattern, clean_code)
            if matches:
                operator_counts[op_pattern] = len(matches)
        
        # Count keyword operators
        keyword_counts = {}
        for keyword in self.keywords:
            pattern = r'\b' + keyword + r'\b'
            matches = re.findall(pattern, clean_code)
            if matches:
                keyword_counts[keyword] = len(matches)
        
        # --- Operand Analysis ---
        operand_counts = {}
        
        # 1. Identify valid C identifiers (variables, functions, etc.)
        identifier_pattern = r'\b[a-zA-Z_][a-zA-Z0-9_]*\b'
        all_identifiers = re.findall(identifier_pattern, clean_code)
        
        # Filter identifiers that are actually keywords (to avoid double counting)
        identifiers = [id_str for id_str in all_identifiers if id_str not in self.keywords]
        
        for identifier in identifiers:
            operand_counts[identifier] = operand_counts.get(identifier, 0) + 1
        
        # 2. Identify numeric constants
        number_pattern = r'\b\d+(?:\.\d+)?\b'
        numbers = re.findall(number_pattern, clean_code)
        for number in numbers:
            operand_counts[number] = operand_counts.get(number, 0) + 1
        
        # 3. Identify string/char constants (generic operand classes)
        string_pattern = r'""'
        char_pattern = r"''"
        start_strings = re.findall(string_pattern, clean_code)
        if start_strings:
            operand_counts['string_literal'] = len(start_strings)
            
        chars = re.findall(char_pattern, clean_code)
        if chars:
            operand_counts['char_literal'] = len(chars)
        
        # --- Metric Calculation ---
        
        # Basic Counts
        # n1: Number of distinct operators
        n1 = len(operator_counts) + len(keyword_counts)
        
        # n2: Number of distinct operands
        n2 = len(operand_counts)
        
        # N1: Total number of operator occurrences
        N1 = sum(operator_counts.values()) + sum(keyword_counts.values())
        
        # N2: Total number of operand occurrences
        N2 = sum(operand_counts.values())
        
        # Derived Measures
        vocabulary = n1 + n2           # Program Vocabulary (n)
        length = N1 + N2               # Program Length (N)
        
        # Calculate Volume (V)
        # V = N * log2(n)
        if vocabulary <= 1:
            volume = 0
        else:
            volume = length * math.log2(vocabulary)
        
        # Calculate Difficulty (D)
        # D = (n1 / 2) * (N2 / n2)
        if n2 == 0:
            difficulty = 0
        else:
            difficulty = (n1 / 2) * (N2 / n2)
        
        # Calculate Effort (E)
        # E = D * V
        effort = difficulty * volume
        
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

def process_dataset(input_file, output_file):
    """
    Process a JSONL dataset to calculate and append Halstead metrics.
    
    Reads each C function definition from the input file, computes its complexity metrics,
    and writes the annotated data to the output file.
    
    Args:
        input_file (str): Path to the input JSONL file containing 'func_def'.
        output_file (str): Path to the output JSONL file for annotated results.
    """
    calculator = HalsteadMetricsCalculator()
    
    print(f"Processing dataset: {input_file} -> {output_file}")
    
    try:
        with open(input_file, 'r', encoding='utf-8') as infile, \
             open(output_file, 'w', encoding='utf-8') as outfile:
            
            for line_num, line in enumerate(infile, 1):
                try:
                    # Parse JSON line
                    data = json.loads(line.strip())
                    
                    # Extract function code
                    func_code = data.get('func_def', '')
                    
                    if not func_code:
                        print(f"Warning: Empty 'func_def' on line {line_num}")
                        # Keep original data even if empty logic
                        data['halstead'] = None
                        outfile.write(json.dumps(data) + '\n')
                        continue
                    
                    # Calculate Halstead metrics
                    halstead_metrics = calculator.calculate_metrics(func_code)
                    data['halstead'] = halstead_metrics
    
                    # Write modified data
                    outfile.write(json.dumps(data) + '\n')
                    
                except json.JSONDecodeError as e:
                    print(f"Error parsing JSON on line {line_num}: {e}")
                except Exception as e:
                    print(f"Error processing line {line_num}: {e}")
                    
    except FileNotFoundError:
        print(f"Error: Input file '{input_file}' not found.")
    except Exception as e:
        print(f"Critical error during processing: {e}")

def main():
    """Main execution entry point."""
    input_file = "real_test.jsonl"
    output_file = "real_test_scored.jsonl"
    
    if not os.path.exists(input_file):
        print(f"Note: Default input file '{input_file}' not found in current directory.")
        print("Please ensure the script is run from the correct directory or update the file paths.")
        return

    process_dataset(input_file, output_file)
    print(f"Halstead metrics calculation completed. Results saved to '{output_file}'.")

if __name__ == "__main__":
    main()