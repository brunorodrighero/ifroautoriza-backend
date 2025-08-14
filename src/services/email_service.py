# src/services/email_service.py
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path
from sqlalchemy.orm import joinedload

from src.core.config import settings
from src.utils.logger import logger
from src.db.models import Autorizacao, Evento, Usuario
from src.db import models
from src.db.session import SessionLocal

class EmailService:
    conf = ConnectionConfig(
        MAIL_USERNAME=settings.SMTP_USER,
        MAIL_PASSWORD=settings.SMTP_PASS,
        MAIL_FROM=settings.FROM_EMAIL,
        MAIL_PORT=settings.SMTP_PORT,
        MAIL_SERVER=settings.SMTP_HOST,
        MAIL_STARTTLS=True,
        MAIL_SSL_TLS=False,
        USE_CREDENTIALS=True,
        VALIDATE_CERTS=True
    )
    
    template_env = Environment(
        loader=FileSystemLoader(Path(__file__).parent / 'email_templates'),
        autoescape=select_autoescape(['html'])
    )

    @classmethod
    async def send_email(cls, subject: str, recipients: list, template_name: str, template_body: dict):
        try:
            valid_recipients = [email for email in recipients if email]
            if not valid_recipients:
                logger.warning(f"Nenhum destinatário válido para o email '{subject}'. Pulando envio.")
                return
            template = cls.template_env.get_template(template_name)
            html_content = template.render(template_body)
            message = MessageSchema(
                subject=subject,
                recipients=valid_recipients,
                body=html_content,
                subtype="html"
            )
            fm = FastMail(cls.conf)
            await fm.send_message(message)
            logger.info(f"Email '{subject}' enviado para {valid_recipients}")
        except Exception as e:
            logger.error(f"Falha catastrófica ao enviar email '{subject}' para {recipients}: {e}")

    # --- FUNÇÕES AUXILIARES DE BUSCA NO DB ---
    @classmethod
    def get_autorizacao_from_db(cls, autorizacao_id: int):
        db = SessionLocal()
        try:
            return db.query(Autorizacao).options(
                joinedload(Autorizacao.evento).joinedload(models.Evento.criador)
            ).filter(Autorizacao.id == autorizacao_id).first()
        finally:
            db.close()

    @classmethod
    def get_user_from_db(cls, user_id: int):
        """Função auxiliar para buscar um usuário fresco do DB."""
        db = SessionLocal()
        try:
            return db.query(Usuario).filter(Usuario.id == user_id).first()
        finally:
            db.close()

    # --- MÉTODOS DE ENVIO DE E-MAIL ---
    @classmethod
    async def send_verification_code(cls, user_id: int, subject: str):
        user = cls.get_user_from_db(user_id)
        if not user: return
        recipients = [user.email]
        template_body = {
            "assunto": subject,
            "nome_usuario": user.nome,
            "codigo": user.codigo_verificacao
        }
        await cls.send_email(subject, recipients, "codigo_verificacao.html", template_body)

    @classmethod
    async def send_submission_confirmation_to_student(cls, autorizacao_id: int):
        autorizacao = cls.get_autorizacao_from_db(autorizacao_id)
        if not autorizacao: return
        subject = f"Confirmação de Recebimento - Evento: {autorizacao.evento.titulo}"
        recipients = [autorizacao.email_aluno, autorizacao.email_responsavel]
        template_body = {"aluno": autorizacao, "evento": autorizacao.evento}
        await cls.send_email(subject, recipients, "confirmacao_submissao.html", template_body)

    @classmethod
    async def notify_teacher_of_new_submission(cls, autorizacao_id: int):
        autorizacao = cls.get_autorizacao_from_db(autorizacao_id)
        if not autorizacao: return
        professor = autorizacao.evento.criador
        subject = f"Nova Autorização Submetida para o Evento: {autorizacao.evento.titulo}"
        recipients = [professor.email]
        template_body = {"aluno": autorizacao, "evento": autorizacao.evento, "professor": professor}
        await cls.send_email(subject, recipients, "notificacao_professor.html", template_body)

    @classmethod
    async def send_approval_notification_to_student(cls, autorizacao_id: int):
        autorizacao = cls.get_autorizacao_from_db(autorizacao_id)
        if not autorizacao: return
        subject = f"✅ Autorização APROVADA - Evento: {autorizacao.evento.titulo}"
        recipients = [autorizacao.email_aluno, autorizacao.email_responsavel]
        template_body = {"aluno": autorizacao, "evento": autorizacao.evento}
        await cls.send_email(subject, recipients, "confirmacao_aprovacao.html", template_body)

    @classmethod
    async def send_rejection_notification_to_student(cls, autorizacao_id: int, motivo: str = ""):
        autorizacao = cls.get_autorizacao_from_db(autorizacao_id)
        if not autorizacao: return
        subject = f"❌ Autorização Rejeitada - Evento: {autorizacao.evento.titulo}"
        recipients = [autorizacao.email_aluno, autorizacao.email_responsavel]
        template_body = {
            "aluno": autorizacao,
            "evento": autorizacao.evento,
            "motivo": motivo or "Por favor, entre em contato com o professor responsável para mais detalhes."
        }
        await cls.send_email(subject, recipients, "notificacao_rejeicao.html", template_body)
