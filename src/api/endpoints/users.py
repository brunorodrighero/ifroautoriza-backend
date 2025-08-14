# src/api/endpoints/users.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from src.api.deps import get_db, get_current_active_admin
from src.core.security import get_password_hash
from src.db import models, schemas
from src.utils.logger import logger

router = APIRouter()

@router.get("/", response_model=List[schemas.User])
def read_users(
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_active_admin)
):
    """
    Retorna todos os usuários. Apenas para administradores.
    """
    users = db.query(models.Usuario).order_by(models.Usuario.nome).all()
    return users

@router.post("/", response_model=schemas.User, status_code=status.HTTP_201_CREATED)
def create_user_by_admin(
    user_in: schemas.UserAdminCreate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_active_admin)
):
    """
    Cria um novo usuário com um tipo específico. Apenas para administradores.
    """
    db_user = db.query(models.Usuario).filter(models.Usuario.email == user_in.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este email já está cadastrado.",
        )
    
    hashed_password = get_password_hash(user_in.password)
    db_user = models.Usuario(
        email=user_in.email,
        nome=user_in.nome,
        senha_hash=hashed_password,
        tipo=user_in.tipo
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    logger.info(f"Admin '{current_user.email}' criou o usuário '{user_in.email}' com tipo '{user_in.tipo}'.")
    return db_user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_by_admin(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_active_admin)
):
    """
    Deleta um usuário. Apenas para administradores.
    Um admin não pode deletar a si mesmo.
    """
    # Impede que um admin delete a própria conta
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Você não pode deletar sua própria conta de administrador.",
        )

    user_to_delete = db.query(models.Usuario).filter(models.Usuario.id == user_id).first()
    if not user_to_delete:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado.",
        )

    db.delete(user_to_delete)
    db.commit()
    
    logger.warning(f"Admin '{current_user.email}' DELETOU o usuário '{user_to_delete.email}' (ID: {user_id}).")
    return