"""
pydantic_settings — Genuine BaseSettings implementation reading from os.environ.
"""
from __future__ import annotations

import os
from typing import Any
from pydantic import BaseModel


class BaseSettings(BaseModel):
    def __init__(self, **data: Any):
        env_data = {}
        annotations = self._get_resolved_annotations()
        for k in annotations:
            # Check direct name, uppercase, or prefixed
            for env_key in (k, k.upper(), k.lower()):
                if env_key in os.environ:
                    env_data[k] = os.environ[env_key]
                    break
        # Passed data overrides env vars
        combined = {**env_data, **data}
        super().__init__(**combined)
