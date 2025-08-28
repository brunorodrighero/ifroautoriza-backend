# src/db/schemas.py
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, Literal, List
from datetime import datetime, date
import re

# --- Schemas de Campus (Sem alterações) ---
class CampusBase(BaseModel):
    nome: str = Field(..., min_length=3, max_length=255)

class CampusCreate(CampusBase):
    pass

class CampusUpdate(CampusBase):
    pass

class Campus(CampusBase):
    id: int
    class Config:
        from_attributes = True


# --- Schemas de Usuário e Autenticação (Sem alterações) ---
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
    campus_id: Optional[int] = None

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

class UserAdminCreate(UserCreate):
    tipo: Literal['professor', 'admin'] = 'professor'
    ativo: Optional[bool] = True

class UserUpdate(BaseModel):
    nome: Optional[str] = None
    email: Optional[EmailStr] = None
    tipo: Optional[Literal['professor', 'admin']] = None
    ativo: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=8)
    campus_id: Optional[int] = None

class User(UserBase):
    id: int
    tipo: str
    ativo: bool
    campus: Optional[Campus] = None
    class Config:
        from_attributes = True


# --- Schemas de Evento (COM A CORREÇÃO FINAL) ---
class EventBase(BaseModel):
    titulo: str = Field(..., min_length=3, max_length=255)
    descricao: Optional[str] = None
    data_inicio: date
    data_fim: Optional[date] = None
    horario: Optional[str] = Field(None, max_length=50)
    local_evento: Optional[str] = Field(None, max_length=500)
    observacoes: Optional[str] = None
    # Este campus_id continua obrigatório, o que é correto para a CRIAÇÃO de eventos
    campus_id: int 

    @validator('data_fim', always=True)
    def validate_date_range(cls, v, values):
        if v and 'data_inicio' in values and v < values['data_inicio']:
            raise ValueError('A data final não pode ser anterior à data inicial.')
        return v

class EventCreate(EventBase):
    pass

class EventUpdate(BaseModel): # Não herda mais de EventBase para ter total controle
    titulo: Optional[str] = Field(None, min_length=3, max_length=255)
    descricao: Optional[str] = None
    data_inicio: Optional[date] = None
    data_fim: Optional[date] = None
    horario: Optional[str] = Field(None, max_length=50)
    local_evento: Optional[str] = Field(None, max_length=500)
    observacoes: Optional[str] = None
    campus_id: Optional[int] = None # Opcional na atualização

class Event(EventBase):
    id: int
    link_unico: str
    usuario_id: int
    autorizacoes_count: int = 0
    
    # --- CORREÇÃO AQUI ---
    # Sobrescrevemos o campus_id de EventBase para que ele seja opcional na resposta
    campus_id: Optional[int] = None 
    campus: Optional[Campus] = None
    class Config:
        from_attributes = True

class EventPublicList(BaseModel):
    titulo: str
    data_inicio: date
    data_fim: Optional[date] = None
    horario: Optional[str] = None
    local_evento: Optional[str] = None
    link_unico: str
    campus: Optional[Campus] = None 
    class Config:
        from_attributes = True

class EventPublicDetail(BaseModel):
    id: int
    titulo: str
    descricao: Optional[str] = None
    data_inicio: date
    data_fim: Optional[date] = None
    horario: Optional[str] = None
    local_evento: Optional[str] = None
    campus: Optional[Campus] = None
    class Config:
        from_attributes = True


# --- Schemas de Presença (Sem alterações) ---
class PresencaBase(BaseModel):
    data_presenca: date
    presente_ida: bool = False
    presente_volta: bool = False

class Presenca(PresencaBase):
    id: int
    autorizacao_id: int
    class Config:
        from_attributes = True

# --- Schemas de Autorização (Sem alterações) ---
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

class PresencaUpdate(BaseModel):
    presente_ida: Optional[bool] = None
    presente_volta: Optional[bool] = None