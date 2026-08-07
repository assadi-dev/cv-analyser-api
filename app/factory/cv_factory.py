
from pathlib import Path
from app.core.config import settings
from app.schemas.cv_upload import CVUploadResult
from app.models.cv import CV
import uuid


class CVFactory:
    """
    CV factory — creates CV models from different input types.
    """
    @staticmethod
    def create_from_upload_result_to_model(user_id: str, input: CVUploadResult) -> CV:
        """
        Create a CV model from an upload result.
        """
        return CV(
            user_id=uuid.UUID(user_id),
            name=input.filename,
            extension=input.extension,
            mime_type=input.mime_type,
            file_size_kb=input.file_size_kb,
            key=input.key,
            is_default=False,
        )

    @staticmethod
    def create_from_dict_to_model(data: dict) -> CV:
        """
        Create a CV model from a dictionary.
        """
        return CV(
            user_id=uuid.UUID(data["user_id"]),
            name=data["name"],
            extension=data["extension"],
            mime_type=data["mime_type"],
            file_size_kb=data["file_size_kb"],
            key=data["key"],
            is_default=data["is_default"],

        )


    @staticmethod
    def update_request_to_model(cv: CV, inputs: dict) -> CV:
        """Updates an existing CV model with input data."""
        for key, value in inputs.items():
            if hasattr(cv, key):
                setattr(cv, key, value)
        return cv



    @staticmethod
    def get_absolute_cv_path(cv: CV) -> str:
        """Get the full path to a CV file."""
        full_path = Path(settings.upload_dir) / str(cv.user_id) / cv.key
        return str(full_path)


    @staticmethod
    def get_absolute_cv_user_folder(user_id: str) -> str:
        """Get the full path to a CV user folder."""
        full_path = Path(settings.upload_dir) / str(user_id) / settings.cv_dir
        return str(full_path)
   
    @staticmethod
    def get_absolute_user_folder(user_id: str) -> str:
        """Get the full path to a CV user folder."""
        full_path = Path(settings.upload_dir) / str(user_id)
        return str(full_path)