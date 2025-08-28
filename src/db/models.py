# src/db/models.py

from sqlalchemy import (Column, Integer, String, Boolean, DateTime, Date,
                        ForeignKey, Enum, Text, UniqueConstraint)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

# --- NOVA TABELA ---
class Campus(Base):
    __tablename__ = "Campi"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(255), unique=True, index=True, nullable=False)
    usuarios = relationship("Usuario", back_populates="campus")
    eventos = relationship("Evento", back_populates="campus")


class Usuario(Base):
    __tablename__ = "Usuarios"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(255), nullable=False)
    email = Column(String(320), unique=True, index=True, nullable=False)
    senha_hash = Column(String(255), nullable=True)
    tipo = Column(Enum('professor', 'instituicao', 'admin', name='user_tipo'), default='professor', nullable=False)
    ativo = Column(Boolean, default=False)
    ultimo_login = Column(DateTime)
    criado_em = Column(DateTime, server_default=func.now())
    
    codigo_verificacao = Column(String(6), nullable=True)
    codigo_verificacao_expira_em = Column(DateTime, nullable=True)
    campus_id = Column(Integer, ForeignKey("Campi.id"), nullable=True) 
    campus = relationship("Campus", back_populates="usuarios")
    
    eventos = relationship("Evento", back_populates="criador", cascade="all, delete-orphan")


class Evento(Base):
    __tablename__ = "Eventos"
    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String(255), nullable=False)
    descricao = Column(Text, nullable=True)
    data_inicio = Column(Date, nullable=False)
    data_fim = Column(Date, nullable=True)
    horario = Column(String(50), nullable=True) 
    local_evento = Column(String(500), nullable=True)
    observacoes = Column(Text, nullable=True)
    link_unico = Column(String(100), unique=True, index=True, nullable=False)
    usuario_id = Column(Integer, ForeignKey("Usuarios.id"), nullable=False)
    criado_em = Column(DateTime, server_default=func.now())
    campus_id = Column(Integer, ForeignKey("Campi.id"), nullable=False)
    campus = relationship("Campus", back_populates="eventos")    
    criador = relationship("Usuario", back_populates="eventos")
    autorizacoes = relationship("Autorizacao", back_populates="evento", cascade="all, delete-orphan")


class Autorizacao(Base):
    __tablename__ = "Autorizacoes"
    id = Column(Integer, primary_key=True, index=True)
    nome_aluno = Column(String(255), nullable=False)
    matricula_aluno = Column(String(50), nullable=True)
    email_aluno = Column(String(320), nullable=True)
    nome_responsavel = Column(String(255), nullable=True)
    email_responsavel = Column(String(320), nullable=True)
    caminho_arquivo = Column(String(500), nullable=True)
    nome_arquivo_original = Column(String(255), nullable=True)
    tamanho_arquivo = Column(Integer, nullable=True)
    tipo_arquivo = Column(String(50), nullable=True)
    status = Column(Enum('pré-cadastrado', 'submetido', 'aprovado', 'rejeitado', name='auth_status'), default='pré-cadastrado', nullable=False)
    evento_id = Column(Integer, ForeignKey("Eventos.id"), nullable=False)
    submetido_em = Column(DateTime, server_default=func.now())
    evento = relationship("Evento", back_populates="autorizacoes")
    presencas = relationship("Presenca", back_populates="autorizacao", cascade="all, delete-orphan")


class Presenca(Base):
    __tablename__ = "Presencas"
    id = Column(Integer, primary_key=True, index=True)
    autorizacao_id = Column(Integer, ForeignKey("Autorizacoes.id"), nullable=False)
    data_presenca = Column(Date, nullable=False)
    presente_ida = Column(Boolean, default=False, nullable=False)
    presente_volta = Column(Boolean, default=False, nullable=False) 
    autorizacao = relationship("Autorizacao", back_populates="presencas")
    __table_args__ = (UniqueConstraint('autorizacao_id', 'data_presenca', name='_autorizacao_data_uc'),)