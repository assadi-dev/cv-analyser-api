

from app.services.encryption_serrvice import EncryptionService
import os


def generate_keys():
    service = EncryptionService()

    if service.is_folder_exist():
        return
    service.generate_keys()
    print("privete key has been generated")
    print("public key has been generated")




generate_keys()