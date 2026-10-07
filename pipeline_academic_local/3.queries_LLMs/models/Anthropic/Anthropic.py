import requests
import os
import time
import json
import uuid
from time import sleep
from typing import List, Dict, Any, Optional
from utils.config import Config
from models.LLM import LLM

class Anthropic(LLM):
    """
    A class to interact with the Anthropic chat API.
    
    This class provides methods to send messages to a Anthropic model and maintain
    conversation history, as well as batch processing capabilities.
    
    Attributes:
        url (str): The endpoint URL for the Anthropic API
        batch_url (str): The endpoint URL for the Anthropic Batch API
        headers (dict): HTTP headers for API requests
        model (str): The name of the Anthropic model to use
        batch_queue (List[Dict[str, Any]]): Queue for batch processing requests
    """

    def __init__(self, model="claude-3-haiku-20240307", url="https://api.anthropic.com/v1/messages"):
        """
        Initialize a new Anthropic chat instance.
        
        Args:
            model (str, optional): The model name to use. Defaults to "claude-3-haiku-20240307"
            url (str, optional): The API endpoint URL. Defaults to Anthropic's messages endpoint.
        """
        self.url = url
        self.batch_url = "https://api.anthropic.com/v1/messages/batches"
        
        config = Config()
        api_key = config.get_value("API_KEY_ANTHROPIC")
        self.headers = {
            'Content-Type': 'application/json',
            'anthropic-version': '2023-06-01',
            'x-api-key': api_key
        }
        self.model = model
        self.batch_queue = []
    
    def chat(self, prompt: str, conversation_history: dict = None) -> tuple:
        """
        Send a message to the Anthropic model and get a response.
        
        This method handles the conversation with the Anthropic model, maintaining the
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
        # If no conversation history is provided, initialize an empty dictionary with messages list
        if conversation_history is None:
            conversation_history = {"messages": []}
        
        # Create a copy of the existing messages and add the new prompt
        messages = conversation_history["messages"].copy()
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        # Prepare the request data
        data = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 4096,
        }

        ok = False
        while not ok:
            # Send request to the API and get response
            first = time.time()
            response = requests.post(self.url, headers=self.headers, json=data)
            second = time.time()
            duration = second - first

            script_dir = os.path.dirname(os.path.abspath(__file__))
            target_dir = os.path.join(script_dir, "logger")
            os.makedirs(target_dir, exist_ok=True)

            try:
                # Log
                log_name = "responses_"+self.model+".log"
                log_path = os.path.join(target_dir, log_name)
                with open(log_path, "a") as f:
                    f.write(str(response.json()))
                    f.write("\n"+("-"*15)+"\n")
                # Get answer to the prompt
                response_content = response.json()['content'][0]['text']
                # Log time
                log_name_time = "responses_time_"+self.model+".log"
                log_path_time = os.path.join(target_dir, log_name_time)
                with open(log_path_time, "a") as f:
                    f.write(f"{duration:.6f}\n")
                ok = True
            except Exception as e:
                print(e)
                print("Trying again in 15 seconds to send the request...")
                sleep(15)

        # Add the assistant's response to the messages
        messages.append({
            "role": "assistant",
            "content": response_content
        })
        
        # Create updated conversation history
        updated_conversation = {
            "messages": messages
        }
        
        # Return both the response and the updated conversation history
        return response_content, updated_conversation
    
    def craftConversationHistory(self, user_message: str, assistant_message: str) -> dict:
        """
        Formats user and assistant messages into a structured dictionary.
        
        Args:
            user_message (str): The message sent by the user
            assistant_message (str): The response from the assistant
            
        Returns:
            dict: A dictionary containing messages array and metadata
                {
                    "messages": [
                        {"role": "user", "content": "user message"},
                        {"role": "assistant", "content": "assistant response"}
                    ]
                }
        """
        conversation = {
            "messages": [
                {
                    "role": "user",
                    "content": user_message
                },
                {
                    "role": "assistant",
                    "content": assistant_message
                }
            ]
        }
        
        return conversation
    
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
        if custom_id is None:
            custom_id = str(uuid.uuid4())
        
        # Prepare messages for the batch request
        if conversation_history is None:
            messages = [{"role": "user", "content": prompt}]
        else:
            messages = conversation_history.get("messages", []).copy()
            messages.append({"role": "user", "content": prompt})
        
        # Create the batch request body according to Anthropic Batch API format
        batch_request = {
            "custom_id": custom_id,
            "params": {
                "model": self.model,
                "messages": messages,
                "temperature": 0.0,
                "max_tokens": kwargs.get("max_tokens", 4096)
            }
        }
        
        # Add any additional kwargs to the params
        for key, value in kwargs.items():
            if key != "max_tokens":  # Already handled above
                batch_request["params"][key] = value
        
        # Store additional metadata
        queue_item = {
            "request": batch_request,
            "prompt": prompt,
            "conversation_history": conversation_history,
            "metadata": kwargs
        }
        
        self.batch_queue.append(queue_item)
        return custom_id
    
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
        return [
            {
                "custom_id": item["request"]["custom_id"],
                "prompt": item["prompt"],
                "conversation_history": item["conversation_history"],
                "metadata": item["metadata"]
            }
            for item in self.batch_queue
        ]
    
    def submit_batch_request(self, batch_name: str = None, 
                           metadata: Dict[str, Any] = None,
                           max_retries: int = 3,
                           retry_delay: int = 15) -> str:
        """
        Submit the queued messages to the Anthropic Batch API for processing.
        
        Args:
            batch_name (str, optional): Name/description for this batch job (ignored by Anthropic)
            metadata (Dict[str, Any], optional): Additional metadata for the batch (ignored by Anthropic)
            max_retries (int): Maximum number of retry attempts
            retry_delay (int): Seconds to wait between retry attempts
            
        Returns:
            str: Batch job ID returned by the API for tracking purposes
            
        Raises:
            ValueError: If no requests in batch queue
            Exception: If all retry attempts fail
        """
        if not self.batch_queue:
            raise ValueError("No requests in batch queue to submit")
        
        # Setup logging directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        target_dir = os.path.join(script_dir, "logger")
        os.makedirs(target_dir, exist_ok=True)
        
        # Create batch data according to Anthropic's format (no metadata support)
        batch_data = {
            "requests": [item["request"] for item in self.batch_queue]
        }
        
        # Retry loop for batch submission
        batch_id = None
        for attempt in range(max_retries):
            try:
                print(f"Attempting batch submission (attempt {attempt + 1}/{max_retries})...")
                
                # Log the batch submission attempt
                log_name = f"batch_upload_{self.model}.log"
                log_path = os.path.join(target_dir, log_name)
                with open(log_path, "a") as f:
                    f.write(f"Batch submission attempt {attempt + 1}/{max_retries}: {len(self.batch_queue)} requests\n")
                    f.write(f"Batch name: {batch_name} (ignored by Anthropic)\n")
                    f.write(f"Metadata: {metadata} (ignored by Anthropic)\n")
                    f.write("-"*15 + "\n")
                
                batch_response = requests.post(self.batch_url, headers=self.headers, json=batch_data)
                
                # Log batch creation response
                log_name_batch = f"batch_creation_{self.model}.log"
                log_path_batch = os.path.join(target_dir, log_name_batch)
                with open(log_path_batch, "a") as f:
                    f.write(f"Batch creation attempt {attempt + 1}/{max_retries}\n")
                    f.write(str(batch_response.json()) + "\n")
                    f.write("-"*15 + "\n")
                
                if batch_response.status_code == 200:
                    batch_id = batch_response.json()['id']
                    print(f"Batch submitted successfully: {batch_id}")
                    
                    # Log successful submission
                    with open(log_path, "a") as f:
                        f.write(f"Batch submitted successfully. Batch ID: {batch_id}\n")
                        f.write(str(batch_response.json()) + "\n")
                        f.write("-"*15 + "\n")
                    
                    break
                else:
                    error_msg = f"Failed to submit batch: {batch_response.status_code} - {batch_response.text}"
                    print(f"Batch submission attempt {attempt + 1} failed: {error_msg}")
                    
                    with open(log_path, "a") as f:
                        f.write(f"ERROR attempt {attempt + 1}: {error_msg}\n")
                        f.write("-"*15 + "\n")
                    
                    if attempt < max_retries - 1:
                        print(f"Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                    else:
                        raise Exception(f"All batch submission attempts failed. Last error: {error_msg}")
                        
            except requests.exceptions.RequestException as e:
                error_msg = f"Network error during batch submission: {str(e)}"
                print(f"Batch submission attempt {attempt + 1} failed: {error_msg}")
                
                with open(log_path, "a") as f:
                    f.write(f"NETWORK ERROR attempt {attempt + 1}: {error_msg}\n")
                    f.write("-"*15 + "\n")
                
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    raise Exception(f"All batch submission attempts failed due to network errors. Last error: {error_msg}")
            
            except Exception as e:
                error_msg = f"Unexpected error during batch submission: {str(e)}"
                print(f"Batch submission attempt {attempt + 1} failed: {error_msg}")
                
                with open(log_path, "a") as f:
                    f.write(f"UNEXPECTED ERROR attempt {attempt + 1}: {error_msg}\n")
                    f.write("-"*15 + "\n")
                
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    raise Exception(f"All batch submission attempts failed. Last error: {error_msg}")
        
        # Clear the queue after successful submission
        self.clear_batch_queue()
        
        return batch_id
    
    def check_batch_status(self, batch_id: str) -> Dict[str, Any]:
        """
        Check the processing status of a submitted batch job.
        Returns standardized status format.
        """
        response = requests.get(f"{self.batch_url}/{batch_id}", headers=self.headers)
        
        if response.status_code != 200:
            raise Exception(f"Failed to get batch status: {response.text}")
        
        batch_info = response.json()
        
        # Convert Anthropic format to standard format
        return self._standardize_batch_status(batch_info)
    
    def _standardize_batch_status(self, anthropic_response: dict) -> dict:
        """Convert Anthropic batch status to standard format"""
        request_counts = anthropic_response.get("request_counts", {})
        
        # Map Anthropic statuses to standard statuses
        status_map = {
            "in_progress": "in_progress",
            "ended": "completed",
            "failed": "failed",
            "canceled": "cancelled",
            "expired": "failed"
        }
        
        anthropic_status = anthropic_response.get("processing_status", "unknown")
        standard_status = status_map.get(anthropic_status, "unknown")
        
        return {
            "status": standard_status,
            "progress": {
                "total": sum(request_counts.values()) if request_counts else 0,
                "completed": request_counts.get("succeeded", 0),
                "failed": request_counts.get("errored", 0),
                "processing": request_counts.get("processing", 0)
            },
            "created_at": anthropic_response.get("created_at"),
            "completed_at": anthropic_response.get("ended_at"),
            "provider_raw": anthropic_response
        }
    
    def download_batch_results(self, batch_id: str, save_to_file: bool = False, file_path: str = None) -> List[Dict[str, Any]]:
        """
        Download batch results and return in standard format.
        """
        # Check if batch is completed
        status_info = self.check_batch_status(batch_id)
        
        if status_info["status"] != "completed":
            raise ValueError(f"Batch {batch_id} is not completed. Current status: {status_info['status']}")
        
        # Get results URL and download
        results_url = status_info["provider_raw"].get("results_url")
        if not results_url:
            results_url = f"{self.batch_url}/{batch_id}/results"
        
        results_response = requests.get(results_url, headers=self.headers)
        if results_response.status_code != 200:
            raise Exception(f"Failed to download results: {results_response.text}")
        
        # Setup logging
        script_dir = os.path.dirname(os.path.abspath(__file__))
        target_dir = os.path.join(script_dir, "logger")
        os.makedirs(target_dir, exist_ok=True)
        
        # Parse results and standardize
        results = []
        for line in results_response.text.strip().split('\n'):
            if line.strip():
                anthropic_result = json.loads(line)
                
                # Log raw result
                log_name = f"batch_responses_{self.model}.log"
                log_path = os.path.join(target_dir, log_name)
                with open(log_path, "a") as f:
                    f.write(str(anthropic_result))
                    f.write("\n"+("-"*15)+"\n")
                
                # Standardize result
                standard_result = self._standardize_batch_result(anthropic_result)
                results.append(standard_result)
        
        # Save if requested
        if save_to_file:
            self._save_results_to_file(results, batch_id, file_path)
        
        return results
    
    def _standardize_batch_result(self, anthropic_result: dict) -> dict:
        """Convert Anthropic batch result to standard format"""
        result = {
            "custom_id": anthropic_result.get("custom_id"),
            "response": None,
            "usage": {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0
            },
            "error": None,
            "provider_raw": anthropic_result
        }
        
        # Handle successful results - Anthropic uses "succeeded" type
        if anthropic_result.get("result") and anthropic_result["result"].get("type") == "succeeded":
            message = anthropic_result["result"]["message"]
            
            # Extract response text
            if message.get("content") and len(message["content"]) > 0:
                result["response"] = message["content"][0]["text"]
            
            # Extract usage info
            if message.get("usage"):
                usage = message["usage"]
                result["usage"] = {
                    "input_tokens": usage.get("input_tokens", 0),
                    "output_tokens": usage.get("output_tokens", 0),
                    "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
                }
        
        # Handle failed results - Anthropic uses "failed" type
        elif anthropic_result.get("result") and anthropic_result["result"].get("type") == "failed":
            result["error"] = str(anthropic_result["result"].get("error", "Unknown error"))
        
        # Handle error results - Anthropic uses "error" type
        elif anthropic_result.get("result") and anthropic_result["result"].get("type") == "error":
            result["error"] = str(anthropic_result["result"]["error"])
        
        return result
    
    def _save_results_to_file(self, results: List[dict], batch_id: str, file_path: str = None):
        """Save standardized results to file"""
        if file_path is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            target_dir = os.path.join(script_dir, "batch_results")
            os.makedirs(target_dir, exist_ok=True)
            file_path = os.path.join(target_dir, f"batch_results_{batch_id}.json")
        
        try:
            with open(file_path, 'w') as f:
                json.dump(results, f, indent=2)
        except Exception as e:
            raise IOError(f"Failed to save results to file: {str(e)}")
    
    def clear_batch_queue(self) -> None:
        """
        Clear all queued batch requests.
        """
        self.batch_queue.clear()
    
    def get_batch_queue_size(self) -> int:
        """
        Get the number of requests currently in the batch queue.
        """
        return len(self.batch_queue)
    
    def remove_from_batch_queue(self, custom_id: str) -> bool:
        """
        Remove a specific request from the batch queue by custom_id.
        
        Args:
            custom_id (str): The custom ID of the request to remove
            
        Returns:
            bool: True if removed successfully, False if not found
        """
        for i, item in enumerate(self.batch_queue):
            if item["request"]["custom_id"] == custom_id:
                self.batch_queue.pop(i)
                return True
        return False