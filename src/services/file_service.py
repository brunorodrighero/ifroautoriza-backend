import aiofiles
import os
import uuid
from pathlib import Path
from fastapi import UploadFile, HTTPException
from src.core.config import settings
from src.utils.logger import logger

async def save_upload_file(upload_file: UploadFile) -> str:
    # Adiciona um log para sabermos exatamente o tipo de arquivo recebido
    logger.info(f"Tentativa de upload do arquivo '{upload_file.filename}' com content-type: {upload_file.content_type}")

    # --- LÓGICA DE VALIDAÇÃO FLEXÍVEL E ROBUSTA ---
    # Permite 'application/pdf' ou qualquer tipo que comece com 'image/'
    
    content_type = upload_file.content_type
    
    if not (content_type == 'application/pdf' or (content_type and content_type.startswith('image/'))):
        logger.warning(f"Upload bloqueado: Tipo de arquivo inválido '{content_type}' para o arquivo '{upload_file.filename}'.")
        raise HTTPException(status_code=400, detail="Tipo de arquivo inválido. Apenas PDF e imagens são permitidos.")
    
    contents = await upload_file.read()
    if len(contents) > settings.MAX_FILE_SIZE:
        logger.warning(f"Upload bloqueado: Arquivo '{upload_file.filename}' excedeu o tamanho máximo de {settings.MAX_FILE_SIZE} bytes.")
        raise HTTPException(status_code=400, detail="Arquivo muito grande.")
    
    upload_dir = Path(settings.UPLOAD_DIRECTORY)
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    ext = Path(upload_file.filename).suffix
    # Garante que a extensão seja minúscula para consistência
    filename = f"{uuid.uuid4()}{ext.lower()}"
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