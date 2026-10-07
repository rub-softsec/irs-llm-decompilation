"""
Processes files with LLMs using sequential batch processing.
Handles automatic retries and state recovery.
"""

import os
import time
import json
import sys

# Import LLM classes
from models.OpenAI.OpenAI import OpenAI
from models.Anthropic.Anthropic import Anthropic

# Import utility functions
from utils.utils import read_file_content, write_file_content, get_all_files

# File type prompts configuration
FILE_PROMPTS = {
    '.asm': {
        'prologue': [
            "You are an expert reverse engineer. Decompile the following assembly code to equivalent C source code.",
            "Analyze the assembly instructions, registers, memory operations, and control flow to produce functional and compilable C source code.",
            "Assembly code to decompile:",
            "",
            "```"
        ],
        'epilogue': [
            "```",
            "",
            "Output format: Only C code, no explanations, no markdown formatting.",
            "Function name: func0",
            "Variable names: var0, var1, var2, etc.",
            "Include necessary headers (#include) if needed.",
            "Do not include ```c or ``` markers."
        ]
    },
    '.llil': {
        'prologue': [
            "You are an expert reverse engineer. Decompile the following LLIL code to equivalent C source code.",
            "LLIL is Binary Ninja's low-level IR that abstracts away architecture-specific details while preserving low-level semantics.",
            "Analyze the LLIL operations, memory accesses, and control structures to produce functional and compilable C source code.",
            "LLIL code to decompile:",
            "",
            "```"
        ],
        'epilogue': [
            "```",
            "",
            "Output format: Only C code, no explanations, no markdown formatting.",
            "Function name: func0", 
            "Variable names: var0, var1, var2, etc.",
            "Include necessary headers (#include) if needed.",
            "Do not include ```c or ``` markers."
        ]
    },
    '.mlil': {
        'prologue': [
            "You are an expert reverse engineer. Decompile the following MLIL code to equivalent C source code.",
            "MLIL is Binary Ninja's medium-level IR that performs data flow analysis and eliminates many low-level artifacts.",
            "Analyze the MLIL operations, variables, and control flow to produce functional and compilable C source code.",
            "MLIL code to decompile:",
            "",
            "```"
        ],
        'epilogue': [
            "```",
            "",
            "Output format: Only C code, no explanations, no markdown formatting.",
            "Function name: func0",
            "Variable names: var0, var1, var2, etc.",
            "Include necessary headers (#include) if needed.",
            "Do not include ```c or ``` markers."
        ]
    },
    '.hlil': {
        'prologue': [
            "You are an expert reverse engineer. Decompile the following HLIL code to equivalent C source code.",
            "HLIL is Binary Ninja's highest-level IR that recovers high-level constructs like loops, conditionals, and function calls.",
            "Analyze the HLIL operations and structures to produce functional and compilable C source code.",
            "HLIL code to decompile:",
            "",
            "```"
        ],
        'epilogue': [
            "```",
            "",
            "Output format: Only C code, no explanations, no markdown formatting.",
            "Function name: func0",
            "Variable names: var0, var1, var2, etc.",
            "Include necessary headers (#include) if needed.",
            "Do not include ```c or ``` markers."
        ]
    }
}

def get_output_path_by_extension(input_path, input_dir, output_dir, file_extension, llm_model_name):
    """Generate output path organized by LLM model and file extension type."""
    relative_path = os.path.relpath(input_path, input_dir)
    file_dir = os.path.dirname(relative_path)
    file_name = os.path.basename(relative_path)
    file_base = os.path.splitext(file_name)[0]
    
    extension_subdir = file_extension[1:] if file_extension.startswith('.') else file_extension
    clean_model_name = llm_model_name.replace("/", "_").replace(":", "_")
    new_filename = f"{file_base}.c"
    
    if file_dir:
        output_path = os.path.join(output_dir, clean_model_name, extension_subdir, file_dir, new_filename)
    else:
        output_path = os.path.join(output_dir, clean_model_name, extension_subdir, new_filename)
    
    return output_path

def get_file_prompts(file_extension):
    """Get prologue and epilogue for a specific file extension."""
    extension_lower = file_extension.lower()
    
    if extension_lower in FILE_PROMPTS:
        prompts = FILE_PROMPTS[extension_lower]
        prologue_text = '\n'.join(prompts['prologue'])
        epilogue_text = '\n'.join(prompts['epilogue'])
        return prologue_text, epilogue_text
    
    return None, None

