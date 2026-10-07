import os
import re
from collections import defaultdict
import json

class ConsolidatedTaxonomyAnalyzer:
    """
    Analyzes compilation errors by ignoring individual iterations.
    
    Groups all errors by Model > IR > Optimization to provide a consolidated view
    of the model's performance across all experiments.
    """
    
    def __init__(self, root_dir="input", output_file="consolidated_error_taxonomy.json"):
        """
        Initialize the consolidated analyzer.
        
        Args:
            root_dir (str): Input directory containing error files.
            output_file (str): Output JSON filename for the consolidated report.
        """
        self.root_dir = root_dir
        self.output_file = output_file
        
        # --- SAME PATTERNS AS THE ORIGINAL SCRIPT ---
        # We reuse the same detailed regex patterns for consistency.
        self.detailed_patterns = {
            'syntax': {
                'missing_syntax_elements': [r"expected ';' before", r"missing ';'", r"expected .* before", r"expected .* at end"],
                'malformed_expression': [r"expected expression before", r"expected primary-expression", r"syntax error before"],
                'invalid_statement': [r"expected statement", r"invalid use of", r"statement not within a loop", r"break statement not within", r"without a previous", r"computed goto must be pointer type", r"is a pointer; did you mean to use", r"exponent has no digits", r"value used where a .* was expected", r"assignment of read-only location"],
                'parse_error': [r"parse error", r"syntax error at end of input"],
                'invalid_suffix': [r"invalid suffix"],
                'invalid_literal': [r"hexadecimal floating constants require an exponent", r"invalid or incomplete multibyte or wide character"]
            },
            'declaration': {
                'undeclared_variable': [r"undeclared \(first use", r"was not declared", r"error: .* undeclared"],
                'undeclared_function': [r"implicit declaration of function", r"undeclared.*function"],
                'multiple_definition': [r"redefinition of", r"multiple definition of", r"redeclared as different kind of symbol", r"duplicate label", r"redeclaration of", r"function definition declared", r"previous declaration"],
                'conflicting_type': [r"conflicting types for"],
                'invalid_declaration': [r"expected declaration", r"declaration does not declare", r"initializer element is not constant", r"label .* used but not defined", r"built-in function .* must be directly called"],
                'unknown_type': [r"unknown type name", r"error: unknown type name"]
            },
            'type': {
                'incompatible_assignment': [r"assignment from incompatible pointer type", r"incompatible types when assigning", r"assignment to expression with array type", r"assignment of read-only variable"],
                'incompatible_initialization': [r"initialization from incompatible pointer type", r"incompatible types when initializing", r"invalid initializer"],
                'invalid_operands': [r"invalid operands to binary", r"array subscript is not an integer"],
                'invalid_conversion': [r"cannot convert", r"invalid conversion", r"non-floating-point arguments in call to function", r"conversion of scalar"],
                'pointer_mismatch': [r"dereferencing pointer to incomplete type", r"in something not a structure or union", r"lvalue required as unary", r"lvalue required as left operand of assignment", r"has no member named", r"called object .* is not a function or function pointer", r"void value not ignored as it ought to be", r"lvalue required as increment operand", r"cast from pointer to integer of different size", r"cast specifies array type", r"array type has incomplete element type"],
                'type_mismatch': [r"incompatible type for argument", r"too few arguments to function", r"too many arguments to function", r"incompatible types when returning", r"non-floating-point argument in call to function", r"used vector type where scalar is required", r"must be an integer constant", r"does not reduce to an integer constant", r"where .* was expected", r"matching constraint references invalid operand number", r"conflicting type qualifiers", r"irst argument must be an integer or floating vector"],
            },
            'preprocessing': {
                'missing_include': [r"fatal error: .*\.h: No such file", r".*\.h: No such file or directory"],
                'file_not_found': [r"No such file or directory", r"cannot open include file"],
                'macro_error': [r"macro .* redefined", r"unterminated #if", r"invalid preprocessing directive"],
                'include_error': [r"#include expects", r"error in #include"]
            },
            'linker': {
                'undefined_reference': [r"undefined reference to", r"unresolved external symbol"],
                'missing_library': [r"cannot find -l", r"library not found"],
                'linker_failure': [r"ld returned .* exit status", r"collect2: error: ld returned"],
                'symbol_error': [r"multiple definition of", r"first defined here"]
            },
            'architecture': {
                'isa_requirements': [r"needs isa option", r"__builtin_.* needs isa option"],
                'assembly_error': [r"operand size mismatch for", r"operand type mismatch for", r"inconsistent operand constraints", r"internal compiler error", r"invalid register name", r"operand has impossible constraints", r"cannot be used in .*asm", r"invalid .*asm", r"bad register name", r"register type mismatch for"],
                'target_mismatch': [r"target specific option mismatch", r"inlining failed.*always_inline.*option mismatch", r"subscripted value is neither array nor pointer nor vector"]
            },
            'other': {
                'unclassified': []
            }
        }
        self.compiled_patterns = self._compile_detailed_patterns()
    
    def _compile_detailed_patterns(self):
        """Pre-compile patterns for efficiency."""
        compiled = {}
        for category, subcategories in self.detailed_patterns.items():
            compiled[category] = {}
            for subcat, patterns in subcategories.items():
                compiled[category][subcat] = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
        return compiled
    
    def parse_error_file(self, filepath):
        """Parse a single error file and return found error categories."""
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            classifications = []
            for category, subcategories in self.compiled_patterns.items():
                for subcat, patterns in subcategories.items():
                    for pattern in patterns:
                        if pattern.search(content):
                            classifications.append((category, subcat))
                            break
                    if classifications and classifications[-1][0] == category:
                        break
            return classifications if classifications else [('other', 'unclassified')]
        except Exception:
            return [('other', 'unclassified')]

    def accumulate_data(self):
        """
        Traverse directories, ignoring the iteration layer, and accumulate raw counts.
        
        The goal is to sum up all errors for a specific (Model, IR, Opt) tuple
        regardless of which iteration they occurred in.
        
        Returns:
            dict: Raw results nested as results[model][ir][opt][category][subcategory] = count
        """
        # Structure: Model -> IR -> Opt -> Category -> Subcategory -> Count
        raw_results = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(int)))))
        
        if not os.path.exists(self.root_dir):
            print(f"Error: Directory {self.root_dir} does not exist")
            return None
        
        total_files = 0
        
        # Expected structure: root/iteration/model/ir/opt/file.error
        for iteration in os.listdir(self.root_dir):
            iter_path = os.path.join(self.root_dir, iteration)
            if not os.path.isdir(iter_path): continue
            
            for model in os.listdir(iter_path):
                model_path = os.path.join(iter_path, model)
                if not os.path.isdir(model_path): continue
                
                for ir_type in os.listdir(model_path):
                    ir_path = os.path.join(model_path, ir_type)
                    if not os.path.isdir(ir_path): continue
                    
                    for opt_level in os.listdir(ir_path):
                        opt_path = os.path.join(ir_path, opt_level)
                        if not os.path.isdir(opt_path): continue
                        
                        error_files = [f for f in os.listdir(opt_path) if f.endswith('.error')]
                        
                        for error_file in error_files:
                            file_path = os.path.join(opt_path, error_file)
                            classifications = self.parse_error_file(file_path)
                            
                            for category, subcat in classifications:
                                # HERE IS WHERE ITERATIONS ARE AGGREGATED (We don't use 'iteration' as a key)
                                raw_results[model][ir_type][opt_level][category][subcat] += 1
                            
                            total_files += 1
                            
        print(f"Processing complete. Total files analyzed: {total_files}")
        return raw_results

    def calculate_rich_statistics(self, raw_results):
        """
        Transform raw counts into a rich JSON structure consistent with the main analysis script.
        """
        final_output = {}
        
        for model in raw_results:
            final_output[model] = {}
            for ir_type in raw_results[model]:
                final_output[model][ir_type] = {}
                for opt_level in raw_results[model][ir_type]:
                    
                    # Raw data for this configuration (Category -> Subcategory -> Count)
                    config_data = raw_results[model][ir_type][opt_level]
                    
                    # 1. Calculate totals per category and grand total
                    category_totals = {}
                    grand_total = 0
                    
                    for category, subcategories in config_data.items():
                        cat_total = sum(subcategories.values())
                        category_totals[category] = cat_total
                        grand_total += cat_total
                    
                    if grand_total > 0:
                        # 2. Rich structure creation
                        config_props = {
                            'total_errors': grand_total,
                            'category_counts': category_totals,
                            'category_proportions': {
                                cat: count/grand_total for cat, count in category_totals.items()
                            },
                            'subcategory_details': {}
                        }
                        
                        # 3. Calculate subcategory details
                        for category, subcategories in config_data.items():
                            if category_totals[category] > 0:
                                config_props['subcategory_details'][category] = {
                                    'counts': dict(subcategories),
                                    'proportions': {
                                        subcat: count/category_totals[category] 
                                        for subcat, count in subcategories.items()
                                    }
                                }
                        
                        final_output[model][ir_type][opt_level] = config_props

        return final_output

    def save_json(self, data):
        """Save the calculated data to a JSON file."""
        with open(self.output_file, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"JSON generated successfully: {self.output_file}")

    def print_summary(self, data):
        """Print a quick summary of the consolidated results."""
        print("\n=== QUICK SUMMARY (CONSOLIDATED) ===")
        for model in data:
            print(f"Model: {model}")
            for ir in data[model]:
                for opt in data[model][ir]:
                    total = data[model][ir][opt]['total_errors']
                    print(f"  - {ir} / {opt}: {total} total errors (consolidated)")

def main():
    """Main entry point."""
    analyzer = ConsolidatedTaxonomyAnalyzer()
    
    print("Starting consolidated analysis...")
    raw_data = analyzer.accumulate_data()
    
    if raw_data:
        rich_stats = analyzer.calculate_rich_statistics(raw_data)
        analyzer.save_json(rich_stats)
        analyzer.print_summary(rich_stats)

if __name__ == "__main__":
    main()