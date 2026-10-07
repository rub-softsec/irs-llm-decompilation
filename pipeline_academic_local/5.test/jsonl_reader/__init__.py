import json
import os

class JSONLDataset:
    def __init__(self, file_path):
        """
        Initialize the dataset from a .jsonl file
        
        Args:
            file_path (str): Path to the .jsonl file
        """
        self.data = []
        
        # Check if file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File {file_path} does not exist")
        
        # Load data from .jsonl file
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():  # Skip empty lines
                    item = json.loads(line)
                    
                    # Remove 'asm' field if it exists
                    if 'asm' in item:
                        del item['asm']
                        
                    self.data.append(item)
        
        print(f"Loaded {len(self.data)} examples from file {file_path}")
    
    def __iter__(self):
        """Allow iteration over the dataset"""
        return iter(self.data)
    
    def __len__(self):
        """Return the number of examples in the dataset"""
        return len(self.data)
    
    def __getitem__(self, idx):
        """Allow access to a specific example by index"""
        return self.data[idx]


def load_jsonl_dataset(file_path):
    """
    Function to load a dataset from a .jsonl file
    
    Args:
        file_path (str): Path to the .jsonl file
        
    Returns:
        JSONLDataset: An iterable object containing the data
    """
    return JSONLDataset(file_path)


# Example usage:
# dataset = load_jsonl_dataset("path/to/file.jsonl")
# for row in dataset:
#     print(row['fname'])