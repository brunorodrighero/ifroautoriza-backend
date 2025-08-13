# src/api/deps.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError, jwt

from src.core.config import settings
from src.db import models
from src.db.session import SessionLocal

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/token")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> models.Usuario:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(models.Usuario).filter(models.Usuario.email == email).first()
    if user is None:
        raise credentials_exception
    return user

def get_current_active_user(current_user: models.Usuario = Depends(get_current_user)) -> models.Usuario:
    if not current_user.ativo:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Usuário inativo")
    return current_user

# ===== NOVAS DEPENDÊNCIAS DE AUTORIZAÇÃO =====

def get_event_by_id_for_user(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_active_user)
) -> models.Evento:
    """
    Busca um evento e verifica se o usuário atual (professor ou admin) tem permissão para acessá-lo.
    """
    event = db.query(models.Evento).filter(models.Evento.id == event_id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evento não encontrado")
    
    # Admin tem acesso a tudo. Professor só tem acesso ao que criou.
    if current_user.tipo != 'admin' and event.usuario_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Ação não permitida")
        
    return event

def get_authorization_by_id_for_user(
    autorizacao_id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_active_user)
) -> models.Autorizacao:
    """
    Busca uma autorização e verifica se o usuário atual (professor ou admin) tem permissão para acessá-la.
    """
    autorizacao = db.query(models.Autorizacao).filter(models.Autorizacao.id == autorizacao_id).first()
    if not autorizacao:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Autorização não encontrada")
        
    # A permissão é verificada através do evento ao qual a autorização pertence.
    if current_user.tipo != 'admin' and autorizacao.evento.usuario_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Ação não permitida")
        
    return autorizacao