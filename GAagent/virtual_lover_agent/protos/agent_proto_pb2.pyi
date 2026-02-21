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
