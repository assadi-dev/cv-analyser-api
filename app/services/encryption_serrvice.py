from app.core.logging import get_logger
from email import base64mime
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from app.core.config import settings
import os
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import base64
import json
from app.schemas.encryption import DecryptionPayload



logger = get_logger(__name__)

class EncryptionService:

  def __init__(self):
    self.private_key = None
    self.public_key = None
    self.private_key_path = settings.secrets_dir + "/private_key.pem"
    self.public_key_path = settings.secrets_dir + "/public_key.pem"


  def is_folder_exist(self):
    if not os.path.exists(settings.secrets_dir):
        os.makedirs(settings.secrets_dir, exist_ok=True)
    if os.path.exists(self.private_key_path) and os.path.exists(self.public_key_path):
        return True
    return False


  def generate_keys(self):
    self.private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    self.public_key = self.private_key.public_key()
    with open(self.private_key_path, "wb") as f:
        f.write(self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ))
    with open(self.public_key_path, "wb") as f:
        f.write(self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ))
 
  
  def load_public_key(self):
    with open(self.private_key_path, "rb") as f:
        self.private_key = serialization.load_pem_private_key(
            f.read(),
            password=None,
        )
    with open(self.public_key_path, "rb") as f:
        self.public_key = f.read().decode("utf-8")
        
    """ 
    def encrypt(self, data: str) -> bytes:
        pass 
    """



  def decrypt(self,payload:DecryptionPayload) -> str:
    try:
        with open(self.private_key_path, "rb") as f:
            private_key = serialization.load_pem_private_key(f.read(), password=None)
            encrypted_key = base64.b64decode(payload.encrypted_key)
            iv = base64.b64decode(payload.iv)
            encrypted_data = base64.b64decode(payload.encrypted_data)   
            aes_key = private_key.decrypt(
            encrypted_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )

        aesgcm = AESGCM(aes_key)
        plaintext = aesgcm.decrypt(iv, encrypted_data, None)
        print("data decrypted successfully")
        return plaintext.decode("utf-8")
    except Exception as e:
        logger.error(e)
        return ""

    

