

from typing import Any
from pathlib import Path
from pydantic import Field, model_validator, field_validator
from app.schemas.common import AppBaseModel



class CVUploadResult(AppBaseModel):
    id:str = Field(..., description="CV ID")
    filename: str = Field(..., description="CV filename")
    extension: str = Field(..., description="CV extension")
    mime_type: str = Field(..., description="CV mime type")
    file_size_kb: int = Field(..., description="CV file size in KB")
    file_path: str = Field(..., description="CV file path")
    key: str = Field(..., description="CV key")

    @model_validator(mode="before")
    @classmethod
    def parse_file_path(cls, v: dict) -> dict:
        if isinstance(v, dict):
            v["file_path"] = str(v["file_path"])
        return v

    @classmethod
    def from_dict(cls, data: dict) -> "CVUploadResult":
        return cls(**data)

        

