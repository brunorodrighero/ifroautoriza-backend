# src/db/schemas.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Literal
from datetime import datetime

# --- NOVOS SCHEMAS PARA CADASTRO E RESET ---
class ProfessorRegisterRequest(BaseModel):
    email: EmailStr
    nome: str

class RequestCode(BaseModel):
    email: EmailStr

class VerifyCode(BaseModel):
    email: EmailStr
    codigo: str = Field(..., min_length=4, max_length=4)

class SetPassword(BaseModel):
    email: EmailStr
    codigo: str
    password: str = Field(..., min_length=8)

# --- Schemas de Token e Usuário ---
class Token(BaseModel):
    access_token: str
    token_type: str

class UserBase(BaseModel):
    email: EmailStr
    nome: str

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

class UserAdminCreate(UserCreate):
    tipo: Literal['professor', 'admin'] = 'professor'

class User(UserBase):
    id: int
    tipo: str
    ativo: bool
    class Config:
        from_attributes = True

# ... (resto dos schemas existentes) ...
class EventBase(BaseModel):
    titulo: str = Field(..., min_length=3, max_length=255)
    descricao: Optional[str] = None
    data_evento: datetime
    local_evento: Optional[str] = Field(None, max_length=500)
    observacoes: Optional[str] = None
class EventCreate(EventBase):
    pass
class EventUpdate(EventBase):
    pass
class Event(EventBase):
    id: int
    link_unico: str
    usuario_id: int
    autorizacoes_count: int = 0
    class Config:
        from_attributes = True
class EventPublicList(BaseModel):
    titulo: str
    data_evento: datetime
    local_evento: Optional[str] = None
    link_unico: str
    class Config:
        from_attributes = True
class EventPublicDetail(BaseModel):
    id: int
    titulo: str
    descricao: Optional[str] = None
    data_evento: datetime
    local_evento: Optional[str] = None
    class Config:
        from_attributes = True
class AuthorizationPreRegister(BaseModel):
    nome_aluno: str
    matricula_aluno: Optional[str] = None
class AuthorizationStudentUpdate(BaseModel):
    email_aluno: EmailStr
    nome_responsavel: str
    email_responsavel: EmailStr
class AuthorizationForProfessor(BaseModel):
    id: int
    nome_aluno: str
    matricula_aluno: Optional[str]
    email_aluno: Optional[EmailStr]
    nome_responsavel: Optional[str]
    email_responsavel: Optional[EmailStr]
    status: str
    presente: bool
    submetido_em: datetime
    caminho_arquivo: Optional[str] = None
    nome_arquivo_original: Optional[str] = None
    class Config:
        from_attributes = True
class AuthorizationForStudentList(BaseModel):
    id: int
    nome_aluno: str
    class Config:
        from_attributes = True
class StatusUpdate(BaseModel):
    status: str
    motivo: Optional[str] = None
