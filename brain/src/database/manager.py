"""
VIRTUS Database Manager
=======================

Gerenciador de conexões e sessões do banco de dados.
Suporta PostgreSQL, SQLite e conexão assíncrona.
"""

import os
from typing import Optional, Generator, AsyncGenerator
from contextlib import contextmanager, asynccontextmanager
from pathlib import Path

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool, StaticPool
from sqlalchemy.exc import SQLAlchemyError

# Async support
try:
    from sqlalchemy.ext.asyncio import (
        create_async_engine, 
        AsyncSession, 
        async_sessionmaker
    )
    ASYNC_AVAILABLE = True
except ImportError:
    ASYNC_AVAILABLE = False

from .models import Base, create_all_tables
from ..core import VirtusLogger


class DatabaseConfig:
    """Configuração do banco de dados."""
    
    def __init__(
        self,
        # Conexão
        driver: str = "sqlite",  # sqlite, postgresql, postgresql+asyncpg
        host: str = "localhost",
        port: int = 5432,
        database: str = "virtus",
        username: str = "virtus",
        password: str = "",
        
        # Pool
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_timeout: int = 30,
        pool_recycle: int = 1800,
        
        # SQLite específico
        sqlite_path: Optional[str] = None,
        
        # Opções
        echo: bool = False,
        echo_pool: bool = False,
    ):
        self.driver = driver
        self.host = host
        self.port = port
        self.database = database
        self.username = username
        self.password = password
        
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.pool_recycle = pool_recycle
        
        self.sqlite_path = sqlite_path
        self.echo = echo
        self.echo_pool = echo_pool
    
    @property
    def connection_string(self) -> str:
        """Gera connection string."""
        if self.driver == "sqlite":
            path = self.sqlite_path or ":memory:"
            return f"sqlite:///{path}"
        
        if self.driver.startswith("postgresql"):
            return (
                f"{self.driver}://{self.username}:{self.password}"
                f"@{self.host}:{self.port}/{self.database}"
            )
        
        raise ValueError(f"Driver não suportado: {self.driver}")
    
    @classmethod
    def from_env(cls) -> 'DatabaseConfig':
        """Cria config a partir de variáveis de ambiente."""
        return cls(
            driver=os.getenv("DB_DRIVER", "sqlite"),
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            database=os.getenv("DB_NAME", "virtus"),
            username=os.getenv("DB_USER", "virtus"),
            password=os.getenv("DB_PASSWORD", ""),
            sqlite_path=os.getenv("DB_SQLITE_PATH"),
            echo=os.getenv("DB_ECHO", "false").lower() == "true",
        )
    
    @classmethod
    def sqlite_default(cls, data_dir: Optional[str] = None) -> 'DatabaseConfig':
        """Config padrão para SQLite local."""
        if data_dir:
            db_path = Path(data_dir) / "virtus.db"
        else:
            db_path = Path(__file__).parent.parent.parent / "data" / "brain" / "virtus.db"
        
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        return cls(
            driver="sqlite",
            sqlite_path=str(db_path),
            echo=False,
        )


