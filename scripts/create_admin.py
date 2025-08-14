import sys
from pathlib import Path
from getpass import getpass

# --- INÍCIO DA CORREÇÃO ---
# Pega o caminho do diretório onde o script está (a pasta 'scripts')
script_dir = Path(__file__).resolve().parent
# Pega o caminho do diretório pai (a raiz do projeto, 'ifroautoriza-backend')
project_root = script_dir.parent
# Adiciona a raiz do projeto ao caminho de busca de módulos do Python
sys.path.append(str(project_root))
# --- FIM DA CORREÇÃO ---

from src.db.session import SessionLocal
from src.db.models import Usuario
from src.core.security import get_password_hash
from src.utils.logger import logger

def create_admin_user():
    """
    Script para criar um usuário administrador interativamente.
    """
    db = SessionLocal()
    try:
        print("--- Criação de Usuário Administrador ---")
        
        # Coleta os dados do novo administrador
        nome = input("Nome completo do admin: ")
        email = input("Email do admin: ")
        
        # Verifica se o email já existe
        existing_user = db.query(Usuario).filter(Usuario.email == email).first()
        if existing_user:
            logger.error(f"O email '{email}' já está cadastrado. Abortando.")
            print(f"\nERRO: O email '{email}' já está cadastrado. Tente novamente com outro email.")
            return

        # Coleta a senha de forma segura (não exibe na tela)
        password = getpass("Senha (mínimo 8 caracteres): ")
        if len(password) < 8:
            logger.error("A senha informada é muito curta. Abortando.")
            print("\nERRO: A senha precisa ter no mínimo 8 caracteres.")
            return
            
        password_confirm = getpass("Confirme a senha: ")
        if password != password_confirm:
            logger.error("As senhas não coincidem. Abortando.")
            print("\nERRO: As senhas não coincidem.")
            return

        # Cria o hash da senha
        hashed_password = get_password_hash(password)

        # Cria a nova instância do usuário
        admin_user = Usuario(
            nome=nome,
            email=email,
            senha_hash=hashed_password,
            tipo='admin',  # Define o tipo como admin
            ativo=True
        )

        # Adiciona ao banco de dados
        db.add(admin_user)
        db.commit()

        logger.info(f"Usuário administrador '{email}' criado com sucesso!")
        print(f"\nSUCESSO: Usuário administrador '{email}' foi criado.")

    except Exception as e:
        logger.error(f"Ocorreu um erro ao criar o admin: {e}")
        print(f"\nERRO INESPERADO: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_admin_user()