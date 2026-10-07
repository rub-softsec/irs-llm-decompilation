import os
import re
import shutil
from collections import defaultdict, Counter
import json

class ExecutionErrorTaxonomyAnalyzer:
    """
    Analyzes execution error taxonomy with detailed subcategories, file organization, and iteration support.
    
    This class differs from the compilation analyzer as it parses runtime logs (execution output)
    rather than compiler error output. It also distinguishes between 'all tests failed' vs 'partial failure'.
    """
    
    def __init__(self, root_dir="input", output_dir="output"):
        """
        Initialize the analyzer.
        
        Args:
            root_dir (str): Path to the input directory.
            output_dir (str): Path where organized files will be saved.
        """
        self.root_dir = root_dir
        self.output_dir = output_dir
        
        # Regex patterns to identify runtime errors.
        # Categories include: logic errors (wrong output), runtime exceptions (crashes), timeouts.
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
        
        # Regex to detect individual test case lines in the execution log.
        # Example format: "  - Test 1: Expected {1}, Got {2}"
        self.test_line_pattern = re.compile(r'^  - Test \d+: (.*)$', re.MULTILINE)
    
    def _compile_detailed_patterns(self):
        """Pre-compile detailed regex patterns for efficiency."""
        compiled = {}
        for category, subcategories in self.detailed_patterns.items():
            compiled[category] = {}
            for subcat, patterns in subcategories.items():
                compiled[category][subcat] = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
        return compiled
    
    def extract_test_failures(self, content):
        """
        Extract individual test failure lines from the log content.
        
        Args:
            content (str): Full log content.
            
        Returns:
            list: List of strings corresponding to specific test failure lines.
        """
        test_failures = self.test_line_pattern.findall(content)
        return test_failures
    
    def classify_error_detailed(self, content):
        """
        Classify execution error content into detailed taxonomy categories.
        
        Determines if the failure is 'allfailed' (0% pass rate) or 'partialfailed'.
        It then scans failure lines against known error patterns to identify the root cause.
        
        Args:
            content (str): Log content.
        
        Returns:
            tuple: (failure_type, classifications_list)
        """
        # Skip files where all tests passed successfully
        if "ALL TESTS PASSED" in content:
            return None, None
        
        # Extract specific test failure lines to analyze per test case
        test_failures = self.extract_test_failures(content)
        if not test_failures:
            return None, None
        
        # Determine the scope of failure: did everything fail or just some tests?
        if "0/10 passed (0.0%)" in content:
            failure_type = "allfailed"
        else:
            failure_type = "partialfailed"
        
        classifications = set()  # Use set to avoid counting the same error category multiple times per file
        has_unrecognized = False
        
        # Iterate over each failed test line
        for test_failure in test_failures:
            test_classified = False
            
            # Check against all known patterns
            for category, subcategories in self.compiled_patterns.items():
                if category == 'unclassified':
                    continue
                    
                for subcat, patterns in subcategories.items():
                    for pattern in patterns:
                        if pattern.search(test_failure):
                            classifications.add((category, subcat))
                            test_classified = True
                            break
                    if test_classified:
                        break
                if test_classified:
                    break
            
            # If a test failure line didn't match any known pattern, flag it
            if not test_classified:
                has_unrecognized = True
        
        # Add 'unclassified' tag if we found failures that didn't match known patterns
        if has_unrecognized:
            classifications.add(('unclassified', 'unclassified'))
        
        # Ensure we return at least 'unclassified' if the list is empty but we caught failures
        classifications_list = list(classifications) if classifications else [('unclassified', 'unclassified')]
        
        return failure_type, classifications_list
    
    def parse_execution_file(self, filepath):
        """
        Parse a single execution .txt file and return failure info.
        
        Args:
            filepath (str): Absolute path to the file.
            
        Returns:
            tuple: (content, failure_type, classifications)
        """
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            failure_type, classifications = self.classify_error_detailed(content)
            return content, failure_type, classifications
        except Exception as e:
            print(f"Warning: Could not read {filepath}: {e}")
            return "", None, None
    
    def create_output_structure(self):
        """
        Create the output directory structure.
        
        Creates top-level directories for 'allfailed' and 'partialfailed' separation.
        """
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)
        os.makedirs(self.output_dir)
        
        # Create subdirectories for different failure types
        os.makedirs(os.path.join(self.output_dir, "allfailed"))
        os.makedirs(os.path.join(self.output_dir, "partialfailed"))
    
    def copy_execution_file(self, source_path, iteration, model, ir_type, opt_level, filename, 
                           failure_type, category, subcategory):
        """
        Copy execution file to the organized output structure.
        
        Structure: output/failure_type/iteration/category/subcategory/model/ir/opt/filename
        """
        target_dir = os.path.join(self.output_dir, failure_type, iteration, category, subcategory, 
                                 model, ir_type, opt_level)
        os.makedirs(target_dir, exist_ok=True)
        
        target_path = os.path.join(target_dir, filename)
        shutil.copy2(source_path, target_path)
    
    def analyze_and_organize(self):
        """
        Analyze directory structure, classify executions, and organize files.
        
        Returns:
            tuple: (results, file_counts, iteration_file_counts, combination_counts)
        """
        # Results structure: failure_type -> iteration -> model -> ir_type -> opt_level -> category -> subcategory -> count
        results = {
            'allfailed': defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(int)))))),
            'partialfailed': defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(int)))))),
            'combined': defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(int))))))
        }
        
        # File counts: overall -> category -> subcategory, by_type -> failure_type -> category -> subcategory
        file_counts = {
            'overall': defaultdict(lambda: defaultdict(int)),
            'by_type': {
                'allfailed': defaultdict(lambda: defaultdict(int)),
                'partialfailed': defaultdict(lambda: defaultdict(int))
            }
        }
        
        # Iteration file counts for time-series analysis
        iteration_file_counts = {
            'overall': defaultdict(lambda: defaultdict(lambda: defaultdict(int))),
            'by_type': {
                'allfailed': defaultdict(lambda: defaultdict(lambda: defaultdict(int))),
                'partialfailed': defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
            }
        }
        
        # Track which error combinations appear together in the same file
        combination_counts = {
            'overall': defaultdict(int),
            'by_type': {
                'allfailed': defaultdict(int),
                'partialfailed': defaultdict(int)
            }
        }
        
        if not os.path.exists(self.root_dir):
            print(f"Error: Directory {self.root_dir} does not exist")
            return results, file_counts, iteration_file_counts, combination_counts
        
        self.create_output_structure()
        
        total_files = 0
        processed_files = 0
        skipped_files = 0
        
        # Recursively traverse directory structure
        for iteration in os.listdir(self.root_dir):
            iteration_path = os.path.join(self.root_dir, iteration)
            if not os.path.isdir(iteration_path):
                continue
            
            for model in os.listdir(iteration_path):
                model_path = os.path.join(iteration_path, model)
                if not os.path.isdir(model_path):
                    continue
                
                for ir_type in os.listdir(model_path):
                    ir_path = os.path.join(model_path, ir_type)
                    if not os.path.isdir(ir_path):
                        continue
                    
                    for opt_level in os.listdir(ir_path):
                        opt_path = os.path.join(ir_path, opt_level)
                        if not os.path.isdir(opt_path):
                            continue
                        
                        txt_files = [f for f in os.listdir(opt_path) if f.endswith('.txt')]
                        total_files += len(txt_files)
                        
                        for txt_file in txt_files:
                            txt_path = os.path.join(opt_path, txt_file)
                            content, failure_type, classifications = self.parse_execution_file(txt_path)
                            
                            # Skip successful executions (no failure type returned)
                            if failure_type is None or classifications is None:
                                skipped_files += 1
                                continue
                            
                            # Create combination string to track co-occurrence of errors in the same file
                            if classifications:
                                combo_parts = []
                                for category, subcategory in classifications:
                                    combo_parts.append(f"{category}:{subcategory}")
                                combination = ",".join(sorted(combo_parts))
                                combination_counts['overall'][combination] += 1
                                combination_counts['by_type'][failure_type][combination] += 1
                            
                            # Update statistics for each identified classification in the file
                            for category, subcategory in classifications:
                                # Update detailed results tree
                                results[failure_type][iteration][model][ir_type][opt_level][category][subcategory] += 1
                                results['combined'][iteration][model][ir_type][opt_level][category][subcategory] += 1
                                
                                # Update flat counts
                                file_counts['overall'][category][subcategory] += 1
                                file_counts['by_type'][failure_type][category][subcategory] += 1
                                
                                # Update per-iteration counts
                                iteration_file_counts['overall'][iteration][category][subcategory] += 1
                                iteration_file_counts['by_type'][failure_type][iteration][category][subcategory] += 1
                                
                                # Copy file to organized structure (physically copying files)
                                self.copy_execution_file(txt_path, iteration, model, ir_type, opt_level, 
                                                       txt_file, failure_type, category, subcategory)
                            
                            processed_files += 1
        
        print(f"Processed {processed_files} error files, skipped {skipped_files} successful files out of {total_files} total files")
        return results, file_counts, iteration_file_counts, combination_counts
    
    def calculate_detailed_proportions(self, results):
        """
        Calculate relative proportions of error types within each configuration.
        """
        proportions = {}
        
        for failure_type in results:
            proportions[failure_type] = {}
            for iteration in results[failure_type]:
                proportions[failure_type][iteration] = {}
                for model in results[failure_type][iteration]:
                    proportions[failure_type][iteration][model] = {}
                    for ir_type in results[failure_type][iteration][model]:
                        proportions[failure_type][iteration][model][ir_type] = {}
                        for opt_level in results[failure_type][iteration][model][ir_type]:
                            config_data = results[failure_type][iteration][model][ir_type][opt_level]
                            
                            # Calculate totals
                            category_totals = {}
                            grand_total = 0
                            
                            for category, subcategories in config_data.items():
                                category_total = sum(subcategories.values())
                                category_totals[category] = category_total
                                grand_total += category_total
                            
                            if grand_total > 0:
                                config_props = {
                                    'category_counts': category_totals,
                                    'category_proportions': {cat: count/grand_total for cat, count in category_totals.items()},
                                    'subcategory_details': {},
                                    'total_errors': grand_total
                                }
                                
                                # Calculate subcategory proportions
                                for category, subcategories in config_data.items():
                                    if category_totals[category] > 0:
                                        config_props['subcategory_details'][category] = {
                                            'counts': dict(subcategories),
                                            'proportions': {subcat: count/category_totals[category] 
                                                          for subcat, count in subcategories.items()}
                                        }
                                
                                proportions[failure_type][iteration][model][ir_type][opt_level] = config_props
        
        return proportions
    
    def print_detailed_summary(self, proportions, file_counts, iteration_file_counts, combination_counts):
        """
        Print comprehensive summary of detailed execution error taxonomy analysis.
        """
        print("=== DETAILED EXECUTION ERROR TAXONOMY ANALYSIS WITH ITERATIONS ===\n")
        
        # Overall statistics across all iterations and failure types
        print("OVERALL ERROR DISTRIBUTION (ALL ITERATIONS, ALL FAILURE TYPES):")
        total_errors = sum(sum(subcats.values()) for subcats in file_counts['overall'].values())
        
        for category in sorted(file_counts['overall'].keys()):
            category_total = sum(file_counts['overall'][category].values())
            print(f"\n{category.upper()}: {category_total} ({category_total/total_errors:.2%})")
            
            for subcat in sorted(file_counts['overall'][category].keys()):
                count = file_counts['overall'][category][subcat]
                subcat_prop = count / category_total if category_total > 0 else 0
                print(f"  {subcat}: {count} ({subcat_prop:.2%})")
        
        print(f"\nTotal errors analyzed: {total_errors}")
        
        # Breakdown by failure type
        print("\n" + "="*60)
        print("BREAKDOWN BY FAILURE TYPE:")
        
        for failure_type in ['allfailed', 'partialfailed']:
            type_total = sum(sum(subcats.values()) for subcats in file_counts['by_type'][failure_type].values())
            print(f"\n{failure_type.upper()}: {type_total} files ({type_total/total_errors:.2%})")
            
            for category in sorted(file_counts['by_type'][failure_type].keys()):
                category_total = sum(file_counts['by_type'][failure_type][category].values())
                print(f"  {category}: {category_total} ({category_total/type_total:.2%})")
        
        # Combination analysis
        print("\n" + "="*60)
        print("ERROR COMBINATION ANALYSIS:")
        print(f"\nOverall most common combinations:")
        for combo, count in Counter(combination_counts['overall']).most_common(10):
            print(f"  {combo}: {count} files ({count/total_errors:.2%})")
        
        for failure_type in ['allfailed', 'partialfailed']:
            type_total = sum(combination_counts['by_type'][failure_type].values())
            if type_total > 0:
                print(f"\n{failure_type.upper()} most common combinations:")
                for combo, count in Counter(combination_counts['by_type'][failure_type]).most_common(5):
                    print(f"  {combo}: {count} files ({count/type_total:.2%})")
        
        print("\n" + "="*60 + "\n")
    
    def export_detailed_results(self, proportions, file_counts, iteration_file_counts, combination_counts,
                               overall_file="detailed_execution_taxonomy_overall.json",
                               iterations_file="detailed_execution_taxonomy_by_iteration.json",
                               comparison_file="execution_iteration_comparison.json",
                               summary_file="execution_summary_with_iterations.json"):
        """
        Export detailed results to JSON files.
        """
        
        # Export overall detailed proportions (all iterations combined)
        with open(overall_file, 'w') as f:
            json.dump(proportions, f, indent=2)
        
        # Export iteration-specific analysis
        iteration_analysis = {
            'by_iteration': proportions,
            'iteration_file_counts': dict(iteration_file_counts)
        }
        with open(iterations_file, 'w') as f:
            json.dump(iteration_analysis, f, indent=2)
        
        # Export enhanced summary statistics
        summary = {
            'overall_distribution': dict(file_counts),
            'combination_counts': dict(combination_counts),
            'iteration_distribution': dict(iteration_file_counts),
            'total_errors': sum(sum(subcats.values()) for subcats in file_counts['overall'].values()),
            'total_iterations': len(iteration_file_counts['overall']),
            'categories': list(file_counts['overall'].keys()),
            'output_structure_created': True,
            'output_directory': self.output_dir
        }
        
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"Overall results exported to {overall_file}")
        print(f"Iteration-specific analysis exported to {iterations_file}")
        print(f"Enhanced summary statistics exported to {summary_file}")
        print(f"Organized execution files copied to {self.output_dir}/")

def main():
    """Main execution function."""
    analyzer = ExecutionErrorTaxonomyAnalyzer()
    
    print("Analyzing detailed execution error taxonomy with iterations and organizing files...")
    results, file_counts, iteration_file_counts, combination_counts = analyzer.analyze_and_organize()
    
    if not any(results.values()):
        print("No execution error files found or unable to access directory structure.")
        return
    
    proportions = analyzer.calculate_detailed_proportions(results)
    analyzer.print_detailed_summary(proportions, file_counts, iteration_file_counts, combination_counts)
    analyzer.export_detailed_results(proportions, file_counts, iteration_file_counts, combination_counts)
    
    print(f"\nAnalysis complete! Check the '{analyzer.output_dir}' directory for organized error files.")
    print("Remember to fill in the empty patterns in the detailed_patterns dictionary to enable proper classification.")

if __name__ == "__main__":
    main()