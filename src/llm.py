from abc import ABC, abstractmethod
import os
import requests
from typing import Dict, Any, Optional, List
import logging

from src.config import Config

logger = logging.getLogger(__name__)


class BaseLLMProvider(ABC):
    """Abstract base class interface for AI/LLM providers in RAXEL."""

    @abstractmethod
    def check_connection(self) -> Dict[str, Any]:
        """Check provider connectivity and status."""
        pass

    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate text response from LLM model."""
        pass

    @abstractmethod
    def get_available_models(self) -> List[str]:
        """Return list of available model names for provider."""
        pass


class OllamaLLM(BaseLLMProvider):
    """Client for local Ollama LLM inference."""

    def __init__(self, model_name: str = "llama3:latest", base_url: str = "http://localhost:11434"):
        self.provider_id = "ollama"
        self.provider_name = "Local Ollama"
        self.model_name = model_name
        self.base_url = base_url.rstrip("/")

    def get_available_models(self) -> List[str]:
        conn = self.check_connection()
        return conn.get("installed_models", Config.AVAILABLE_OLLAMA_MODELS)

    def check_connection(self) -> Dict[str, Any]:
        """
        Check if Ollama service is reachable and if configured model is available.
        
        Returns:
            {"available": bool, "message": str, "installed_models": list}
        """
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("name") for m in data.get("models", [])]
                
                # Check if exact model or model prefix exists (e.g. 'llama3:latest' or 'llama3')
                has_model = any(
                    self.model_name == m or self.model_name.split(":")[0] == m.split(":")[0] 
                    for m in models
                )
                
                if not has_model:
                    return {
                        "available": False,
                        "message": f"Ollama is running, but model '{self.model_name}' was not found. Installed models: {models}",
                        "installed_models": models
                    }

                return {
                    "available": True,
                    "message": f"Connected to Ollama. Model '{self.model_name}' ready.",
                    "installed_models": models
                }
            else:
                return {
                    "available": False,
                    "message": f"Ollama returned HTTP status {resp.status_code}.",
                    "installed_models": []
                }
        except requests.exceptions.RequestException as e:
            return {
                "available": False,
                "message": f"Could not connect to Ollama at '{self.base_url}'. Make sure 'ollama serve' is running.",
                "installed_models": []
            }

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Generate text response from Ollama model.
        """
        conn_status = self.check_connection()
        if not conn_status["available"]:
            return (
                f"⚠️ **Local LLM Error**: {conn_status['message']}\n\n"
                f"Please ensure Ollama is running (`ollama serve`) and the model is pulled (`ollama pull {self.model_name}`)."
            )

        endpoint = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,  # Low temperature for deterministic, factual grounded answers
                "top_p": 0.9
            }
        }

        if system_prompt:
            payload["system"] = system_prompt

        try:
            logger.info(f"Sending prompt to Ollama model '{self.model_name}'...")
            resp = requests.post(endpoint, json=payload, timeout=60)
            if resp.status_code == 200:
                result = resp.json()
                return result.get("response", "").strip()
            else:
                logger.error(f"Ollama generation failed: {resp.status_code} - {resp.text}")
                return f"⚠️ LLM API Error ({resp.status_code}): Could not generate response."
        except Exception as e:
            logger.error(f"Ollama request error: {str(e)}")
            return f"⚠️ Connection Error while communicating with Ollama: {str(e)}"


# Alias for clean architecture alignment
OllamaProvider = OllamaLLM


