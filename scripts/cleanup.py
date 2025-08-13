import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Adiciona o diretório raiz ao path para importar módulos do projeto
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.db.session import SessionLocal
from src.db.models import Autorizacao
from src.services.file_service import delete_file
from src.utils.logger import logger

def cleanup_old_records():
    db = SessionLocal()
    try:
        two_years_ago = datetime.now() - timedelta(days=365*2)
        
        old_authorizations = db.query(Autorizacao).filter(Autorizacao.submetido_em < two_years_ago).all()
        
        if not old_authorizations:
            logger.info("Limpeza: Nenhum registro antigo encontrado.")
            return

        logger.info(f"Limpeza: Encontrados {len(old_authorizations)} registros com mais de 2 anos.")
        
        for auth in old_authorizations:
            if auth.caminho_arquivo:
                delete_file(auth.caminho_arquivo)
            db.delete(auth)
        
        db.commit()
        logger.info("Limpeza: Registros e arquivos antigos removidos com sucesso.")
        
    except Exception as e:
        logger.error(f"Erro no script de limpeza: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    cleanup_old_records()