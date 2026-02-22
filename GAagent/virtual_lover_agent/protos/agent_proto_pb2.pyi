from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class ChatRequest(_message.Message):
    __slots__ = ("user_id", "system_prompt", "user_message")
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    SYSTEM_PROMPT_FIELD_NUMBER: _ClassVar[int]
    USER_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    system_prompt: str
    user_message: str
    def __init__(self, user_id: _Optional[str] = ..., system_prompt: _Optional[str] = ..., user_message: _Optional[str] = ...) -> None: ...

class ChatResponse(_message.Message):
    __slots__ = ("delta", "emotion", "is_end")
    DELTA_FIELD_NUMBER: _ClassVar[int]
    EMOTION_FIELD_NUMBER: _ClassVar[int]
    IS_END_FIELD_NUMBER: _ClassVar[int]
    delta: str
    emotion: str
    is_end: bool
    def __init__(self, delta: _Optional[str] = ..., emotion: _Optional[str] = ..., is_end: bool = ...) -> None: ...

class AudioRequest(_message.Message):
    __slots__ = ("audio_chunk", "session_id", "user_id", "system_prompt")
    AUDIO_CHUNK_FIELD_NUMBER: _ClassVar[int]
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    SYSTEM_PROMPT_FIELD_NUMBER: _ClassVar[int]
    audio_chunk: bytes
    session_id: str
    user_id: str
    system_prompt: str
    def __init__(self, audio_chunk: _Optional[bytes] = ..., session_id: _Optional[str] = ..., user_id: _Optional[str] = ..., system_prompt: _Optional[str] = ...) -> None: ...

class AudioResponse(_message.Message):
    __slots__ = ("ai_audio_chunk", "ai_text")
    AI_AUDIO_CHUNK_FIELD_NUMBER: _ClassVar[int]
    AI_TEXT_FIELD_NUMBER: _ClassVar[int]
    ai_audio_chunk: bytes
    ai_text: str
    def __init__(self, ai_audio_chunk: _Optional[bytes] = ..., ai_text: _Optional[str] = ...) -> None: ...
