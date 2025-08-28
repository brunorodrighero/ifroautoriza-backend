# ifroautoriza-backend/src/api/endpoints/campus.py

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from src.db import models, schemas
from src.api import deps

router = APIRouter()

@router.post(
    "/",
    response_model=schemas.Campus,
    status_code=status.HTTP_201_CREATED,
    summary="Cria um novo Campus",
    description="Cria um novo campus no sistema. Apenas administradores podem executar esta ação."
)
def create_campus(
    *,
    db: Session = Depends(deps.get_db),
    campus_in: schemas.CampusCreate,
    current_user: models.Usuario = Depends(deps.get_current_active_admin)
):
    """
    Endpoint para criar um novo campus.
    - **nome**: Nome do novo campus.
    """
    db_campus = db.query(models.Campus).filter(models.Campus.nome == campus_in.nome).first()
    if db_campus:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Um campus com este nome já existe.",
        )
    
    new_campus = models.Campus(nome=campus_in.nome)
    db.add(new_campus)
    db.commit()
    db.refresh(new_campus)
    return new_campus

@router.get(
    "/",
    response_model=List[schemas.Campus],
    summary="Lista todos os Campi",
    description="Retorna uma lista de todos os campi cadastrados no sistema. Este é um endpoint público."
)
def read_campuses(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100
):
    """
    Endpoint para listar todos os campi com paginação.
    """
    campuses = db.query(models.Campus).order_by(models.Campus.nome).offset(skip).limit(limit).all()
    return campuses

@router.put(
    "/{campus_id}",
    response_model=schemas.Campus,
    summary="Atualiza um Campus",
    description="Atualiza o nome de um campus existente. Apenas administradores."
)
def update_campus(
    *,
    db: Session = Depends(deps.get_db),
    campus_id: int,
    campus_in: schemas.CampusUpdate,
    current_user: models.Usuario = Depends(deps.get_current_active_admin)
):
    """
    Endpoint para atualizar um campus.
    - **campus_id**: ID do campus a ser atualizado.
    """
    campus = db.query(models.Campus).filter(models.Campus.id == campus_id).first()
    if not campus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campus não encontrado.",
        )
    
    existing_campus = db.query(models.Campus).filter(models.Campus.nome == campus_in.nome).first()
    if existing_campus and existing_campus.id != campus_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Um campus com este nome já existe.",
        )

    campus.nome = campus_in.nome
    db.commit()
    db.refresh(campus)
    return campus

@router.delete(
    "/{campus_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deleta um Campus",
    description="Deleta um campus do sistema. Apenas administradores."
)
def delete_campus(
    *,
    db: Session = Depends(deps.get_db),
    campus_id: int,
    current_user: models.Usuario = Depends(deps.get_current_active_admin)
):
    """
    Endpoint para deletar um campus.
    - **campus_id**: ID do campus a ser deletado.
    \n
    *Nota: Um campus não pode ser deletado se houver usuários ou eventos associados a ele.*
    """
    campus = db.query(models.Campus).filter(models.Campus.id == campus_id).first()
    if not campus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campus não encontrado.",
        )
    
    if campus.usuarios or campus.eventos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível excluir o campus pois existem usuários ou eventos associados a ele.",
        )

    db.delete(campus)
    db.commit()
    return