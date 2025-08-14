# src/api/endpoints/auth.py
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import random

from src.api.deps import get_db
from src.core.security import create_access_token, verify_password, get_password_hash
from src.db import models, schemas
from src.utils.logger import logger
from src.services.email_service import EmailService

router = APIRouter()

def generate_verification_code() -> str:
    """Gera um código numérico de 4 dígitos."""
    return str(random.randint(1000, 9999))

# --- FLUXO DE CADASTRO DE PROFESSOR ---

@router.post("/register/request-code", status_code=status.HTTP_200_OK)
async def request_registration_code(
    user_in: schemas.ProfessorRegisterRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Passo 1 do Cadastro: Valida o e-mail @ifro.edu.br, cria um usuário inativo
    e envia um código de verificação.
    """
    if not user_in.email.endswith('@ifro.edu.br'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cadastro permitido apenas para e-mails institucionais (@ifro.edu.br)."
        )

    db_user = db.query(models.Usuario).filter(models.Usuario.email == user_in.email).first()
    if db_user and db_user.ativo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este e-mail já está cadastrado e ativo. Use a opção 'Esqueci minha senha'."
        )

    if not db_user:
        db_user = models.Usuario(email=user_in.email, nome=user_in.nome, tipo='professor')
        db.add(db_user)
    
    db_user.codigo_verificacao = generate_verification_code()
    db_user.codigo_verificacao_expira_em = datetime.now() + timedelta(minutes=10)
    db.commit()
    db.refresh(db_user) # Necessário para obter o ID do novo usuário
    
    # CORREÇÃO: Passando o ID do usuário em vez do objeto
    background_tasks.add_task(EmailService.send_verification_code, db_user.id, "Código de Confirmação de Cadastro")
    logger.info(f"Código de cadastro enviado para {user_in.email}")
    return {"message": "Código de verificação enviado para o seu e-mail."}

@router.post("/register/verify-code", status_code=status.HTTP_200_OK)
def verify_registration_code(form_data: schemas.VerifyCode, db: Session = Depends(get_db)):
    """
    Passo 2 do Cadastro: Verifica se o código fornecido é válido.
    """
    user = db.query(models.Usuario).filter(models.Usuario.email == form_data.email).first()
    if not user or user.codigo_verificacao != form_data.codigo or user.codigo_verificacao_expira_em < datetime.now():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Código inválido ou expirado.")
    
    return {"message": "Código verificado com sucesso. Prossiga para criar sua senha."}

@router.post("/register/set-password", status_code=status.HTTP_200_OK)
def set_registration_password(form_data: schemas.SetPassword, db: Session = Depends(get_db)):
    """
    Passo 3 do Cadastro: Define a senha e ativa o usuário.
    """
    user = db.query(models.Usuario).filter(models.Usuario.email == form_data.email).first()
    if not user or user.codigo_verificacao != form_data.codigo or user.codigo_verificacao_expira_em < datetime.now():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Código inválido ou expirado. Tente novamente.")
        
    user.senha_hash = get_password_hash(form_data.password)
    user.ativo = True
    user.codigo_verificacao = None
    user.codigo_verificacao_expira_em = None
    db.commit()
    
    logger.info(f"Usuário {user.email} completou o cadastro e ativou a conta.")
    return {"message": "Senha criada e cadastro concluído com sucesso! Você já pode fazer o login."}

# --- FLUXO DE RECUPERAÇÃO DE SENHA ---

@router.post("/password-reset/request-code", status_code=status.HTTP_200_OK)
async def request_password_reset_code(
    form_data: schemas.RequestCode,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Passo 1 do Reset: Envia um código de recuperação para um e-mail existente e ativo.
    """
    user = db.query(models.Usuario).filter(models.Usuario.email == form_data.email, models.Usuario.ativo == True).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nenhum usuário ativo encontrado com este e-mail.")
        
    user.codigo_verificacao = generate_verification_code()
    user.codigo_verificacao_expira_em = datetime.now() + timedelta(minutes=10)
    db.commit()
    db.refresh(user) # Necessário para obter o ID
    
    # CORREÇÃO: Passando o ID do usuário em vez do objeto
    background_tasks.add_task(EmailService.send_verification_code, user.id, "Código de Recuperação de Senha")
    logger.info(f"Código de recuperação de senha enviado para {form_data.email}")
    return {"message": "Código de recuperação enviado para o seu e-mail."}

# --- LOGIN (TOKEN) ---

@router.post("/token", response_model=schemas.Token)
def login_for_access_token(
    db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    Endpoint para login e obtenção de token JWT.
    """
    user = db.query(models.Usuario).filter(models.Usuario.email == form_data.username).first()
    if not user or not user.senha_hash or not verify_password(form_data.password, user.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.ativo:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Usuário inativo ou cadastro não finalizado.")

    access_token = create_access_token(data={"sub": user.email}, user=user)
    return {"access_token": access_token, "token_type": "bearer"}
