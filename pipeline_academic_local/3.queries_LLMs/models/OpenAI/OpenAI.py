import requests
import os
import time
import json
import uuid
from time import sleep
from typing import List, Dict, Any, Optional
from utils.config import Config
from models.LLM import LLM

class OpenAI(LLM):
    """
    A class to interact with the OpenAI chat API.
    
    This class provides methods to send messages to a OpenAI model and maintain
    conversation history, as well as batch processing capabilities.
    
    Attributes:
        url (str): The endpoint URL for the OpenAI API
        batch_url (str): The endpoint URL for the OpenAI Batch API
        headers (dict): HTTP headers for API requests
        model (str): The name of the OpenAI model to use
        batch_queue (List[Dict[str, Any]]): Queue for batch processing requests
    """

    def __init__(self, model="gpt-4o-mini", url="https://api.openai.com/v1/chat/completions"):
        """
        Initialize a new OpenAI chat instance.
        
        Args:
            model (str, optional): The model name to use. Defaults to "gpt-4o-mini"
            url (str, optional): The API endpoint URL. Defaults to OpenAI's chat completions endpoint.
        """
        self.url = url
        self.batch_url = "https://api.openai.com/v1/batches"
        self.files_url = "https://api.openai.com/v1/files"
        
        config = Config()
        api_key = config.get_value("API_KEY_OPENAI")
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + api_key
        }
        self.model = model
        self.batch_queue = []
    
    def _is_reasoning_model(self) -> bool:
        """
        Check if the current model is a reasoning model (o1, o3 series).
        
        Returns:
            bool: True if the model is a reasoning model that doesn't support temperature
        """
        return any(model_prefix in self.model.lower() for model_prefix in ["o1", "o3"])
    
    def chat(self, prompt: str, conversation_history: dict = None) -> tuple:
        """
        Send a message to the OpenAI model and get a response.
        
        This method handles the conversation with the OpenAI model, maintaining the
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
        
        # Reasoning models (o1, o3 series) don't support temperature parameter
        if self._is_reasoning_model():
            data = {
                "model": self.model,
                "messages": messages,
                "stream": False
            }
        else:
            data = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.1,
                "stream": False
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
                response_content = response.json()['choices'][0]['message']['content']
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
        
        # Create the batch request body according to OpenAI Batch API format
        batch_request = {
            "custom_id": custom_id,
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": {
                "model": self.model,
                "messages": messages
            }
        }
        
        # Only add temperature for non-reasoning models
        if not self._is_reasoning_model():
            batch_request["body"]["temperature"] = 0.0
        
        # Add any additional kwargs to the body
        batch_request["body"].update(kwargs)
        
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
        Submit the queued messages to the OpenAI Batch API for processing.
        
        Args:
            batch_name (str, optional): Name/description for this batch job
            metadata (Dict[str, Any], optional): Additional metadata for the batch
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
        
        # Create JSONL content for the batch file
        jsonl_content = []
        for item in self.batch_queue:
            jsonl_content.append(json.dumps(item["request"]))
        
        jsonl_data = "\n".join(jsonl_content)
        
        # Retry loop for file upload
        file_id = None
        for upload_attempt in range(max_retries):
            try:
                print(f"Attempting file upload (attempt {upload_attempt + 1}/{max_retries})...")
                
                # Upload the batch file
                files = {
                    'file': ('batch_requests.jsonl', jsonl_data, 'application/json'),
                }
                
                file_headers = {
                    'Authorization': self.headers['Authorization']
                }
                
                upload_data = {
                    'purpose': 'batch'
                }
                
                # Log the file upload attempt
                log_name = f"batch_upload_{self.model}.log"
                log_path = os.path.join(target_dir, log_name)
                with open(log_path, "a") as f:
                    f.write(f"Upload attempt {upload_attempt + 1}/{max_retries}: {len(self.batch_queue)} requests\n")
                    f.write(f"Batch name: {batch_name}\n")
                    f.write(f"Metadata: {metadata}\n")
                    f.write("-"*15 + "\n")
                
                file_response = requests.post(self.files_url, headers=file_headers, 
                                            files=files, data=upload_data)
                
                if file_response.status_code == 200:
                    file_id = file_response.json()['id']
                    
                    # Log successful file upload
                    with open(log_path, "a") as f:
                        f.write(f"File uploaded successfully. File ID: {file_id}\n")
                        f.write(str(file_response.json()) + "\n")
                        f.write("-"*15 + "\n")
                    
                    print(f"File uploaded successfully: {file_id}")
                    break
                else:
                    error_msg = f"Failed to upload batch file: {file_response.status_code} - {file_response.text}"
                    print(f"Upload attempt {upload_attempt + 1} failed: {error_msg}")
                    
                    with open(log_path, "a") as f:
                        f.write(f"ERROR attempt {upload_attempt + 1}: {error_msg}\n")
                        f.write("-"*15 + "\n")
                    
                    if upload_attempt < max_retries - 1:
                        print(f"Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                    else:
                        raise Exception(f"All upload attempts failed. Last error: {error_msg}")
                        
            except requests.exceptions.RequestException as e:
                error_msg = f"Network error during file upload: {str(e)}"
                print(f"Upload attempt {upload_attempt + 1} failed: {error_msg}")
                
                with open(log_path, "a") as f:
                    f.write(f"NETWORK ERROR attempt {upload_attempt + 1}: {error_msg}\n")
                    f.write("-"*15 + "\n")
                
                if upload_attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    raise Exception(f"All upload attempts failed due to network errors. Last error: {error_msg}")
            
            except Exception as e:
                error_msg = f"Unexpected error during file upload: {str(e)}"
                print(f"Upload attempt {upload_attempt + 1} failed: {error_msg}")
                
                with open(log_path, "a") as f:
                    f.write(f"UNEXPECTED ERROR attempt {upload_attempt + 1}: {error_msg}\n")
                    f.write("-"*15 + "\n")
                
                if upload_attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    raise Exception(f"All upload attempts failed. Last error: {error_msg}")
        
        # Retry loop for batch creation
        batch_id = None
        for batch_attempt in range(max_retries):
            try:
                print(f"Attempting batch creation (attempt {batch_attempt + 1}/{max_retries})...")
                
                # Create the batch job
                batch_data = {
                    "input_file_id": file_id,
                    "endpoint": "/v1/chat/completions",
                    "completion_window": "24h"
                }
                
                if batch_name:
                    batch_data["metadata"] = {"description": batch_name}
                
                if metadata:
                    if "metadata" not in batch_data:
                        batch_data["metadata"] = {}
                    batch_data["metadata"].update(metadata)
                
                batch_response = requests.post(self.batch_url, headers=self.headers, json=batch_data)
                
                # Log batch creation response
                log_name_batch = f"batch_creation_{self.model}.log"
                log_path_batch = os.path.join(target_dir, log_name_batch)
                with open(log_path_batch, "a") as f:
                    f.write(f"Batch creation attempt {batch_attempt + 1}/{max_retries}\n")
                    f.write(str(batch_response.json()) + "\n")
                    f.write("-"*15 + "\n")
                
                if batch_response.status_code == 200:
                    batch_id = batch_response.json()['id']
                    print(f"Batch created successfully: {batch_id}")
                    break
                else:
                    error_msg = f"Failed to create batch job: {batch_response.status_code} - {batch_response.text}"
                    print(f"Batch creation attempt {batch_attempt + 1} failed: {error_msg}")
                    
                    with open(log_path_batch, "a") as f:
                        f.write(f"ERROR attempt {batch_attempt + 1}: {error_msg}\n")
                        f.write("-"*15 + "\n")
                    
                    if batch_attempt < max_retries - 1:
                        print(f"Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                    else:
                        raise Exception(f"All batch creation attempts failed. Last error: {error_msg}")
                        
            except requests.exceptions.RequestException as e:
                error_msg = f"Network error during batch creation: {str(e)}"
                print(f"Batch creation attempt {batch_attempt + 1} failed: {error_msg}")
                
                with open(log_path_batch, "a") as f:
                    f.write(f"NETWORK ERROR attempt {batch_attempt + 1}: {error_msg}\n")
                    f.write("-"*15 + "\n")
                
                if batch_attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    raise Exception(f"All batch creation attempts failed due to network errors. Last error: {error_msg}")
            
            except Exception as e:
                error_msg = f"Unexpected error during batch creation: {str(e)}"
                print(f"Batch creation attempt {batch_attempt + 1} failed: {error_msg}")
                
                with open(log_path_batch, "a") as f:
                    f.write(f"UNEXPECTED ERROR attempt {batch_attempt + 1}: {error_msg}\n")
                    f.write("-"*15 + "\n")
                
                if batch_attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    raise Exception(f"All batch creation attempts failed. Last error: {error_msg}")
        
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
        
        # Convert OpenAI format to standard format
        return self._standardize_batch_status(batch_info)
    
    def _standardize_batch_status(self, openai_response: dict) -> dict:
        """Convert OpenAI batch status to standard format"""
        request_counts = openai_response.get("request_counts", {})
        
        # Map OpenAI statuses to standard statuses
        status_map = {
            "validating": "in_progress",
            "in_progress": "in_progress", 
            "finalizing": "in_progress",
            "completed": "completed",
            "expired": "completed",
            "failed": "failed",
            "cancelling": "cancelled",
            "cancelled": "cancelled"
        }
        
        openai_status = openai_response.get("status", "unknown")
        standard_status = status_map.get(openai_status, "unknown")
        
        return {
            "status": standard_status,
            "progress": {
                "total": request_counts.get("total", 0),
                "completed": request_counts.get("completed", 0),
                "failed": request_counts.get("failed", 0),
                "processing": request_counts.get("total", 0) - request_counts.get("completed", 0) - request_counts.get("failed", 0)
            },
            "created_at": openai_response.get("created_at"),
            "completed_at": openai_response.get("completed_at"),
            "provider_raw": openai_response
        }
    
    def download_batch_results(self, batch_id: str, save_to_file: bool = False, file_path: str = None) -> List[Dict[str, Any]]:
        """
        Download batch results and return in standard format.
        """
        # Check if batch is completed
        status_info = self.check_batch_status(batch_id)
        
        if status_info["status"] != "completed":
            raise ValueError(f"Batch {batch_id} is not completed. Current status: {status_info['status']}")
        
        # Get batch info and download results
        batch_response = requests.get(f"{self.batch_url}/{batch_id}", headers=self.headers)
        if batch_response.status_code != 200:
            raise Exception(f"Failed to get batch info: {batch_response.text}")
        
        batch_info = batch_response.json()
        output_file_id = batch_info.get("output_file_id")
        
        if not output_file_id:
            raise ValueError("No output file found for this batch")
        
        file_response = requests.get(f"{self.files_url}/{output_file_id}/content", headers=self.headers)
        if file_response.status_code != 200:
            raise Exception(f"Failed to download results file: {file_response.text}")
        
        # Setup logging
        script_dir = os.path.dirname(os.path.abspath(__file__))
        target_dir = os.path.join(script_dir, "logger")
        os.makedirs(target_dir, exist_ok=True)
        
        # Parse results and standardize
        results = []
        for line in file_response.text.strip().split('\n'):
            if line.strip():
                openai_result = json.loads(line)
                
                # Log raw result
                log_name = f"batch_responses_{self.model}.log"
                log_path = os.path.join(target_dir, log_name)
                with open(log_path, "a") as f:
                    f.write(str(openai_result))
                    f.write("\n"+("-"*15)+"\n")
                
                # Standardize result
                standard_result = self._standardize_batch_result(openai_result)
                results.append(standard_result)
        
        # Save if requested
        if save_to_file:
            self._save_results_to_file(results, batch_id, file_path)
        
        return results
    
    def _standardize_batch_result(self, openai_result: dict) -> dict:
        """Convert OpenAI batch result to standard format"""
        result = {
            "custom_id": openai_result.get("custom_id"),
            "response": None,
            "usage": {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0
            },
            "error": openai_result.get("error"),
            "provider_raw": openai_result
        }
        
        # Extract response and usage if successful
        if openai_result.get("response") and openai_result["response"].get("body"):
            body = openai_result["response"]["body"]
            
            # Extract response text
            if body.get("choices") and len(body["choices"]) > 0:
                result["response"] = body["choices"][0]["message"]["content"]
            
            # Extract usage info
            if body.get("usage"):
                usage = body["usage"]
                result["usage"] = {
                    "input_tokens": usage.get("prompt_tokens", 0),
                    "output_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0)
                }
        
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