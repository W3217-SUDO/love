from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MediaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    kind: str
    sha256: str
    mime: str
    size_bytes: int
    width: int | None
    height: int | None
    exif_taken_at: datetime | None
    thumb_url: str = ""
    preview_url: str = ""
