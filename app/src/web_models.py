"""
Copyright 2025 5G-AICoder. All Rights Reserved.
Author: Marios Karagiannopoulos <mkaragiannop@juniper.net>
Module: WebServices API Models
"""

# pylint: disable=logging-fstring-interpolation,too-many-statements
from typing import List, Optional
from pydantic import BaseModel


# OpenAI-compatible chat completion request format
class Message(BaseModel):
    role: str  # "system", "user", "assistant"
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[Message]
    temperature: Optional[float] = 1.0
    max_tokens: Optional[int] = None
    top_p: Optional[float] = 1.0
    frequency_penalty: Optional[float] = 0.0
    presence_penalty: Optional[float] = 0.0


class ChatCompletionResponse(BaseModel):
    id: str
    object: str
    created: int
    model: str
    choices: List[dict]
    usage: dict


# OpenAI-compatible response model for listing models
class ModelData(BaseModel):
    id: str
    object: str = "model"
    created: int
    owned_by: str


class ModelListResponse(BaseModel):
    object: str = "list"
    data: list[ModelData]
