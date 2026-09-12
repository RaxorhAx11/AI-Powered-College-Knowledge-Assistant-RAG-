import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.config import Config
from src.llm import BaseLLMProvider, GeminiProvider, OllamaLLM, get_llm_provider

def test_providers():
    print("========================================")
    print("Testing LLM Provider Abstraction Layer")
    print("========================================")

    # 1. Test Gemini Provider Instantiation & Check Connection
    print("\n[1] Gemini Provider:")
    gemini_p = get_llm_provider("gemini")
    print(f"Provider: {gemini_p.provider_name} ({gemini_p.provider_id})")
    print(f"Model: {gemini_p.model_name}")
    print(f"API Key present: {bool(gemini_p.api_key)}")
    gemini_conn = gemini_p.check_connection()
    print(f"Connection status: {gemini_conn}")

    # Test Gemini generation gracefully if API Key is missing or present
    res_gemini = gemini_p.generate("Hello, state in one short sentence what RAXEL assistant does.")
    print(f"Gemini output response snippet:\n{res_gemini[:200]}")

    # 2. Test Ollama Provider Instantiation & Check Connection
    print("\n[2] Ollama Provider (Preserved):")
    ollama_p = get_llm_provider("ollama")
    print(f"Provider: {ollama_p.provider_name} ({ollama_p.provider_id})")
    print(f"Model: {ollama_p.model_name}")
    ollama_conn = ollama_p.check_connection()
    print(f"Connection status: {ollama_conn}")

    print("\n========================================")
    print("Provider Abstraction Test Complete!")
    print("========================================")

if __name__ == "__main__":
    test_providers()
