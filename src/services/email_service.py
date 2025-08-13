# src/services/email_service.py
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path

from src.core.config import settings
from src.utils.logger import logger
from src.db.models import Autorizacao, Evento, Usuario

class EmailService:
    """
    Serviço centralizado para o envio de todos os emails transacionais da aplicação.
    """
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
    
    # Aponta para a pasta que conterá os arquivos .html dos emails.
    template_env = Environment(
        loader=FileSystemLoader(Path(__file__).parent / 'email_templates'),
        autoescape=select_autoescape(['html'])
    )

    @classmethod
    async def send_email(cls, subject: str, recipients: list, template_name: str, template_body: dict):
        """
        Método base genérico para enviar um email usando um template.
        """
        try:
            # Filtra destinatários nulos ou vazios
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

    @classmethod
    async def send_submission_confirmation_to_student(cls, autorizacao: Autorizacao):
        """
        Enviado para o aluno e seu responsável após a submissão bem-sucedida do formulário.
        """
        subject = f"Confirmação de Recebimento - Evento: {autorizacao.evento.titulo}"
        recipients = [autorizacao.email_aluno, autorizacao.email_responsavel]
        template_body = {
            "aluno": autorizacao,
            "evento": autorizacao.evento
        }
        await cls.send_email(subject, recipients, "confirmacao_submissao.html", template_body)

    @classmethod
    async def notify_teacher_of_new_submission(cls, autorizacao: Autorizacao):
        """
        Enviado para o professor responsável pelo evento quando uma nova autorização é submetida.
        """
        professor = autorizacao.evento.criador
        subject = f"Nova Autorização Submetida para o Evento: {autorizacao.evento.titulo}"
        recipients = [professor.email]
        template_body = {
            "aluno": autorizacao,
            "evento": autorizacao.evento,
            "professor": professor
        }
        await cls.send_email(subject, recipients, "notificacao_professor.html", template_body)

    @classmethod
    async def send_approval_notification_to_student(cls, autorizacao: Autorizacao):
        """
        Enviado para o aluno e seu responsável quando a autorização é APROVADA.
        """
        subject = f"✅ Autorização APROVADA - Evento: {autorizacao.evento.titulo}"
        recipients = [autorizacao.email_aluno, autorizacao.email_responsavel]
        template_body = {
            "aluno": autorizacao,
            "evento": autorizacao.evento
        }
        await cls.send_email(subject, recipients, "confirmacao_aprovacao.html", template_body)

    @classmethod
    async def send_rejection_notification_to_student(cls, autorizacao: Autorizacao, motivo: str = ""):
        """
        Enviado para o aluno e seu responsável quando a autorização é REJEITADA.
        """
        subject = f"❌ Autorização Rejeitada - Evento: {autorizacao.evento.titulo}"
        recipients = [autorizacao.email_aluno, autorizacao.email_responsavel]
        template_body = {
            "aluno": autorizacao,
            "evento": autorizacao.evento,
            "motivo": motivo or "Por favor, entre em contato com o professor responsável para mais detalhes."
        }
        await cls.send_email(subject, recipients, "notificacao_rejeicao.html", template_body)