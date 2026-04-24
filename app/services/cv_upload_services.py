from app.services.upload_servive import UploadService
from fastapi import UploadFile
from app.core.config import settings

class CVUploadService():
    """
    CV upload service — handles CV file uploads and validation.
    """
    def __init__(self):
        self.upload_service = UploadService()

    async def upload_cv(self, file: UploadFile, user_id: str) -> dict[str, str]:
        self.upload_service.validate_file_extension(self.upload_service.get_file_extension(file))
        self.upload_service.validate_file_size(file)
        key = self.upload_service.generate_file_key(file)
        file_path = await self.upload_service.save_file(file, user_id, settings.cv_dir, key)
        return {
            "id": key,
            "filename": file.filename,
            "extension": self.upload_service.get_file_extension(file),
            "mime_type": self.upload_service.get_file_mime_type(file),
            "file_size_kb": self.upload_service.get_file_size(file) // 1024,
            "file_path": file_path,
            "key": f"{settings.cv_dir}/{key}",
        }