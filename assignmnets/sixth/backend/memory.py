# backend/memory.py
from typing import Optional
from .schemas import MemoryRecord, StoryPreferences

class MemoryLayer:
    def __init__(self) -> None:
        self._store: dict[str, MemoryRecord] = {}

    def get(self, user_id: str) -> Optional[MemoryRecord]:
        return self._store.get(user_id)

    def upsert(self, user_id: str, prefs: StoryPreferences, last_topic: Optional[str] = None) -> MemoryRecord:
        rec = MemoryRecord(last_preferences=prefs, last_topic=last_topic)
        self._store[user_id] = rec
        return rec
