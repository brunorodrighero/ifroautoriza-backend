# src/api/endpoints/events.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import uuid
from typing import List
from datetime import date

from src.api.deps import get_db, get_current_active_user, get_event_by_id_for_user
from src.db import models, schemas
from src.services.file_service import delete_file
from src.utils.logger import logger
from . import event_model_generator

router = APIRouter()

# =================================================================
# ROTAS PÚBLICAS (ATUALIZADAS)
# =================================================================

@router.get("/publicos", response_model=List[schemas.EventPublicList])
def read_public_events(db: Session = Depends(get_db)):
    """
    Retorna uma lista simplificada de eventos cuja data final (ou inicial, se não houver final)
    é hoje ou no futuro.
    """
    today = date.today()
    events = db.query(models.Evento).filter(
        (models.Evento.data_fim >= today) | (models.Evento.data_fim == None and models.Evento.data_inicio >= today)
    ).order_by(models.Evento.data_inicio.asc()).all()
    return events

@router.get("/publico/{link_unico}", response_model=schemas.EventPublicDetail)
def read_public_event_by_link(link_unico: str, db: Session = Depends(get_db)):
    """
    Busca os detalhes públicos de um evento pelo seu link único.
    """
    event = db.query(models.Evento).filter(models.Evento.link_unico == link_unico).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evento não encontrado")
    return event

# =================================================================
# ROTAS DO PROFESSOR/ADMINISTRADOR (ATUALIZADAS)
# =================================================================

@router.post("/", response_model=schemas.Event, status_code=status.HTTP_201_CREATED)
def create_event(
    event_in: schemas.EventCreate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_active_user)
):
    link_unico = str(uuid.uuid4())
    # Garante que data_fim seja nulo se não for fornecido
    event_data = event_in.model_dump()
    if 'data_fim' in event_data and not event_data['data_fim']:
        event_data['data_fim'] = None

    db_event = models.Evento(**event_data, usuario_id=current_user.id, link_unico=link_unico)
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    logger.info(f"Usuário '{current_user.email}' criou o evento '{db_event.titulo}' (ID: {db_event.id})")
    return db_event

@router.get("/", response_model=List[schemas.Event])
def read_events(
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_active_user)
):
    if current_user.tipo == 'admin':
        events = db.query(models.Evento).order_by(models.Evento.data_inicio.desc()).all()
    else:
        events = db.query(models.Evento).filter(models.Evento.usuario_id == current_user.id).order_by(models.Evento.data_inicio.desc()).all()

    for event in events:
        event.autorizacoes_count = len(event.autorizacoes)
    return events

@router.get("/{event_id}", response_model=schemas.Event)
def read_event(event: models.Evento = Depends(get_event_by_id_for_user)):
    return event

@router.put("/{event_id}", response_model=schemas.Event)
def update_event(
    event_in: schemas.EventUpdate,
    db_event: models.Evento = Depends(get_event_by_id_for_user),
    db: Session = Depends(get_db)
):
    update_data = event_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_event, key, value)
    
    db.commit()
    db.refresh(db_event)
    logger.info(f"Evento {db_event.id} atualizado.")
    return db_event

@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(
    db_event: models.Evento = Depends(get_event_by_id_for_user),
    db: Session = Depends(get_db)
):
    event_id = db_event.id
    for autorizacao in db_event.autorizacoes:
        if autorizacao.caminho_arquivo:
            try:
                delete_file(autorizacao.caminho_arquivo)
            except Exception as e:
                logger.error(f"Erro ao deletar arquivo {autorizacao.caminho_arquivo}: {e}")

    db.delete(db_event)
    db.commit()
    logger.warning(f"Evento {event_id} e todos os seus dados foram DELETADOS.")
    return

router.include_router(event_model_generator.router, prefix="/{event_id}/modelo")