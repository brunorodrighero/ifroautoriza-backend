from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import uuid

from src.api.deps import get_db, get_current_active_user
from src.db import models, schemas
from src.services.file_service import delete_file
from src.utils.logger import logger
from . import event_model_generator

router = APIRouter()

@router.post("/", response_model=schemas.Event, status_code=201)
def create_event(
    event_in: schemas.EventCreate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_active_user)
):
    link_unico = str(uuid.uuid4())
    db_event = models.Evento(**event_in.model_dump(), usuario_id=current_user.id, link_unico=link_unico)
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    logger.info(f"Usuário '{current_user.email}' criou o evento '{db_event.titulo}' (ID: {db_event.id})")
    return db_event

@router.get("/", response_model=list[schemas.Event])
def read_events(
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_active_user)
):
    events = db.query(models.Evento).filter(models.Evento.usuario_id == current_user.id).order_by(models.Evento.data_evento.desc()).all()
    for event in events:
        event.autorizacoes_count = len(event.autorizacoes)
    return events

@router.get("/{event_id}", response_model=schemas.Event)
def read_event(event_id: int, db: Session = Depends(get_db)):
    db_event = db.query(models.Evento).filter(models.Evento.id == event_id).first()
    if not db_event:
        raise HTTPException(status_code=404, detail="Evento não encontrado")
    return db_event

@router.put("/{event_id}", response_model=schemas.Event)
def update_event(
    event_id: int,
    event_in: schemas.EventUpdate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_active_user)
):
    db_event = db.query(models.Evento).filter(models.Evento.id == event_id).first()
    if not db_event:
        raise HTTPException(status_code=404, detail="Evento não encontrado")
    if db_event.usuario_id != current_user.id:
        raise HTTPException(status_code=403, detail="Não autorizado")

    update_data = event_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_event, key, value)
    
    db.commit()
    db.refresh(db_event)
    logger.info(f"Evento {event_id} atualizado pelo usuário '{current_user.email}'")
    return db_event

@router.delete("/{event_id}", status_code=204)
def delete_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_active_user)
):
    db_event = db.query(models.Evento).filter(models.Evento.id == event_id).first()
    if not db_event:
        raise HTTPException(status_code=404, detail="Evento não encontrado")
    if db_event.usuario_id != current_user.id:
        raise HTTPException(status_code=403, detail="Não autorizado")

    for autorizacao in db_event.autorizacoes:
        if autorizacao.caminho_arquivo:
            try:
                delete_file(autorizacao.caminho_arquivo)
            except Exception as e:
                logger.error(f"Erro ao deletar arquivo {autorizacao.caminho_arquivo}: {e}")

    db.delete(db_event)
    db.commit()
    logger.warning(f"Evento {event_id} e seus dados foram DELETADOS por '{current_user.email}'")
    return

router.include_router(event_model_generator.router, prefix="/{evento_id}/modelo")