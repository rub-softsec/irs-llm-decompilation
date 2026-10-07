import json
import os
import math
from collections import defaultdict
import random
import argparse

def process_json_samples(input_file, output_file, max_difficulty=120.0):
    """
    Selects samples using stratified sampling based on Halstead difficulty.
    
    Args:
        input_file: Path to metrics.json
        output_file: Path to save selected.json
        max_difficulty: Maximum difficulty to include (default 120.0 to match original script intent, though it said 75 in prints)
    """
    
    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(output_file)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    # Read and group samples by Halstead difficulty bucket
    samples_by_bucket = defaultdict(list)
    total_samples = 0
    filtered_samples = 0
    
    print(f"reading input file: {input_file}")
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data_array = json.load(f)
            
            for entry in data_array:
                try:
                    # Extract Halstead difficulty
                    halstead_data = entry.get('halstead')
                    if halstead_data is None:
                        continue
                        
                    difficulty = halstead_data.get('difficulty')
                    if difficulty is None:
                        continue
                    
                    # Filter samples with reasonable difficulty range
                    if 1.0 <= difficulty <= max_difficulty:
                        # Calculate bucket (1.0, 2.0, 3.0, ..., N.0)
                        bucket = math.ceil(difficulty)
                        if bucket == 0:  # Edge case for difficulty exactly 0.0
                            bucket = 1
                        
                        samples_by_bucket[bucket].append(entry)
                        total_samples += 1
                    else:
                        filtered_samples += 1
                        
                except (KeyError, TypeError) as e:
                    print(f"Warning: Missing or invalid halstead data in entry: {e}")
                    continue
                    
    except FileNotFoundError:
        print(f"Error: Input file '{input_file}' not found!")
        return
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in file '{input_file}': {e}")
        return
    
    print(f"Total samples with difficulty 1.0-{max_difficulty}: {total_samples}")
    print(f"Samples filtered out (difficulty outside range): {filtered_samples}")
    
    # Select samples for each bucket
    selected_samples = []
    selection_stats = {}
    
    print("\nSelection process:")
    keys = sorted(samples_by_bucket.keys())
    if not keys:
         print("No samples found in valid range.")
         return

    for bucket in keys:
        available = len(samples_by_bucket[bucket])
        
        # Sampling Strategy:
        # If < 25 available, take all.
        
        if available < 25:
            selected_count = available
            selected = samples_by_bucket[bucket]
        else:
            selected_count = 25
            # Randomly sample the required number
            selected = random.sample(samples_by_bucket[bucket], selected_count)
        
        selected_samples.extend(selected)
        selection_stats[bucket] = {
            'total': available,
            'selected': selected_count,
            'percentage': (selected_count / available) * 100 if available > 0 else 0
        }
        
        bucket_range = f"{bucket-1:.1f}-{bucket:.1f}" if bucket > 1 else f"0.0-{bucket:.1f}"
        # print(f"  Bucket {bucket:.1f} ({bucket_range}): {selected_count}/{available}")
    
    # Write selected samples to output file (as JSON array)
    print(f"\nWriting {len(selected_samples)} selected samples to '{output_file}'...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(selected_samples, f, indent=2)
    
    # Print final statistics
    print("\n" + "="*70)
    print("FINAL STATISTICS")
    print("="*70)
    print(f"Total valid samples:     {total_samples}")
    print(f"Total samples selected:  {len(selected_samples)}")
    selection_rate = (len(selected_samples)/total_samples)*100 if total_samples > 0 else 0
    print(f"Overall selection rate:  {selection_rate:.1f}%")
    
    print("\nDetailed breakdown by Halstead difficulty bucket (Top 10 populated):")
    print("Bucket | Range           | Total | Selected | Percentage")
    print("-" * 65)
    
    # Show stats for top buckets by population to avoid huge output list
    sorted_buckets = sorted(selection_stats.items(), key=lambda x: x[1]['total'], reverse=True)[:20]
    
    for bucket, stats in sorted_buckets:
        bucket_range = f"{bucket-1:.1f}-{bucket:.1f}" if bucket > 1 else f"0.0-{bucket:.1f}"
        print(f"{bucket:6.1f} | {bucket_range:15} | {stats['total']:5} | {stats['selected']:8} | {stats['percentage']:9.1f}%")
    
    print("-" * 65)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Select functions using stratified sampling on Halstead difficulty.")
    
    default_input = os.path.join("output", "metrics.json")
    default_output = os.path.join("output", "selected.json")
    
    parser.add_argument('--input_file', default=default_input,
                        help=f"Input metrics JSON (default: {default_input})")
    parser.add_argument('--output_file', default=default_output,
                        help=f"Output selected JSON (default: {default_output})")
    
    args = parser.parse_args()

    # Set random seed for reproducible results
    random.seed(42)
    
    print("Function Selector (Stratified Sampling)")
    print("=" * 70)
    process_json_samples(args.input_file, args.output_file)
    print("\nProcess completed!")