def log_error(message):
    """Log error message to error.txt file."""
    try:
        with open("error.txt", "a", encoding="utf-8") as error_file:
            error_file.write(f"{message}\n")
    except Exception as e:
        print(f"Error writing to error.txt: {e}")

def clean_llm_response(response):
    """Clean LLM response by removing markdown code blocks and extra formatting."""
    if not response:
        return response
    
    cleaned = response.strip()
    
    if cleaned.startswith('```c') or cleaned.startswith('```C'):
        first_newline = cleaned.find('\n')
        if first_newline != -1:
            cleaned = cleaned[first_newline + 1:]
    elif cleaned.startswith('```'):
        first_newline = cleaned.find('\n')
        if first_newline != -1:
            cleaned = cleaned[first_newline + 1:]
    
    if cleaned.endswith('```'):
        last_backticks = cleaned.rfind('```')
        if last_backticks != -1:
            cleaned = cleaned[:last_backticks]
    
    return cleaned.strip()

def create_llm_instance(model_name):
    """Create appropriate LLM instance based on model name."""
    if "gpt" in model_name or "openai" in model_name.lower() or "o4" in model_name:
        return OpenAI(model_name)
    elif "claude" in model_name or "anthropic" in model_name.lower():
        return Anthropic(model_name)
    else:
        print(f"Warning: Unknown model type '{model_name}', defaulting to OpenAI")
        return OpenAI(model_name)

def load_state(state_file="batch_state.json"):
    """Load execution state."""
    if os.path.exists(state_file):
        with open(state_file, 'r') as f:
            return json.load(f)
    return {
        'current_session_id': 0,
        'llm_progress': {},
        'batch_info': {}
    }

def save_state(state, state_file="batch_state.json"):
    """Save execution state."""
    with open(state_file, 'w') as f:
        json.dump(state, f, indent=2)

def create_batch_metadata(file_paths, input_directory, llm_model, batch_start_index=0):
    """Create metadata mapping for batch processing."""
    metadata = {}
    for i, file_path in enumerate(file_paths):
        file_extension = os.path.splitext(file_path)[1].lower()
        custom_id = f"{llm_model}_file_{(batch_start_index + i):04d}"
        metadata[custom_id] = {
            'file_path': file_path,
            'file_extension': file_extension,
            'llm_model': llm_model,
            'index': batch_start_index + i
        }
    return metadata

def wait_for_batch_completion(llm, batch_id, check_interval=60):
    """Wait for batch processing to complete."""
    print(f"Waiting for batch {batch_id[:8]}...")
    
    while True:
        try:
            status = llm.check_batch_status(batch_id)
            current_status = status['status']
            progress = status['progress']
            
            if current_status in ['completed', 'failed', 'cancelled']:
                print(f"Batch {batch_id[:8]} status: {current_status}")
                return status
            
            time.sleep(check_interval)
            
        except Exception as e:
            print(f"Error checking batch status: {e}")
            time.sleep(check_interval)

def process_batch_results(batch_id, batch_metadata, llm, input_directory, output_directory):
    """Process completed batch results."""
    try:
        results = llm.download_batch_results(batch_id, save_to_file=True)
        
        success_count = 0
        error_count = 0
        
        for result in results:
            custom_id = result['custom_id']
            response = result['response']
            error = result.get('error')
            
            if error or not response:
                error_count += 1
                continue
            
            file_info = batch_metadata.get(custom_id)
            if not file_info:
                error_count += 1
                continue
            
            try:
                cleaned_response = clean_llm_response(response)
                output_path = get_output_path_by_extension(
                    file_info['file_path'],
                    input_directory,
                    output_directory,
                    file_info['file_extension'],
                    file_info['llm_model']
                )
                
                write_file_content(output_path, cleaned_response)
                success_count += 1
                
            except Exception as e:
                error_count += 1
                log_error(f"Error saving result for {custom_id}: {e}")
        
        print(f"{success_count} files processed, {error_count} errors")
        return error_count == 0
        
    except Exception as e:
        print(f"Error processing batch results: {e}")
        log_error(f"Error processing batch results: {e}")
        return False

