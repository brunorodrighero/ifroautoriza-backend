import aiofiles
import os
import uuid
from pathlib import Path
from fastapi import UploadFile, HTTPException
from src.core.config import settings
from src.utils.logger import logger

async def save_upload_file(upload_file: UploadFile) -> str:
    if upload_file.content_type not in settings.ALLOWED_FILE_TYPES:
        raise HTTPException(status_code=400, detail="Tipo de arquivo inválido.")
    
    contents = await upload_file.read()
    if len(contents) > settings.MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="Arquivo muito grande.")
    
    upload_dir = Path(settings.UPLOAD_DIRECTORY)
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    ext = Path(upload_file.filename).suffix
    filename = f"{uuid.uuid4()}{ext}"
    file_path = upload_dir / filename
    
    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(contents)
    
    logger.info(f"Arquivo '{upload_file.filename}' salvo como '{filename}'")
    return filename

def delete_file(filename: str):
    file_path = Path(settings.UPLOAD_DIRECTORY) / filename
    try:
        if file_path.is_file():
            os.remove(file_path)
            logger.info(f"Arquivo deletado: {file_path}")
        else:
            logger.warning(f"Arquivo para deletar não encontrado: {file_path}")
    except Exception as e:
        logger.error(f"Erro ao deletar o arquivo {file_path}: {e}")
        raise