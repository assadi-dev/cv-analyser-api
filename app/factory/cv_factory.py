
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
            file_path=input.file_path,
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
            file_path=data["file_path"],
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