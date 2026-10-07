import json
import os
import math
import random
from collections import defaultdict

class DatasetSelector:
    """
    Selects a balanced subset of function samples from the dataset based on Halstead complexity metrics.
    
    This class implements a stratified sampling strategy to ensure that the final dataset contains 
    a diverse representation of code complexity. It filters samples into difficulty buckets and 
    selects a representative number of samples from each bucket to minimize bias.
    """
    
    def __init__(self, input_dir="input", output_dir="output", random_seed=42):
        """
        Initialize the selector.
        
        Args:
            input_dir (str): Directory containing the scored input dataset.
            output_dir (str): Directory where the selected dataset will be saved.
            random_seed (int): Seed for random number generation to ensure reproducibility.
        """
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.input_file = os.path.join(input_dir, "real_test_scored.jsonl")
        self.output_file = os.path.join(output_dir, "selected.jsonl")
        
        # Set random seed for reproducible results
        random.seed(random_seed)
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

    def process_selection(self):
        """
        Execute the stratified sampling process.
        
        This method performs the following steps:
        1. Reads the input JSONL file containing functions with Halstead metrics.
        2. Filters samples based on a difficulty range (1.0 to 75.0).
        3. Groups valid samples into difficulty buckets.
        4. Performs stratified sampling from each bucket.
        5. Writes the selected samples to the output file.
        6. Prints detailed statistics about the selection process.
        """
        # Read and group samples by Halstead difficulty bucket
        samples_by_bucket = defaultdict(list)
        total_samples = 0
        filtered_samples = 0
        
        print("Reading input file...")
        try:
            with open(self.input_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        sample = json.loads(line.strip())
                        
                        # Extract Halstead difficulty metric
                        halstead_data = sample.get('halstead')
                        if halstead_data is None:
                            continue
                            
                        difficulty = halstead_data.get('difficulty')
                        if difficulty is None:
                            continue
                        
                        # Filter samples with difficulty between 1.0 and 75.0 (inclusive)
                        # This range is chosen to exclude trivial code (very low difficulty) 
                        # and outliers (extremely high difficulty).
                        if 1.0 <= difficulty <= 75.0:
                            # Discretize difficulty into buckets (1.0, 2.0, ..., 75.0)
                            bucket = math.ceil(difficulty)
                            if bucket == 0:  # Handle edge case where difficulty is exactly 0.0
                                bucket = 1
                            
                            samples_by_bucket[bucket].append(sample)
                            total_samples += 1
                        else:
                            filtered_samples += 1
                            
                    except json.JSONDecodeError as e:
                        print(f"Warning: Invalid JSON on line {line_num}: {e}")
                        continue
                    except (KeyError, TypeError) as e:
                        print(f"Warning: Missing or invalid halstead data on line {line_num}: {e}")
                        continue
                        
        except FileNotFoundError:
            print(f"Error: Input file '{self.input_file}' not found!")
            return
        
        print(f"Total samples within difficulty range [1.0, 75.0]: {total_samples}")
        print(f"Samples filtered out (out of range): {filtered_samples}")
        
        # Select samples for each bucket using stratified sampling
        selected_samples = []
        selection_stats = {}
        
        print("\nExecuting stratified sampling...")
        for bucket in sorted(samples_by_bucket.keys()):
            available = len(samples_by_bucket[bucket])
            
            # Sampling Strategy:
            # 1. If available samples < 25: Take all available samples.
            if available < 25:
                selected_count = available
                selected = samples_by_bucket[bucket]
            else:
                selected_count = 25
                # Randomly sample the calculated number of items
                selected = random.sample(samples_by_bucket[bucket], selected_count)
            
            selected_samples.extend(selected)
            selection_stats[bucket] = {
                'total': available,
                'selected': selected_count,
                'percentage': (selected_count / available) * 100
            }
        
        # Write selected samples to output file
        print(f"Writing {len(selected_samples)} selected samples to '{self.output_file}'...")
        with open(self.output_file, 'w', encoding='utf-8') as f:
            for sample in selected_samples:
                f.write(json.dumps(sample) + '\n')
        
        self.print_statistics(total_samples, selected_samples, selection_stats)

    def print_statistics(self, total_samples, selected_samples, selection_stats):
        """
        Print comprehensive statistics about the selection process.
        
        Args:
            total_samples (int): Total number of valid samples processed.
            selected_samples (list): List of selected sample dicts.
            selection_stats (dict): Statistics per bucket.
        """
        print("\n" + "="*70)
        print("FINAL SELECTION STATISTICS")
        print("="*70)
        print(f"Total valid samples processed: {total_samples}")
        print(f"Total samples selected: {len(selected_samples)}")
        
        if total_samples > 0:
             print(f"Overall selection rate: {(len(selected_samples)/total_samples)*100:.1f}%")
        
        print("\nDetailed breakdown by Halstead difficulty bucket:")
        print("Bucket | Range           | Total | Selected | Percentage")
        print("-" * 65)
        
        total_selected = 0
        for bucket in sorted(selection_stats.keys()):
            stats = selection_stats[bucket]
            total_selected += stats['selected']
            bucket_range = f"{bucket-1:.1f}...1-{bucket:.1f}" if bucket > 1 else f"0.0-{bucket:.1f}"
            print(f"{bucket:6.1f} | {bucket_range:15} | {stats['total']:5} | {stats['selected']:8} | {stats['percentage']:9.1f}%")
        
        print("-" * 65)
        if total_samples > 0:
            print(f"TOTAL  | {'':15} | {total_samples:5} | {total_selected:8} | {(total_selected/total_samples)*100:9.1f}%")

def main():
    """Main execution entry point."""
    print("Initializing Dataset Selector based on Halstead Difficulty...")
    print("=" * 70)
    
    selector = DatasetSelector()
    selector.process_selection()
    
    print("\nSelection process completed successfully!")

if __name__ == "__main__":
    main()