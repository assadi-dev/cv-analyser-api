import shutil
import uuid
from app.core.exceptions import FileTooLargeError
from app.core.exceptions import UnsupportedFileTypeError
from app.core.config import settings
from fastapi import UploadFile
from pathlib import Path




class UploadService:
    def __init__(self):
        pass


    def get_file_extension(self, file: UploadFile) -> str:
        # Validate file extension
        extension = Path(file.filename or "").suffix.lower()
        return extension

    def validate_file_extension(self, extension: str) -> None:
        if extension not in settings.allowed_cv_extensions:
            raise UnsupportedFileTypeError(
                detail=f"Invalid file extension: {extension}. Allowed: {', '.join(settings.allowed_cv_extensions)}"
            )

    def validate_file_size(self, file: UploadFile) -> None:
        if file.size > settings.max_cv_size_bytes:
            raise FileTooLargeError(
                detail=f"File too large: {file.size}. Allowed: {settings.max_cv_size_bytes}"
            )

    def create_upload_folder(self, user_id: str, folder: str) -> Path:
        upload_path = Path(settings.upload_dir) / user_id/folder
        upload_path.mkdir(parents=True, exist_ok=True)
        return upload_path

    def remove_file(self, file_path: str) -> None:
        file_path = Path(file_path)
        if file_path.exists():
            file_path.unlink()
    
    def remove_folder_recursively(self, folder_path: str) -> None:
        folder_path = Path(folder_path)
        if folder_path.exists():
            shutil.rmtree(folder_path)

    def generate_file_name(self, file: UploadFile) -> dict[str, str]:
        extension = self.get_file_extension(file)
        id = uuid.uuid4().hex
        return {
            "id": id,
            "name": file.filename,
            "extension": extension,
            "key": f"{id}{extension}",
            
        }

    def generate_file_key(self, file: UploadFile) -> str:
        extension = self.get_file_extension(file)
        id = uuid.uuid4().hex
        return f"{id}{extension}"

    async def save_file(self, file: UploadFile, user_id: str, folder: str,key:str) -> str:
        # Read and validate file size
        content = await file.read()
        self.validate_file_size(file)

        # Create upload folder if not exists
        upload_path = self.create_upload_folder(user_id, folder)

        # Save file to disk
        save_path = upload_path / key
        save_path.write_bytes(content)
        return save_path

        

    def get_file_size(self, file: UploadFile) -> int:
        return file.size

    def get_file_mime_type(self, file: UploadFile) -> str:
        return file.content_type
