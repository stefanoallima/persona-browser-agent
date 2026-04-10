"""Configuration loading and validation."""

import os
from pathlib import Path
from typing import List, Optional

import yaml
from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    provider: str = "openrouter"
    model: str = "google/gemini-2.5-flash-preview"
    endpoint: str = "https://openrouter.ai/api/v1"
    api_key_env: str = "OPENROUTER_API_KEY"
    temperature: float = 0.1
    max_tokens: int = 20000




class ScoringLLMConfig(BaseModel):
    provider: str = "openrouter"
    model: str = "google/gemini-2.5-flash-preview"  # non-empty default prevents late errors
    endpoint: str = "https://openrouter.ai/api/v1"
    api_key_env: str = "OPENROUTER_API_KEY"
    temperature: float = 0.1
    max_tokens: int = 20000


class ScoringConfig(BaseModel):
    text_scorer: ScoringLLMConfig = Field(
        default_factory=lambda: ScoringLLMConfig(
            model="zhipuai/glm-5-turbo",
        )
    )
    visual_scorer: ScoringLLMConfig = Field(
        default_factory=lambda: ScoringLLMConfig(
            model="google/gemini-3-flash",
        )
    )
    reconciler: ScoringLLMConfig = Field(
        default_factory=lambda: ScoringLLMConfig(
            model="anthropic/claude-sonnet-4-6",
        )
    )

class BrowserConfig(BaseModel):
    headless: bool = True
    width: int = Field(default=1280, gt=0)
    height: int = Field(default=720, gt=0)
    # Legacy field — kept for backward compatibility with old config files.
    # timeout_seconds takes precedence when set.
    timeout: int = 300
    record_video: bool = False
    record_video_dir: str = "./recordings"
    # Navigator control fields (v2+)
    max_steps: int = Field(default=50, gt=0)  # Max browser-use agent steps before stopping
    timeout_seconds: int = Field(default=120, gt=0)  # Max seconds for navigator session
    app_domains: List[str] = Field(default_factory=list)  # Domains for HAR filtering (empty = all)
    capture_network: bool = True    # Enable HAR recording


class ReportingConfig(BaseModel):
    screenshots: bool = True
    screenshots_dir: str = "./screenshots"
    format: str = "json"


class Config(BaseModel):
    llm: LLMConfig = Field(default_factory=LLMConfig)
    scoring: ScoringConfig = Field(default_factory=ScoringConfig)
    browser: BrowserConfig = Field(default_factory=BrowserConfig)
    reporting: ReportingConfig = Field(default_factory=ReportingConfig)


def load_config(config_path: Optional[str] = None) -> Config:
    """Load config from YAML file, falling back to defaults."""
    if config_path and Path(config_path).exists():
        with open(config_path) as f:
            data = yaml.safe_load(f) or {}
        return Config(**data)

    # Check default locations
    for default_path in ["config.yaml", "persona-browser-agent/config.yaml"]:
        if Path(default_path).exists():
            with open(default_path) as f:
                data = yaml.safe_load(f) or {}
            return Config(**data)

    return Config()


def get_api_key(config: LLMConfig) -> str:
    """Get API key from environment variable."""
    key = os.environ.get(config.api_key_env, "")
    if not key:
        raise ValueError(
            f"Missing API key: set the {config.api_key_env} environment variable.\n"
            f"Provider: {config.provider}, Model: {config.model}"
        )
    return key
