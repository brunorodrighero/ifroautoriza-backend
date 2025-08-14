# src/api/endpoints/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from src.api.deps import get_db
from src.core.security import create_access_token, verify_password, get_password_hash
from src.db import models, schemas
from src.utils.logger import logger

router = APIRouter()

@router.post("/register", response_model=schemas.User, status_code=status.HTTP_201_CREATED)
def register_user(
    user_in: schemas.UserCreate,
    db: Session = Depends(get_db)
):
    """
    Endpoint para registro de novos usuários (professores).
    """
    # Verifica se o usuário já existe
    db_user = db.query(models.Usuario).filter(models.Usuario.email == user_in.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este email já está cadastrado.",
        )
    
    hashed_password = get_password_hash(user_in.password)
    # Todos os novos registros são do tipo 'professor' por padrão.
    db_user = models.Usuario(
        email=user_in.email,
        nome=user_in.nome,
        senha_hash=hashed_password,
        tipo='professor'
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    logger.info(f"Novo usuário registrado: {user_in.email}")
    return db_user

@router.post("/token", response_model=schemas.Token)
def login_for_access_token(
    db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
):
    # ... (lógica de verificação do usuário)
    user = db.query(models.Usuario).filter(models.Usuario.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.ativo:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Usuário inativo")

    access_token = create_access_token(data={"sub": user.email}, user=user) # Passa o objeto 'user'
    return {"access_token": access_token, "token_type": "bearer"}