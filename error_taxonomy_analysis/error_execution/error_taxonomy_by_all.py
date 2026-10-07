import os
import re
from collections import defaultdict
import json

class ConsolidatedExecutionAnalyzer:
    """
    Analyzes EXECUTION errors grouped by: Model > IR > Optimization.
    
    This class consolidates statistics by ignoring individual iterations, providing
    an aggregated view of runtime characteristics across all experiments.
    """
    
    def __init__(self, root_dir="input", output_file="consolidated_execution_taxonomy.json"):
        """
        Initialize the analyzer.
        
        Args:
            root_dir (str): Input directory containing execution logs.
            output_file (str): Output JSON filename for the consolidated report.
        """
        self.root_dir = root_dir
        self.output_file = output_file
        
        # --- EXECUTION PATTERNS (Same as the main script) ---
        self.detailed_patterns = {
            'logic': {
                'wrong_logic': [r"Expected {.*}, Got {.*}$"]
            },
            'runtime_exceptions': {
                'memory_corruption': [r"Exception - generator didn't stop after throw", r"Exception - Expecting value: line 1 column 1"],
            },
            'control_flow': {
                'infinite_loop': [r"Command.*timed out after 60 seconds$"]
            },
            'unclassified': {
                'unclassified': []
            }
        }
        self.compiled_patterns = self._compile_detailed_patterns()
        
        # Regex to detect individual test case lines in the log
        self.test_line_pattern = re.compile(r'^  - Test \d+: (.*)$', re.MULTILINE)
    
    def _compile_detailed_patterns(self):
        """Pre-compile regex patterns for efficiency."""
        compiled = {}
        for category, subcategories in self.detailed_patterns.items():
            compiled[category] = {}
            for subcat, patterns in subcategories.items():
                compiled[category][subcat] = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
        return compiled
    
    def extract_test_failures(self, content):
        """Extract test failure lines from the log."""
        test_failures = self.test_line_pattern.findall(content)
        return test_failures
    
    def classify_error_detailed(self, content):
        """
        Classify the error content.
        
        Returns:
            list: A list of unique (category, subcategory) tuples found in the file.
        """
        # If all tests passed, there is no error to classify
        if "ALL TESTS PASSED" in content:
            return []
        
        # Extract specific failure lines
        test_failures = self.extract_test_failures(content)
        
        # If no explicit test lines found, check the entire content
        # (could be a crash before tests ran, or a global timeout)
        lines_to_check = test_failures if test_failures else [content]
        
        classifications = set()
        has_unrecognized = False
        
        for line in lines_to_check:
            test_classified = False
            
            for category, subcategories in self.compiled_patterns.items():
                if category == 'unclassified': continue
                    
                for subcat, patterns in subcategories.items():
                    for pattern in patterns:
                        if pattern.search(line):
                            classifications.add((category, subcat))
                            test_classified = True
                            break
                    if test_classified: break
                if test_classified: break
            
            if not test_classified:
                has_unrecognized = True
        
        # If unclassified failures occurred or nothing specific was found but it failed
        if has_unrecognized or (not classifications and lines_to_check):
            classifications.add(('unclassified', 'unclassified'))
        
        return list(classifications)

    def accumulate_data(self):
        """
        Traverse directories and accumulate counts by Model > IR > Opt.
        """
        # Dictionary structure: Model -> IR -> Opt -> Category -> Subcategory -> Count
        raw_results = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(int)))))
        
        if not os.path.exists(self.root_dir):
            print(f"Error: Directory {self.root_dir} does not exist")
            return None
        
        total_files = 0
        processed_errors = 0
        
        # Traversal: root/iteration/model/ir/opt/file.txt
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
                        
                        # Execution logs are usually .txt files
                        files = [f for f in os.listdir(opt_path) if f.endswith('.txt')]
                        
                        for file in files:
                            path = os.path.join(opt_path, file)
                            try:
                                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                                    content = f.read()
                                
                                # Get classifications
                                classifications = self.classify_error_detailed(content)
                                
                                if classifications:
                                    processed_errors += 1
                                    for category, subcat in classifications:
                                        raw_results[model][ir_type][opt_level][category][subcat] += 1
                                
                                total_files += 1
                            except Exception as e:
                                print(f"Error reading {path}: {e}")

        print(f"Processing complete. {total_files} files read, {processed_errors} contained errors.")
        return raw_results

    def calculate_rich_statistics(self, raw_results):
        """Calculate totals, proportions, and detailed JSON structure."""
        final_output = {}
        
        for model in raw_results:
            final_output[model] = {}
            for ir_type in raw_results[model]:
                final_output[model][ir_type] = {}
                for opt_level in raw_results[model][ir_type]:
                    
                    config_data = raw_results[model][ir_type][opt_level]
                    
                    # Totals
                    category_totals = {}
                    grand_total = 0
                    
                    for category, subcategories in config_data.items():
                        cat_total = sum(subcategories.values())
                        category_totals[category] = cat_total
                        grand_total += category_total
                    
                    if grand_total > 0:
                        config_props = {
                            'total_errors': grand_total,
                            'category_counts': category_totals,
                            'category_proportions': {
                                cat: count/grand_total for cat, count in category_totals.items()
                            },
                            'subcategory_details': {}
                        }
                        
                        # Subcategories
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
        with open(self.output_file, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Results exported to: {self.output_file}")

    def print_summary(self, data):
        print("\n=== EXECUTION SUMMARY (Consolidated) ===")
        for model in sorted(data.keys()):
            print(f"Model: {model}")
            for ir in sorted(data[model].keys()):
                for opt in sorted(data[model][ir].keys()):
                    info = data[model][ir][opt]
                    print(f"  [{ir}][{opt}] -> Total Errors: {info['total_errors']}")
                    # Show the most common category
                    if info['category_counts']:
                        top_cat = max(info['category_counts'], key=info['category_counts'].get)
                        print(f"      Top Category: {top_cat} ({info['category_counts'][top_cat]})")

def main():
    analyzer = ConsolidatedExecutionAnalyzer()
    print("Analyzing execution errors (consolidating iterations)...")
    
    raw_data = analyzer.accumulate_data()
    
    if raw_data:
        rich_stats = analyzer.calculate_rich_statistics(raw_data)
        analyzer.save_json(rich_stats)
        analyzer.print_summary(rich_stats)
    else:
        print("No data found to process.")

if __name__ == "__main__":
    main()