class GeminiProvider(BaseLLMProvider):
    """Client for Google Gemini API inference via REST API."""

    def __init__(self, model_name: Optional[str] = None, api_key: Optional[str] = None):
        self.provider_id = "gemini"
        self.provider_name = "Gemini API"
        self._model_name = model_name
        self._api_key = api_key

    @property
    def model_name(self) -> str:
        return self._model_name or Config.GEMINI_MODEL

    @property
    def api_key(self) -> str:
        return self._api_key or Config.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")

    def get_available_models(self) -> List[str]:
        return Config.AVAILABLE_GEMINI_MODELS

    def check_connection(self) -> Dict[str, Any]:
        """
        Check if Gemini API Key is configured and API is reachable.
        """
        if not self.api_key:
            return {
                "available": False,
                "message": "Gemini API Key missing. Please configure GEMINI_API_KEY in .env file.",
                "installed_models": Config.AVAILABLE_GEMINI_MODELS
            }

        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={self.api_key}"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                return {
                    "available": True,
                    "message": f"Connected to Gemini API. Model '{self.model_name}' ready.",
                    "installed_models": Config.AVAILABLE_GEMINI_MODELS
                }
            elif resp.status_code in (401, 403):
                return {
                    "available": False,
                    "message": f"Gemini API Authentication Failed ({resp.status_code}): Invalid or missing GEMINI_API_KEY.",
                    "installed_models": Config.AVAILABLE_GEMINI_MODELS
                }
            else:
                return {
                    "available": False,
                    "message": f"Gemini API returned status code {resp.status_code}.",
                    "installed_models": Config.AVAILABLE_GEMINI_MODELS
                }
        except Exception as e:
            return {
                "available": False,
                "message": f"Could not connect to Gemini API: {str(e)}",
                "installed_models": Config.AVAILABLE_GEMINI_MODELS
            }

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Generate text response from Gemini model using Google Generative Language REST API.
        """
        if not self.api_key:
            # Check if local Ollama is available as graceful fallback
            try:
                ollama = OllamaLLM()
                if ollama.check_connection().get("available", False):
                    logger.info("Gemini API key missing. Falling back to Local Ollama.")
                    ollama_ans = ollama.generate(prompt, system_prompt=system_prompt)
                    return (
                        f"💡 *Note: Gemini API key is missing in `.env`. RAXEL answered using your local Ollama (`{ollama.model_name}`). "
                        f"To use Gemini Cloud, configure `GEMINI_API_KEY=AIzaSy...` in your `.env` file.*\n\n{ollama_ans}"
                    )
            except Exception as e:
                logger.debug(f"Ollama fallback attempt failed: {e}")

            return (
                "⚠️ **Gemini API Key Missing**\n\n"
                "Please configure your `GEMINI_API_KEY` in the environment or `.env` file to use Gemini API.\n"
                "Example: `GEMINI_API_KEY=AIzaSy...`\n\n"
                "👉 Alternatively, switch to **Local Ollama** in the top AI Provider dropdown."
            )

        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
        
        payload: Dict[str, Any] = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "topP": 0.9
            }
        }

        if system_prompt:
            payload["systemInstruction"] = {
                "parts": [{"text": system_prompt}]
            }

        try:
            logger.info(f"Sending prompt to Gemini API model '{self.model_name}'...")
            resp = requests.post(endpoint, json=payload, timeout=60)
            
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "").strip()
                return "⚠️ **Gemini API**: Empty response generated."
            elif resp.status_code in (401, 403):
                logger.error(f"Gemini API Auth error: {resp.status_code} - {resp.text}")
                return "⚠️ **Gemini API Error (401/403)**: Invalid API key. Please check your `GEMINI_API_KEY`."
            elif resp.status_code == 429:
                logger.error(f"Gemini API Quota/Rate Limit error: {resp.status_code}")
                return "⚠️ **Gemini API Error (429)**: Rate limit or quota exceeded. Please try again later."
            else:
                logger.error(f"Gemini API Error ({resp.status_code}): {resp.text}")
                err_detail = ""
                try:
                    err_json = resp.json()
                    err_detail = err_json.get("error", {}).get("message", resp.text)
                except Exception:
                    err_detail = resp.text
                return f"⚠️ **Gemini API Error ({resp.status_code})**: {err_detail}"
        except Exception as e:
            logger.error(f"Gemini API request exception: {str(e)}")
            return f"⚠️ **Connection Error while communicating with Gemini API**: {str(e)}"


def get_llm_provider(
    provider_name: Optional[str] = None,
    model_name: Optional[str] = None,
    api_key: Optional[str] = None
) -> BaseLLMProvider:
    """
    Factory function to retrieve LLM provider instance based on provider name.
    Supported providers: 'gemini' (default), 'ollama'.
    """
    selected_provider = (provider_name or Config.LLM_PROVIDER or "gemini").lower().strip()
    
    if selected_provider == "ollama":
        model = model_name or Config.LLM_MODEL
        return OllamaLLM(model_name=model, base_url=Config.OLLAMA_BASE_URL)
    else:
        model = model_name or Config.GEMINI_MODEL
        return GeminiProvider(model_name=model, api_key=api_key)
