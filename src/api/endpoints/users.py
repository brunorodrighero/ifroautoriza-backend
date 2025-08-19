# src/api/endpoints/users.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

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
        tipo=user_in.tipo,
        ativo=user_in.ativo
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    logger.info(f"Admin '{current_user.email}' criou o usuário '{user_in.email}' com tipo '{user_in.tipo}'.")
    return db_user

# --- NOVO ENDPOINT DE ATUALIZAÇÃO ---
@router.put("/{user_id}", response_model=schemas.User)
def update_user_by_admin(
    user_id: int,
    user_in: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_active_admin)
):
    """
    Atualiza um usuário. Apenas para administradores.
    """
    user_to_update = db.query(models.Usuario).filter(models.Usuario.id == user_id).first()
    if not user_to_update:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado.",
        )

    update_data = user_in.model_dump(exclude_unset=True)
    
    if "password" in update_data and update_data["password"]:
        hashed_password = get_password_hash(update_data["password"])
        user_to_update.senha_hash = hashed_password
    
    # Atualiza outros campos
    for key, value in update_data.items():
        if key != "password":
            setattr(user_to_update, key, value)
            
    db.commit()
    db.refresh(user_to_update)
    
    logger.info(f"Admin '{current_user.email}' atualizou o usuário '{user_to_update.email}' (ID: {user_id}).")
    return user_to_update

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