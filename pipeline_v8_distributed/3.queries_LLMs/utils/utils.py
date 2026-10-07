"""
Utility functions for file processing and directory management.
"""

import os

def read_file_content(file_path):
    """
    Read the content of a file.
    
    Args:
        file_path (str): Path to the file
        
    Returns:
        str: File content or None if error
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return None

def write_file_content(file_path, content):
    """
    Write content to a file, creating directories if needed.
    
    Args:
        file_path (str): Path to the file
        content (str): Content to write
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(content)
        print(f"Saved response to: {file_path}")
    except Exception as e:
        print(f"Error writing file {file_path}: {e}")

def get_all_files(directory):
    """
    Get all files recursively from a directory.
    
    Args:
        directory (str): Directory path
        
    Returns:
        list: List of file paths
    """
    file_paths = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_paths.append(os.path.join(root, file))
    return file_paths

def get_output_path(input_path, input_dir, output_dir, llm_model_name):
    """
    Generate output path maintaining directory structure.
    
    Args:
        input_path (str): Original file path
        input_dir (str): Input directory
        output_dir (str): Output directory
        llm_model_name (str): LLM model name for filename suffix
        
    Returns:
        str: Output file path
    """
    # Get relative path from input directory
    relative_path = os.path.relpath(input_path, input_dir)
    
    # Get file parts
    file_dir = os.path.dirname(relative_path)
    file_name = os.path.basename(relative_path)
    file_base, file_ext = os.path.splitext(file_name)
    
    # Create new filename with LLM model suffix
    new_filename = f"{file_base}_{llm_model_name}_response{file_ext}"
    
    # Combine with output directory
    if file_dir:
        output_path = os.path.join(output_dir, file_dir, new_filename)
    else:
        output_path = os.path.join(output_dir, new_filename)
    
    return output_path