def submit_and_process_batch(llm, supported_files, input_directory, output_directory, batch_start, batch_end, session_id, state, batch_id=None):
    """Submit batch and process results sequentially."""
    batch_files = supported_files[batch_start:batch_end]
    batch_num = batch_start // (batch_end - batch_start) + 1
    
    print(f"Range {batch_start}-{batch_end-1}: {len(batch_files)} files")
    
    # Create metadata
    batch_metadata = create_batch_metadata(batch_files, input_directory, llm.model, batch_start)
    
    # If batch_id provided, it's a pending batch - just wait for it
    if batch_id:
        print(f"Waiting for existing batch: {batch_id[:8]}")
        final_status = wait_for_batch_completion(llm, batch_id)
    else:
        # Submit new batch
        queued_count = 0
        for file_path in batch_files:
            try:
                file_content = read_file_content(file_path)
                if file_content is None:
                    continue
                
                file_extension = os.path.splitext(file_path)[1].lower()
                prologue, epilogue = get_file_prompts(file_extension)
                
                if prologue is None or epilogue is None:
                    continue
                
                full_message = prologue + file_content + epilogue
                file_index = batch_files.index(file_path)
                custom_id = f"{llm.model}_file_{(batch_start + file_index):04d}"
                
                llm.add_to_batch_queue(prompt=full_message, custom_id=custom_id)
                queued_count += 1
                
            except Exception as e:
                log_error(f"Error queuing {file_path}: {e}")
        
        if queued_count == 0:
            print(f"No valid files queued")
            return True, None
        
        # Submit batch
        try:
            batch_name = f"{llm.model}_s{session_id}_r{batch_start}-{batch_end-1}"
            batch_id = llm.submit_batch_request(batch_name=batch_name)
            print(f"Submitted: {batch_id[:8]} ({queued_count} files)")
            
            # Save state immediately after submission
            model_key = llm.model
            for range_info in state['llm_progress'][model_key]['ranges']:
                if range_info['start'] == batch_start and range_info['end'] == batch_end:
                    range_info['batch_id'] = batch_id
                    range_info['status'] = 'pending'
                    break
            save_state(state)
            
            # Wait for completion
            final_status = wait_for_batch_completion(llm, batch_id)
            
        except Exception as e:
            print(f"Error submitting: {e}")
            log_error(f"Error in submit_and_process_batch: {e}")
            return False, None
    
    # Save batch info for compatibility (always save, regardless of status)
    batch_info = {
        'batch_id': batch_id,
        'model': llm.model,
        'metadata': batch_metadata,
        'created_at': time.time(),
        'status': 'submitted',
        'session_id': session_id,
        'range_start': batch_start,
        'range_end': batch_end
    }
    
    batch_info_file = "batch_info.json"
    if os.path.exists(batch_info_file):
        with open(batch_info_file, 'r') as f:
            all_batches = json.load(f)
    else:
        all_batches = {}
    
    all_batches[batch_id] = batch_info
    
    # Process results
    if final_status['status'] == 'completed':
        success = process_batch_results(batch_id, batch_metadata, llm, input_directory, output_directory)
        
        # Update batch info with final status
        all_batches[batch_id]['status'] = 'processed' if success else 'error'
        all_batches[batch_id]['completed_at'] = time.time()
        
        with open(batch_info_file, 'w') as f:
            json.dump(all_batches, f, indent=2)
        
        return success, batch_id
    else:
        print(f"Batch failed: {final_status['status']}")
        # Update batch info with failed status
        all_batches[batch_id]['status'] = 'failed'
        all_batches[batch_id]['completed_at'] = time.time()
        
        with open(batch_info_file, 'w') as f:
            json.dump(all_batches, f, indent=2)
        
        return False, batch_id

