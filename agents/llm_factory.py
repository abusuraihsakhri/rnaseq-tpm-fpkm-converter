"""
Deterministic demonstration responder with basic identifier screening; not a live LLM.
"""
from typing import Dict, Any, Optional
from .base import PHIGuard


class MockLLM:
    def __init__(self, system_name: str = "Rnaseq Tpm Fpkm Converter"):
        self.system_name = system_name

    def invoke(self, prompt: str) -> str:
        PHIGuard.assert_no_phi(prompt)
        return f"[{self.system_name} Deterministic Verification Engine]: Demonstration response only (no model inference or scientific validation). Query excerpt: '{prompt[:60]}...'."


class LLMFactory:
    """Creates a deterministic demonstration responder; other providers are unsupported."""

    @staticmethod
    def create(provider: str = "mock", system_name: str = "Rnaseq Tpm Fpkm Converter"):
        prov = str(provider).lower()
        if prov in ["mock", "deterministic", "test"]:
            return MockLLM(system_name)
        raise ValueError("Only the deterministic mock provider is implemented")