class DatabaseManager:
    """
    Gerenciador de conexões do banco de dados.
    
    Suporta:
    - SQLite para desenvolvimento local
    - PostgreSQL para produção
    - Conexões síncronas e assíncronas
    - Pool de conexões
    - Migrações automáticas
    """
    
    _instance: Optional['DatabaseManager'] = None
    
    def __new__(cls, config: Optional[DatabaseConfig] = None, force_new: bool = False):
        if cls._instance is None or force_new:
            if cls._instance is not None:
                cls._instance.close()
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config: Optional[DatabaseConfig] = None, force_new: bool = False):
        if self._initialized and not force_new:
            return
        
        self._initialized = True
        self.logger = VirtusLogger.get_logger("database")
        
        self.config = config or DatabaseConfig.sqlite_default()
        
        self._engine = None
        self._async_engine = None
        self._session_factory = None
        self._async_session_factory = None
        
        self._initialize_engine()
    
    def _initialize_engine(self) -> None:
        """Inicializa o engine de banco de dados."""
        conn_string = self.config.connection_string
        
        # Engine síncrono
        if self.config.driver == "sqlite":
            # SQLite precisa de config especial para threads
            self._engine = create_engine(
                conn_string,
                echo=self.config.echo,
                poolclass=StaticPool,
                connect_args={"check_same_thread": False}
            )
            
            # Habilita foreign keys no SQLite
            @event.listens_for(self._engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()
        else:
            # PostgreSQL com pool
            self._engine = create_engine(
                conn_string,
                echo=self.config.echo,
                echo_pool=self.config.echo_pool,
                poolclass=QueuePool,
                pool_size=self.config.pool_size,
                max_overflow=self.config.max_overflow,
                pool_timeout=self.config.pool_timeout,
                pool_recycle=self.config.pool_recycle,
            )
        
        # Session factory
        self._session_factory = sessionmaker(
            bind=self._engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False
        )
        
        # Engine assíncrono (se PostgreSQL com asyncpg)
        if ASYNC_AVAILABLE and "asyncpg" in self.config.driver:
            self._async_engine = create_async_engine(
                conn_string,
                echo=self.config.echo,
                pool_size=self.config.pool_size,
                max_overflow=self.config.max_overflow,
            )
            
            self._async_session_factory = async_sessionmaker(
                bind=self._async_engine,
                class_=AsyncSession,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False
            )
        
        self.logger.info(f"Database engine initialized: {self.config.driver}")
    
    def create_tables(self) -> None:
        """Cria todas as tabelas."""
        create_all_tables(self._engine)
        self.logger.info("Database tables created")
    
    def drop_tables(self) -> None:
        """Remove todas as tabelas (CUIDADO!)."""
        Base.metadata.drop_all(self._engine)
        self.logger.warning("Database tables dropped!")
    
    @property
    def engine(self):
        """Retorna o engine SQLAlchemy."""
        return self._engine
    
    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """
        Context manager para sessão síncrona.
        
        Uso:
            with db.session() as session:
                session.add(trade)
                session.commit()
        """
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"Database error: {e}")
            raise
        finally:
            session.close()
    
    @asynccontextmanager
    async def async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Context manager para sessão assíncrona.
        
        Uso:
            async with db.async_session() as session:
                session.add(trade)
                await session.commit()
        """
        if not self._async_session_factory:
            raise RuntimeError("Async sessions not available. Use postgresql+asyncpg driver.")
        
        session = self._async_session_factory()
        try:
            yield session
            await session.commit()
        except SQLAlchemyError as e:
            await session.rollback()
            self.logger.error(f"Database error: {e}")
            raise
        finally:
            await session.close()
    
    def get_session(self) -> Session:
        """Retorna uma nova sessão (deve ser fechada manualmente)."""
        return self._session_factory()
    
    def execute(self, query: str, params: dict = None) -> list:
        """Executa query SQL raw."""
        with self.session() as session:
            result = session.execute(text(query), params or {})
            return result.fetchall()
    
    def health_check(self) -> bool:
        """Verifica se a conexão está funcionando."""
        try:
            with self.session() as session:
                session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            self.logger.error(f"Database health check failed: {e}")
            return False
    
    def get_stats(self) -> dict:
        """Retorna estatísticas do pool de conexões."""
        if not self._engine.pool:
            return {}
        
        pool = self._engine.pool
        return {
            'pool_size': pool.size(),
            'checked_in': pool.checkedin(),
            'checked_out': pool.checkedout(),
            'overflow': pool.overflow(),
        }
    
    def close(self) -> None:
        """Fecha todas as conexões."""
        if self._engine:
            self._engine.dispose()
            self.logger.info("Database connections closed")
    
    async def close_async(self) -> None:
        """Fecha conexões assíncronas."""
        if self._async_engine:
            await self._async_engine.dispose()
    
    def __del__(self):
        self.close()


# Instância global (singleton)
def get_database(config: Optional[DatabaseConfig] = None) -> DatabaseManager:
    """Obtém instância do DatabaseManager."""
    return DatabaseManager(config)