def process_llm_batches(llm, supported_files, input_directory, output_directory, batch_size, state, max_retries=3):
    """Process all batches for one LLM with retry logic."""
    model_key = llm.model
    session_id = state['current_session_id']
    total_files = len(supported_files)
    
    # Initialize LLM progress if not exists
    if model_key not in state['llm_progress']:
        state['llm_progress'][model_key] = {
            'session_id': session_id,
            'ranges': []
        }
        
        # Create initial ranges
        for start in range(0, total_files, batch_size):
            end = min(start + batch_size, total_files)
            state['llm_progress'][model_key]['ranges'].append({
                'start': start,
                'end': end,
                'status': 'pending',
                'batch_id': None,
                'retries': 0
            })
    
    llm_progress = state['llm_progress'][model_key]
    
    # Reset session if different
    if llm_progress['session_id'] != session_id:
        print(f"New session for {model_key}, resetting to pending")
        llm_progress['session_id'] = session_id
        for range_info in llm_progress['ranges']:
            if range_info['status'] != 'completed':
                range_info['status'] = 'pending'
                range_info['batch_id'] = None
                range_info['retries'] = 0
    
    # Count status
    completed = sum(1 for r in llm_progress['ranges'] if r['status'] == 'completed')
    total_ranges = len(llm_progress['ranges'])
    
    print(f"\n{'='*50}")
    print(f"{llm.model}")
    print(f"Progress: {completed}/{total_ranges} ranges completed")
    print(f"{'='*50}")
    
    # Process non-completed ranges
    for range_info in llm_progress['ranges']:
        if range_info['status'] == 'completed':
            continue
            
        start, end = range_info['start'], range_info['end']
        print(f"\nProcessing range {start}-{end-1}")
        print(f"Status: {range_info['status']}")
        
        success = False
        
        while not success and range_info['retries'] < max_retries:
            if range_info['retries'] > 0:
                print(f"Retry {range_info['retries']}/{max_retries}")
            
            # Check if it's a pending batch with existing batch_id
            existing_batch_id = range_info.get('batch_id') if range_info['status'] == 'pending' else None
            
            success, batch_id = submit_and_process_batch(
                llm, supported_files, input_directory, output_directory,
                start, end, session_id, state, existing_batch_id
            )
            
            if success:
                range_info['status'] = 'completed'
                range_info['batch_id'] = batch_id
                print(f"Range {start}-{end-1} completed")
            else:
                range_info['retries'] += 1
                range_info['status'] = 'failed'
                range_info['batch_id'] = batch_id
                
                if range_info['retries'] < max_retries:
                    print(f"Waiting 60s before retry...")
                    time.sleep(60)
                else:
                    print(f"Range {start}-{end-1} failed after {max_retries} retries")
        
        # Save progress after each range
        save_state(state)
    
    # Final count
    completed = sum(1 for r in llm_progress['ranges'] if r['status'] == 'completed')
    failed = sum(1 for r in llm_progress['ranges'] if r['status'] == 'failed')
    
    print(f"{model_key}: {completed}/{total_ranges} completed, {failed} failed")
    
    return failed == 0

def main():
    """Main execution function with state management and failure recovery."""
    # Configuration
    input_directory = "input"
    output_directory = "output"
    batch_size = 100
    state_file = "batch_state.json"
    
    # LLMs to use
    llms_config = [
        "gpt-4o-mini-2024-07-18",
        "gpt-4.1-2025-04-14",
        "claude-3-5-haiku-20241022",
        "claude-sonnet-4-20250514"
    ]
    
    print(f"BATCH PROCESSING STARTED")
    print(f"Input: {input_directory}")
    print(f"Output: {output_directory}")
    print(f"Batch size: {batch_size}")
    
    # Check input directory
    if not os.path.exists(input_directory):
        print(f"Input directory '{input_directory}' not found")
        return
    
    # Get supported files
    all_files = get_all_files(input_directory)
    supported_files = []
    
    for file_path in all_files:
        file_extension = os.path.splitext(file_path)[1].lower()
        prologue, epilogue = get_file_prompts(file_extension)
        
        if prologue is not None and epilogue is not None:
            supported_files.append(file_path)
    
    print(f"Found {len(supported_files)} supported files")
    
    if not supported_files:
        print("No supported files found")
        return
    
    # Load or create state
    state = load_state(state_file)
    
    # Check for resume
    if len(sys.argv) > 1 and sys.argv[1] == "resume":
        print(f"Resuming from session {state['current_session_id']}")
    else:
        # New session
        state['current_session_id'] += 1
        print(f"Starting new session {state['current_session_id']}")
    
    save_state(state, state_file)
    
    # Process each LLM sequentially
    all_success = True
    
    for model_name in llms_config:
        try:
            llm = create_llm_instance(model_name)
            success = process_llm_batches(
                llm, supported_files, input_directory, output_directory,
                batch_size, state
            )
            
            if not success:
                all_success = False
                
        except Exception as e:
            print(f"Error with {model_name}: {e}")
            log_error(f"Error with {model_name}: {e}")
            all_success = False
    
    # Final summary
    print(f"\n{'='*50}")
    print(f"PROCESSING COMPLETED")
    print(f"{'='*50}")
    
    for model_name in llms_config:
        if model_name in state['llm_progress']:
            ranges = state['llm_progress'][model_name]['ranges']
            completed = sum(1 for r in ranges if r['status'] == 'completed')
            failed = sum(1 for r in ranges if r['status'] == 'failed')
            total = len(ranges)
            status = "OK" if failed == 0 else "FAIL"
            print(f"{status} {model_name}: {completed}/{total} ranges, {failed} failed")
    
    if all_success:
        print(f"All processing completed successfully!")
    else:
        print(f"Some ranges failed. Run 'python {sys.argv[0]} resume' to retry")
    
    print(f"State saved to: {state_file}")
    print(f"Batch info: batch_info.json")

if __name__ == "__main__":
    main()