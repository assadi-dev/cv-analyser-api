from pydantic import BaseModel,Field,model_validator

class DecryptionPayload(BaseModel): 
    encrypted_key:str = Field(...,description="encrypted key")
    iv:str = Field(...,description="iv")
    encrypted_data:str = Field(...,description="encrypted data")

