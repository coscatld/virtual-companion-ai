from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class RecentTurnsRequest(_message.Message):
    __slots__ = ("user_id", "companion_id")
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    COMPANION_ID_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    companion_id: str
    def __init__(self, user_id: _Optional[str] = ..., companion_id: _Optional[str] = ...) -> None: ...

class RecentTurnsResponse(_message.Message):
    __slots__ = ("messages",)
    MESSAGES_FIELD_NUMBER: _ClassVar[int]
    messages: _containers.RepeatedCompositeFieldContainer[HistoryMessage]
    def __init__(self, messages: _Optional[_Iterable[_Union[HistoryMessage, _Mapping]]] = ...) -> None: ...

class HistoryMessage(_message.Message):
    __slots__ = ("role", "content")
    ROLE_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    role: str
    content: str
    def __init__(self, role: _Optional[str] = ..., content: _Optional[str] = ...) -> None: ...

class ChatRequest(_message.Message):
    __slots__ = ("user_id", "system_prompt", "user_message", "companion_id", "skip_memory_write")
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    SYSTEM_PROMPT_FIELD_NUMBER: _ClassVar[int]
    USER_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    COMPANION_ID_FIELD_NUMBER: _ClassVar[int]
    SKIP_MEMORY_WRITE_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    system_prompt: str
    user_message: str
    companion_id: str
    skip_memory_write: bool
    def __init__(self, user_id: _Optional[str] = ..., system_prompt: _Optional[str] = ..., user_message: _Optional[str] = ..., companion_id: _Optional[str] = ..., skip_memory_write: bool = ...) -> None: ...

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
    __slots__ = ("audio_chunk", "session_id", "user_id", "system_prompt", "companion_id", "voice_id")
    AUDIO_CHUNK_FIELD_NUMBER: _ClassVar[int]
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    SYSTEM_PROMPT_FIELD_NUMBER: _ClassVar[int]
    COMPANION_ID_FIELD_NUMBER: _ClassVar[int]
    VOICE_ID_FIELD_NUMBER: _ClassVar[int]
    audio_chunk: bytes
    session_id: str
    user_id: str
    system_prompt: str
    companion_id: str
    voice_id: str
    def __init__(self, audio_chunk: _Optional[bytes] = ..., session_id: _Optional[str] = ..., user_id: _Optional[str] = ..., system_prompt: _Optional[str] = ..., companion_id: _Optional[str] = ..., voice_id: _Optional[str] = ...) -> None: ...

class AudioResponse(_message.Message):
    __slots__ = ("ai_audio_chunk", "ai_text", "audio_content_type", "user_text", "is_end", "error")
    AI_AUDIO_CHUNK_FIELD_NUMBER: _ClassVar[int]
    AI_TEXT_FIELD_NUMBER: _ClassVar[int]
    AUDIO_CONTENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    USER_TEXT_FIELD_NUMBER: _ClassVar[int]
    IS_END_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    ai_audio_chunk: bytes
    ai_text: str
    audio_content_type: str
    user_text: str
    is_end: bool
    error: str
    def __init__(self, ai_audio_chunk: _Optional[bytes] = ..., ai_text: _Optional[str] = ..., audio_content_type: _Optional[str] = ..., user_text: _Optional[str] = ..., is_end: bool = ..., error: _Optional[str] = ...) -> None: ...
