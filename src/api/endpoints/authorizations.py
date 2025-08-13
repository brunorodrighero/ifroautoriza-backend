# src/api/endpoints/authorizations.py
from fastapi import (APIRouter, Depends, HTTPException, BackgroundTasks, 
                     UploadFile, File, Form, status)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pathlib import Path
from typing import List

from src.api.deps import get_db, get_current_active_user
from src.db import models, schemas
from src.services.email_service import EmailService
from src.services.file_service import save_upload_file
from src.utils.logger import logger
from src.core.config import settings

router = APIRouter()

# =================================================================
# ROTAS DO PROFESSOR/ADMINISTRADOR (REQUEREM AUTENTICAÇÃO)
# =================================================================

@router.post("/eventos/{evento_id}/pre-cadastrar", response_model=schemas.AuthorizationForProfessor, status_code=status.HTTP_201_CREATED)
def preregister_student(
    evento_id: int,
    student_in: schemas.AuthorizationPreRegister,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_active_user)
):
    """Pré-cadastra um aluno em um evento, inserindo apenas nome e matrícula."""
    db_event = db.query(models.Evento).filter(models.Evento.id == evento_id, models.Evento.usuario_id == current_user.id).first()
    if not db_event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evento não encontrado ou não pertence a você.")
    
    db_auth = models.Autorizacao(**student_in.model_dump(), evento_id=evento_id, status='pré-cadastrado')
    db.add(db_auth)
    db.commit()
    db.refresh(db_auth)
    logger.info(f"Aluno '{student_in.nome_aluno}' pré-cadastrado no evento {evento_id} pelo usuário '{current_user.email}'.")
    return db_auth

@router.get("/eventos/{evento_id}/autorizacoes", response_model=List[schemas.AuthorizationForProfessor])
def get_event_authorizations(
    evento_id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_active_user)
):
    """Busca todas as autorizações (em qualquer status) de um evento específico."""
    event = db.query(models.Evento).filter(models.Evento.id == evento_id).first()
    if not event or event.usuario_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evento não encontrado ou não autorizado.")
    return sorted(event.autorizacoes, key=lambda x: x.nome_aluno)

@router.patch("/{autorizacao_id}/status", response_model=schemas.AuthorizationForProfessor)
async def update_authorization_status(
    autorizacao_id: int,
    status_update: schemas.StatusUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_active_user)
):
    """UNIFICADO: Aprova ou rejeita uma autorização e dispara o e-mail correspondente."""
    autorizacao = db.query(models.Autorizacao).filter(models.Autorizacao.id == autorizacao_id).first()
    if not autorizacao:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Autorização não encontrada")
    if autorizacao.evento.usuario_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Ação não permitida")
    if status_update.status not in ['aprovado', 'rejeitado']:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Status inválido. Use 'aprovado' ou 'rejeitado'.")

    autorizacao.status = status_update.status
    db.commit()
    db.refresh(autorizacao)
    
    if autorizacao.status == 'aprovado':
        background_tasks.add_task(EmailService.send_approval_notification_to_student, autorizacao)
        logger.info(f"Autorização {autorizacao.id} APROVADA pelo usuário '{current_user.email}'.")
    elif autorizacao.status == 'rejeitado':
        background_tasks.add_task(EmailService.send_rejection_notification_to_student, autorizacao, status_update.motivo)
        logger.warning(f"Autorização {autorizacao.id} REJEITADA pelo usuário '{current_user.email}'.")

    return autorizacao

@router.patch("/{autorizacao_id}/presenca", response_model=schemas.AuthorizationForProfessor)
def mark_attendance(
    autorizacao_id: int,
    presente: bool,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_active_user)
):
    """Marca a presença de um aluno em um evento."""
    autorizacao = db.query(models.Autorizacao).filter(models.Autorizacao.id == autorizacao_id).first()
    if not autorizacao:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Autorização não encontrada")
    if autorizacao.evento.usuario_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Ação não permitida")
    if autorizacao.status != 'aprovado':
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Apenas autorizações aprovadas podem ter a presença marcada.")
    
    autorizacao.presente = presente
    db.commit()
    db.refresh(autorizacao)
    logger.info(f"Presença do aluno '{autorizacao.nome_aluno}' (Auth ID: {autorizacao_id}) marcada como {presente}.")
    return autorizacao

@router.get("/{autorizacao_id}/arquivo", response_class=FileResponse)
def get_authorization_file(
    autorizacao_id: int,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_active_user)
):
    """Permite que o professor baixe o arquivo de autorização enviado pelo aluno."""
    autorizacao = db.query(models.Autorizacao).filter(models.Autorizacao.id == autorizacao_id).first()
    if not autorizacao:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Autorização não encontrada")
    if autorizacao.evento.usuario_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado")
    
    if not autorizacao.caminho_arquivo:
        raise HTTPException(status_code=404, detail="Nenhum arquivo associado a esta autorização.")
        
    file_path = Path(settings.UPLOAD_DIRECTORY) / autorizacao.caminho_arquivo
    if not file_path.is_file():
        logger.error(f"Arquivo não encontrado no disco: {file_path}, mas referenciado no DB.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Arquivo não encontrado no servidor.")
        
    return FileResponse(path=file_path, filename=autorizacao.nome_arquivo_original, media_type=autorizacao.tipo_arquivo)

# =================================================================
# ROTAS PÚBLICAS (NÃO REQUEREM AUTENTICAÇÃO)
# =================================================================

@router.get("/eventos/{evento_id}/pre-cadastrados", response_model=List[schemas.AuthorizationForStudentList])
def get_preregistered_students(evento_id: int, db: Session = Depends(get_db)):
    """Retorna a lista de alunos pré-cadastrados para o formulário público."""
    students = db.query(models.Autorizacao).filter(
        models.Autorizacao.evento_id == evento_id,
        models.Autorizacao.status == 'pré-cadastrado'
    ).order_by(models.Autorizacao.nome_aluno).all()
    return students

@router.put("/{autorizacao_id}/submeter", response_model=schemas.AuthorizationForProfessor)
async def student_submit_authorization(
    autorizacao_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    email_aluno: str = Form(...),
    nome_responsavel: str = Form(...),
    email_responsavel: str = Form(...),
    arquivo: UploadFile = File(...)
):
    """Recebe os dados e o arquivo do aluno, atualizando o registro pré-cadastrado."""
    db_auth = db.query(models.Autorizacao).filter(models.Autorizacao.id == autorizacao_id).first()
    if not db_auth or db_auth.status != 'pré-cadastrado':
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cadastro de aluno não encontrado ou já submetido.")

    saved_file_path = await save_upload_file(arquivo)

    db_auth.email_aluno = email_aluno
    db_auth.nome_responsavel = nome_responsavel
    db_auth.email_responsavel = email_responsavel
    db_auth.caminho_arquivo = saved_file_path
    db_auth.nome_arquivo_original = arquivo.filename
    db_auth.tamanho_arquivo = arquivo.size
    db_auth.tipo_arquivo = arquivo.content_type
    db_auth.status = 'submetido'
    
    db.commit()
    db.refresh(db_auth)
    logger.info(f"Submissão recebida para o aluno '{db_auth.nome_aluno}' (Auth ID: {db_auth.id}).")
    
    # Dispara os emails de notificação
    background_tasks.add_task(EmailService.send_submission_confirmation_to_student, db_auth)
    background_tasks.add_task(EmailService.notify_teacher_of_new_submission, db_auth)
    
    return db_auth