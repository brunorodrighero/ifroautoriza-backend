import logging
from logging.handlers import RotatingFileHandler

def setup_logger():
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

    # File handler
    fh = RotatingFileHandler('logs/app.log', maxBytes=1024*1024*5, backupCount=5)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    
    return logger

logger = setup_logger()