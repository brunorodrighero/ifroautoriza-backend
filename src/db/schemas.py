# src/db/schemas.py
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, Literal, List
from datetime import datetime, date
import re

# --- Schemas de Usuário e Autenticação (Com adição para Update) ---
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
    ativo: Optional[bool] = True

# --- NOVO SCHEMA PARA ATUALIZAÇÃO DE USUÁRIO ---
class UserUpdate(BaseModel):
    nome: Optional[str] = None
    email: Optional[EmailStr] = None
    tipo: Optional[Literal['professor', 'admin']] = None
    ativo: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=8)

class User(UserBase):
    id: int
    tipo: str
    ativo: bool
    class Config:
        from_attributes = True

# --- Schemas de Evento (Atualizados) ---
class EventBase(BaseModel):
    titulo: str = Field(..., min_length=3, max_length=255)
    descricao: Optional[str] = None
    # --- ALTERADO ---
    data_inicio: date
    data_fim: Optional[date] = None
    horario: Optional[str] = Field(None, max_length=50)
    # --- FIM DA ALTERAÇÃO ---
    local_evento: Optional[str] = Field(None, max_length=500)
    observacoes: Optional[str] = None

    @validator('data_fim', always=True)
    def validate_date_range(cls, v, values):
        if v and 'data_inicio' in values and v < values['data_inicio']:
            raise ValueError('A data final não pode ser anterior à data inicial.')
        return v

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
    # --- ALTERADO ---
    data_inicio: date
    data_fim: Optional[date] = None
    horario: Optional[str] = None
    # --- FIM DA ALTERAÇÃO ---
    local_evento: Optional[str] = None
    link_unico: str
    class Config:
        from_attributes = True

class EventPublicDetail(BaseModel):
    id: int
    titulo: str
    descricao: Optional[str] = None
    # --- ALTERADO ---
    data_inicio: date
    data_fim: Optional[date] = None
    horario: Optional[str] = None
    # --- FIM DA ALTERAÇÃO ---
    local_evento: Optional[str] = None
    class Config:
        from_attributes = True

# --- Schemas de Presença (NOVOS) ---
class PresencaBase(BaseModel):
    data_presenca: date
    presente_ida: bool = False
    presente_volta: bool = False

class Presenca(PresencaBase):
    id: int
    autorizacao_id: int
    class Config:
        from_attributes = True

# --- Schemas de Autorização (Atualizados) ---
class AuthorizationPreRegister(BaseModel):
    nome_aluno: str
    matricula_aluno: Optional[str] = None

    @validator('matricula_aluno')
    def validate_matricula(cls, v):
        if v:
            cleaned = re.sub(r'\D', '', v)
            if len(cleaned) < 13:
                raise ValueError('A matrícula, se informada, deve conter pelo menos 13 dígitos.')
        return v

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
    submetido_em: datetime
    caminho_arquivo: Optional[str] = None
    nome_arquivo_original: Optional[str] = None
    # --- NOVO CAMPO ---
    presencas: List[Presenca] = []
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

# --- NOVO SCHEMA PARA PRESENÇA ---
class PresencaUpdate(BaseModel):
    presente_ida: Optional[bool] = None
    presente_volta: Optional[bool] = None