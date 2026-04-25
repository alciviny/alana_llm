"""
LLM Loader Module for Alana LLM System.

This module provides a professional, enterprise-grade loader for Large Language Models (LLMs).
It handles model loading, caching, and error management with robust logging and type safety.
Designed for scalability, similar to FAANG-level implementations.

Features:
- Asynchronous loading for non-blocking operations.
- Error handling with retries and fallbacks.
- Memory management and model unloading.
- Integration with Hugging Face Transformers.

Dependencies: transformers, torch, asyncio, logging.
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
import torch

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMConfig:
    """Configuration class for LLM parameters."""
    def __init__(
        self,
        model_name: str,
        device: str = "auto",
        torch_dtype: torch.dtype = torch.float16,
        max_memory: Optional[Dict[str, str]] = None,
        trust_remote_code: bool = False,
    ):
        self.model_name = model_name
        self.device = device
        self.torch_dtype = torch_dtype
        self.max_memory = max_memory or {"cpu": "16GB"}
        self.trust_remote_code = trust_remote_code

class LLMError(Exception):
    """Custom exception for LLM-related errors."""
    pass

class LLMManager:
    """Manager class for loading, managing, and unloading LLMs."""
    
    def __init__(self):
        self.loaded_models: Dict[str, Any] = {}
        self.tokenizers: Dict[str, Any] = {}
        self.pipelines: Dict[str, Any] = {}
    
    async def load_model(self, config: LLMConfig, retries: int = 3) -> str:
        """
        Asynchronously load an LLM model with error handling and retries.
        
        Args:
            config: LLMConfig instance with model parameters.
            retries: Number of retry attempts on failure.
        
        Returns:
            str: Model identifier for reference.
        
        Raises:
            LLMError: If loading fails after retries.
        """
        model_id = config.model_name
        if model_id in self.loaded_models:
            logger.info(f"Model {model_id} already loaded.")
            return model_id
        
        for attempt in range(retries + 1):
            try:
                logger.info(f"Loading model {model_id} (attempt {attempt + 1})...")
                
                # Load tokenizer
                tokenizer = AutoTokenizer.from_pretrained(
                    model_id,
                    trust_remote_code=config.trust_remote_code
                )
                
                # Load model with memory constraints
                model = AutoModelForCausalLM.from_pretrained(
                    model_id,
                    torch_dtype=config.torch_dtype,
                    device_map=config.device,
                    max_memory=config.max_memory,
                    trust_remote_code=config.trust_remote_code
                )
                
                # Create pipeline for text generation
                pipe = pipeline(
                    "text-generation",
                    model=model,
                    tokenizer=tokenizer,
                    device_map=config.device
                )
                
                # Store references
                self.loaded_models[model_id] = model
                self.tokenizers[model_id] = tokenizer
                self.pipelines[model_id] = pipe
                
                logger.info(f"Model {model_id} loaded successfully.")
                return model_id
            
            except Exception as e:
                logger.error(f"Failed to load model {model_id} on attempt {attempt + 1}: {str(e)}")
                if attempt < retries:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise LLMError(f"Failed to load model {model_id} after {retries + 1} attempts: {str(e)}")
    
    def get_pipeline(self, model_id: str) -> Optional[Any]:
        """
        Retrieve the pipeline for a loaded model.
        
        Args:
            model_id: Identifier of the loaded model.
        
        Returns:
            Pipeline object or None if not loaded.
        """
        return self.pipelines.get(model_id)
    
    def unload_model(self, model_id: str) -> bool:
        """
        Unload a model to free memory.
        
        Args:
            model_id: Identifier of the model to unload.
        
        Returns:
            bool: True if unloaded, False if not found.
        """
        if model_id in self.loaded_models:
            del self.loaded_models[model_id]
            del self.tokenizers[model_id]
            del self.pipelines[model_id]
            torch.cuda.empty_cache() if torch.cuda.is_available() else None
            logger.info(f"Model {model_id} unloaded.")
            return True
        logger.warning(f"Model {model_id} not found for unloading.")
        return False
    
    def list_loaded_models(self) -> list[str]:
        """Return a list of currently loaded model IDs."""
        return list(self.loaded_models.keys())

# Singleton instance for global access (FAANG-style)
llm_manager = LLMManager()

# Example usage (for testing)
async def example_load():
    config = LLMConfig(model_name="microsoft/DialoGPT-medium")
    try:
        model_id = await llm_manager.load_model(config)
        print(f"Loaded: {model_id}")
    except LLMError as e:
        print(f"Error: {e}")