# src/api/endpoints/events.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_
import uuid
from typing import List, Optional
from datetime import date

from src.api.deps import get_db, get_current_active_user, get_event_by_id_for_user
from src.db import models, schemas
from src.services.file_service import delete_file
from src.utils.logger import logger
from . import event_model_generator

router = APIRouter()

# =================================================================
# ROTAS PÚBLICAS (ATUALIZADAS COM FILTRO DE CAMPUS)
# =================================================================

@router.get("/publicos", response_model=List[schemas.EventPublicList])
def read_public_events(
    campus_id: Optional[int] = Query(None, description="Filtra eventos por ID do campus. Se não fornecido, retorna de todos os campi."),
    db: Session = Depends(get_db)
):
    """
    Retorna uma lista simplificada de eventos futuros.
    Pode ser filtrada por campus.
    """
    today = date.today()
    
    query = db.query(models.Evento).options(joinedload(models.Evento.campus)).filter(
        or_(
            models.Evento.data_fim >= today,
            and_(models.Evento.data_fim.is_(None), models.Evento.data_inicio >= today)
        )
    )

    # --- ALTERAÇÃO: Aplicar filtro de campus se fornecido ---
    if campus_id is not None:
        query = query.filter(models.Evento.campus_id == campus_id)

    events = query.order_by(models.Evento.data_inicio.asc()).all()
    # --- FIM DA ALTERAÇÃO ---
    
    return events


@router.get("/publico/{link_unico}", response_model=schemas.EventPublicDetail)
def read_public_event_by_link(link_unico: str, db: Session = Depends(get_db)):
    """
    Busca os detalhes públicos de um evento pelo seu link único.
    """
    event = db.query(models.Evento).options(joinedload(models.Evento.campus)).filter(models.Evento.link_unico == link_unico).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evento não encontrado")
    return event

# =================================================================
# ROTAS DO PROFESSOR/ADMINISTRADOR (ATUALIZADAS COM CAMPUS)
# =================================================================

@router.post("/", response_model=schemas.Event, status_code=status.HTTP_201_CREATED)
def create_event(
    event_in: schemas.EventCreate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_active_user)
):
    """
    Cria um novo evento. O evento será associado ao campus_id fornecido.
    """
    # --- ALTERAÇÃO: Validar Campus ---
    campus = db.query(models.Campus).filter(models.Campus.id == event_in.campus_id).first()
    if not campus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"O Campus com ID {event_in.campus_id} não foi encontrado.",
        )
    # --- FIM DA ALTERAÇÃO ---

    link_unico = str(uuid.uuid4())
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
    campus_id: Optional[int] = Query(None, description="Filtra eventos por ID do campus. Admin pode ver todos, professor vê apenas do seu campus por padrão."),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_active_user)
):
    """
    Lista eventos.
    - Admin: Pode filtrar por qualquer campus_id. Se nenhum for fornecido, vê todos.
    - Professor: Se campus_id for fornecido, filtra por ele. Se não, filtra pelos eventos do seu próprio campus.
    """
    query = db.query(models.Evento).options(joinedload(models.Evento.campus))

    if current_user.tipo == 'admin':
        if campus_id is not None:
            query = query.filter(models.Evento.campus_id == campus_id)
    else: # Se for professor
        # Professores só podem ver eventos do seu próprio campus, a menos que especifiquem um filtro (respeitando a regra inicial)
        target_campus_id = campus_id if campus_id is not None else current_user.campus_id
        
        if target_campus_id is None and campus_id is None:
             # Caso o professor não tenha campus e não filtre, não deve ver nenhum evento restrito
             # Ou podemos decidir mostrar todos. Mostrando nenhum parece mais seguro.
             query = query.filter(models.Evento.campus_id == None) # Retorna nada se campus_id for obrigatório
        else:
             query = query.filter(models.Evento.campus_id == target_campus_id)

    events = query.order_by(models.Evento.data_inicio.desc()).all()

    for event in events:
        event.autorizacoes_count = len(event.autorizacoes)
    return events


@router.get("/{event_id}", response_model=schemas.Event)
def read_event(event: models.Evento = Depends(get_event_by_id_for_user)):
    return event

@router.put("/{event_id}", response_model=schemas.Event)
def update_event(
    event_in: schemas.EventUpdate,
    db: Session = Depends(get_db), # Adicionado db
    db_event: models.Evento = Depends(get_event_by_id_for_user)
):
    """
    Atualiza um evento. O campus_id também pode ser atualizado.
    """
    update_data = event_in.model_dump(exclude_unset=True)

    # --- ALTERAÇÃO: Validar Campus se ele for alterado ---
    if "campus_id" in update_data:
        campus = db.query(models.Campus).filter(models.Campus.id == update_data["campus_id"]).first()
        if not campus:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"O Campus com ID {update_data['campus_id']} não foi encontrado.",
            )
    # --- FIM DA ALTERAÇÃO ---

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