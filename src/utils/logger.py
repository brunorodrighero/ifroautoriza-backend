import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_logger():
    # --- INÍCIO DA CORREÇÃO ---
    # Define o caminho para o diretório raiz do projeto (indo "para cima" duas vezes a partir de src/utils/)
    project_root = Path(__file__).resolve().parents[2]
    log_dir = project_root / 'logs'

    # Cria o diretório de logs se ele não existir
    log_dir.mkdir(exist_ok=True)

    # Define o caminho completo e absoluto para o arquivo de log
    log_file_path = log_dir / 'app.log'
    # --- FIM DA CORREÇÃO ---

    logger = logging.getLogger("sistema_autorizacoes")
    logger.setLevel(logging.INFO)
    
    # Evita adicionar handlers duplicados
    if logger.hasHandlers():
        logger.handlers.clear()

    # Formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Console handler
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # File handler - agora usando o caminho absoluto
    fh = RotatingFileHandler(log_file_path, maxBytes=1024*1024*5, backupCount=5)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    
    return logger

logger = setup_logger()
