import os
from typing import Dict
from pathlib import Path

class Config:
    """
    A class to read and parse configuration settings from a file.
    
    This class is designed to load configurations from a `.secret` file and store them 
    in a dictionary for easy access throughout the application.
    
    Attributes:
        file_path (Path): Path to the `.secret` file
        config (Dict[str, str]): Dictionary containing the configuration keys and values
    """

    def __init__(self, file_path: str = ".secret"):
        """
        Initialize the Config instance.
        
        Args:
            file_path (str): Path to the `.secret` file (default is ".secret").
        """
        self.file_path = Path(file_path)
        self.config: Dict[str, str] = {}
        self.load_config()

    def load_config(self):
        """
        Load configurations from the `.secret` file into the `config` dictionary.
        
        This method checks if the `.secret` file exists, reads its content, 
        and parses it into key-value pairs. Each line in the file should 
        follow the format: `KEY=VALUE`.
        """
        if not self.file_path.exists():
            raise FileNotFoundError(f"The configuration file '{self.file_path}' does not exist.")

        with self.file_path.open("r", encoding="utf-8") as file:
            for line in file:
                # Ignore empty lines or lines starting with a comment
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                
                # Split the line into a key-value pair
                if "=" not in line:
                    raise ValueError(f"Invalid line format in configuration file: {line}")
                
                key, value = line.split("=", 1)
                # Remove any surrounding quotes from the value
                value = value.strip().strip('"').strip("'")
                self.config[key.strip()] = value.strip()

    def get_value(self, key: str) -> str:
        """
        Retrieve the value of a configuration key.
        
        Args:
            key (str): The name of the configuration key to retrieve.
        
        Returns:
            str: The value associated with the configuration key.
        
        Raises:
            KeyError: If the key is not found in the configurations.
        """
        return self.config.get(key, None)
