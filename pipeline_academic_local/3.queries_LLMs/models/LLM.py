from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple

class LLM(ABC):
    
    @abstractmethod
    def chat(self, prompt: str, conversation_history: dict = None) -> tuple:
        """
        Send a message to the LLM model and get a response.
        
        This method handles the conversation with the LLM model, maintaining the
        conversation history and formatting messages appropriately.
        
        Args:
            prompt (str): The user's message to send to the model
            conversation_history (dict, optional): Previous conversation containing
                a "messages" key with the message list. Defaults to None.
        
        Returns:
            tuple: A tuple containing (response_content, updated_messages), where:
                - response_content (str): The model's response text
                - updated_messages (dict): The full conversation history including
                  the new messages
        """
        raise NotImplementedError("This method must be implemented by concrete classes")
    
    @abstractmethod
    def craftConversationHistory(self, user_message: str, assistant_message: str) -> dict:
        """
        Formats user and assistant messages into a structured dictionary.
        
        Args:
            user_message (str): The message sent by the user
            assistant_message (str): The response from the assistant
            
        Returns:
            dict: A dictionary containing messages array and metadata
        """
        raise NotImplementedError("This method must be implemented by concrete classes")
    
    @abstractmethod
    def add_to_batch_queue(self, prompt: str, custom_id: str = None, 
                          conversation_history: dict = None, **kwargs) -> str:
        """
        Add a prompt to the batch processing queue.
        
        Args:
            prompt (str): The user's message to add to the batch
            custom_id (str, optional): Custom identifier for this request. 
                If None, a unique ID will be generated.
            conversation_history (dict, optional): Previous conversation history
            **kwargs: Additional parameters specific to the LLM provider
            
        Returns:
            str: The custom_id assigned to this batch request
        """
        raise NotImplementedError("This method must be implemented by concrete classes")
    
    @abstractmethod
    def get_batch_queue(self) -> List[Dict[str, Any]]:
        """
        Retrieve the current list of messages queued for batch processing.
        
        Returns:
            List[Dict[str, Any]]: List of batch requests with their details including:
                - custom_id: Unique identifier for the request
                - prompt: The message to be processed
                - conversation_history: Any associated conversation history
                - metadata: Additional request parameters
        """
        raise NotImplementedError("This method must be implemented by concrete classes")
    
    @abstractmethod
    def submit_batch_request(self, batch_name: str = None, 
                           metadata: Dict[str, Any] = None) -> str:
        """
        Submit the queued messages to the LLM's batch API for processing.
        
        Args:
            batch_name (str, optional): Name/description for this batch job
            metadata (Dict[str, Any], optional): Additional metadata for the batch
            
        Returns:
            str: Batch job ID returned by the API for tracking purposes
        """
        raise NotImplementedError("This method must be implemented by concrete classes")
    
    @abstractmethod
    def check_batch_status(self, batch_id: str) -> Dict[str, Any]:
        """
        Check the processing status of a submitted batch job.
        Returns standardized status format.
        
        Args:
            batch_id (str): The batch job ID returned from submit_batch_request
            
        Returns:
            Dict[str, Any]: Standardized status information including:
                - status: Current status ('in_progress', 'completed', 'failed', 'cancelled')
                - progress: Dict with total, completed, failed, processing counts
                - created_at: When the batch was created
                - completed_at: When the batch was completed (if finished)
                - provider_raw: Original provider response for debugging
        """
        raise NotImplementedError("This method must be implemented by concrete classes")
    
    @abstractmethod
    def download_batch_results(self, batch_id: str, 
                             save_to_file: bool = False, 
                             file_path: str = None) -> List[Dict[str, Any]]:
        """
        Download and retrieve the results from a completed batch job.
        Returns standardized result format.
        
        Args:
            batch_id (str): The batch job ID to download results for
            save_to_file (bool): Whether to save results to a file
            file_path (str, optional): Path to save the results file. 
                If None and save_to_file is True, a default path will be used.
                
        Returns:
            List[Dict[str, Any]]: List of standardized batch results containing:
                - custom_id: The original custom ID for the request
                - response: The LLM's response to the prompt
                - usage: Dict with input_tokens, output_tokens, total_tokens
                - error: Any error that occurred for this specific request
                - provider_raw: Original provider response for debugging
                
        Raises:
            ValueError: If batch is not completed or batch_id is invalid
            IOError: If there are issues saving to file when save_to_file is True
        """
        raise NotImplementedError("This method must be implemented by concrete classes")
    
    # Helper methods that can be implemented in concrete classes
    def clear_batch_queue(self) -> None:
        """
        Clear all queued batch requests. Should be implemented by concrete classes.
        """
        raise NotImplementedError("This method should be implemented by concrete classes")
    
    def get_batch_queue_size(self) -> int:
        """
        Get the number of requests currently in the batch queue.
        Should be implemented by concrete classes.
        """
        raise NotImplementedError("This method should be implemented by concrete classes")
    
    def remove_from_batch_queue(self, custom_id: str) -> bool:
        """
        Remove a specific request from the batch queue by custom_id.
        Should be implemented by concrete classes.
        
        Args:
            custom_id (str): The custom ID of the request to remove
            
        Returns:
            bool: True if removed successfully, False if not found
        """
        raise NotImplementedError("This method should be implemented by concrete classes")