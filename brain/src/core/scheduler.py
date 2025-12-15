"""
VIRTUS Core - Scheduler
=======================

Sistema de agendamento de tarefas.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Callable, Dict, Optional, Any, List, Coroutine
from dataclasses import dataclass, field
from enum import Enum
import functools

from .logger import get_logger

logger = get_logger("scheduler")


class TaskStatus(Enum):
    """Status de uma tarefa agendada"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class ScheduledTask:
    """Representa uma tarefa agendada"""
    id: str
    name: str
    callback: Callable
    interval_seconds: Optional[float] = None
    run_at: Optional[datetime] = None
    repeat: bool = False
    
    # Status
    status: TaskStatus = TaskStatus.PENDING
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    error_count: int = 0
    last_error: Optional[str] = None
    
    # Handle da task asyncio
    _task: Optional[asyncio.Task] = field(default=None, repr=False)


class Scheduler:
    """
    Gerenciador de tarefas agendadas.
    
    Suporta:
    - Tarefas periódicas (intervalo fixo)
    - Tarefas agendadas (horário específico)
    - Tarefas únicas ou repetitivas
    """
    
    def __init__(self):
        self._tasks: Dict[str, ScheduledTask] = {}
        self._running = False
        self._task_counter = 0
    
    def _generate_task_id(self, name: str) -> str:
        """Gera ID único para tarefa"""
        self._task_counter += 1
        return f"{name}_{self._task_counter}"
    
    def add_periodic_task(
        self,
        name: str,
        callback: Callable[[], Coroutine],
        interval_seconds: float,
        start_immediately: bool = False
    ) -> str:
        """
        Adiciona tarefa periódica.
        
        Args:
            name: Nome da tarefa
            callback: Função async a executar
            interval_seconds: Intervalo entre execuções
            start_immediately: Se deve executar imediatamente
            
        Returns:
            ID da tarefa
        """
        task_id = self._generate_task_id(name)
        
        next_run = datetime.now()
        if not start_immediately:
            next_run += timedelta(seconds=interval_seconds)
        
        task = ScheduledTask(
            id=task_id,
            name=name,
            callback=callback,
            interval_seconds=interval_seconds,
            repeat=True,
            next_run=next_run
        )
        
        self._tasks[task_id] = task
        logger.info(f"📅 Tarefa periódica adicionada: {name} (cada {interval_seconds}s)")
        
        return task_id
    
    def add_scheduled_task(
        self,
        name: str,
        callback: Callable[[], Coroutine],
        run_at: datetime,
        repeat_daily: bool = False
    ) -> str:
        """
        Adiciona tarefa para horário específico.
        
        Args:
            name: Nome da tarefa
            callback: Função async a executar
            run_at: Horário de execução
            repeat_daily: Se deve repetir diariamente
            
        Returns:
            ID da tarefa
        """
        task_id = self._generate_task_id(name)
        
        # Se o horário já passou hoje, agenda para amanhã
        now = datetime.now()
        if run_at <= now:
            run_at = run_at + timedelta(days=1)
        
        interval = 86400 if repeat_daily else None  # 24 horas em segundos
        
        task = ScheduledTask(
            id=task_id,
            name=name,
            callback=callback,
            run_at=run_at,
            interval_seconds=interval,
            repeat=repeat_daily,
            next_run=run_at
        )
        
        self._tasks[task_id] = task
        logger.info(f"📅 Tarefa agendada: {name} para {run_at.strftime('%H:%M:%S')}")
        
        return task_id
    
    def add_once_task(
        self,
        name: str,
        callback: Callable[[], Coroutine],
        delay_seconds: float = 0
    ) -> str:
        """
        Adiciona tarefa única.
        
        Args:
            name: Nome da tarefa
            callback: Função async a executar
            delay_seconds: Atraso antes da execução
            
        Returns:
            ID da tarefa
        """
        task_id = self._generate_task_id(name)
        
        run_at = datetime.now() + timedelta(seconds=delay_seconds)
        
        task = ScheduledTask(
            id=task_id,
            name=name,
            callback=callback,
            run_at=run_at,
            repeat=False,
            next_run=run_at
        )
        
        self._tasks[task_id] = task
        logger.debug(f"📅 Tarefa única adicionada: {name}")
        
        return task_id
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancela uma tarefa"""
        if task_id not in self._tasks:
            return False
        
        task = self._tasks[task_id]
        task.status = TaskStatus.CANCELLED
        
        if task._task and not task._task.done():
            task._task.cancel()
        
        logger.info(f"❌ Tarefa cancelada: {task.name}")
        return True
    
    def remove_task(self, task_id: str) -> bool:
        """Remove uma tarefa"""
        if task_id not in self._tasks:
            return False
        
        self.cancel_task(task_id)
        del self._tasks[task_id]
        return True
    
    def get_task_status(self, task_id: str) -> Optional[ScheduledTask]:
        """Retorna status de uma tarefa"""
        return self._tasks.get(task_id)
    
    def list_tasks(self) -> List[Dict[str, Any]]:
        """Lista todas as tarefas"""
        return [
            {
                'id': task.id,
                'name': task.name,
                'status': task.status.value,
                'last_run': task.last_run.isoformat() if task.last_run else None,
                'next_run': task.next_run.isoformat() if task.next_run else None,
                'run_count': task.run_count,
                'error_count': task.error_count,
            }
            for task in self._tasks.values()
        ]
    
    async def _run_task(self, task: ScheduledTask):
        """Executa uma tarefa"""
        task.status = TaskStatus.RUNNING
        task.last_run = datetime.now()
        
        try:
            await task.callback()
            task.status = TaskStatus.COMPLETED
            task.run_count += 1
            logger.debug(f"✅ Tarefa completada: {task.name}")
            
        except asyncio.CancelledError:
            task.status = TaskStatus.CANCELLED
            raise
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error_count += 1
            task.last_error = str(e)
            logger.error(f"❌ Erro na tarefa {task.name}: {e}")
        
        # Agenda próxima execução se repetitiva
        if task.repeat and task.interval_seconds:
            task.next_run = datetime.now() + timedelta(seconds=task.interval_seconds)
            task.status = TaskStatus.PENDING
    
    async def _task_loop(self, task: ScheduledTask):
        """Loop de execução para uma tarefa"""
        try:
            while self._running and task.status != TaskStatus.CANCELLED:
                if task.next_run:
                    # Espera até o próximo horário de execução
                    now = datetime.now()
                    if task.next_run > now:
                        wait_seconds = (task.next_run - now).total_seconds()
                        await asyncio.sleep(wait_seconds)
                
                if not self._running or task.status == TaskStatus.CANCELLED:
                    break
                
                await self._run_task(task)
                
                if not task.repeat:
                    break
                    
        except asyncio.CancelledError:
            task.status = TaskStatus.CANCELLED
    
    async def start(self):
        """Inicia o scheduler"""
        if self._running:
            return
        
        self._running = True
        logger.info("🚀 Scheduler iniciado")
        
        # Inicia tasks para cada tarefa
        for task in self._tasks.values():
            if task.status != TaskStatus.CANCELLED:
                task._task = asyncio.create_task(self._task_loop(task))
    
    async def stop(self):
        """Para o scheduler"""
        self._running = False
        
        # Cancela todas as tasks
        for task in self._tasks.values():
            if task._task and not task._task.done():
                task._task.cancel()
                try:
                    await task._task
                except asyncio.CancelledError:
                    pass
        
        logger.info("🛑 Scheduler parado")
    
    async def run_forever(self):
        """Executa o scheduler indefinidamente"""
        await self.start()
        try:
            while self._running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            await self.stop()


# Decorador para tarefas periódicas
def periodic(interval_seconds: float, start_immediately: bool = False):
    """
    Decorador para transformar função em tarefa periódica.
    
    Usage:
        @periodic(60)  # Executa a cada 60 segundos
        async def my_task():
            ...
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(scheduler: Scheduler) -> str:
            return scheduler.add_periodic_task(
                name=func.__name__,
                callback=func,
                interval_seconds=interval_seconds,
                start_immediately=start_immediately
            )
        wrapper._is_periodic = True
        wrapper._interval = interval_seconds
        return wrapper
    return decorator


# Decorador para tarefas diárias
def daily(hour: int, minute: int = 0):
    """
    Decorador para tarefa diária em horário específico.
    
    Usage:
        @daily(8, 30)  # Executa todo dia às 8:30
        async def my_task():
            ...
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(scheduler: Scheduler) -> str:
            run_at = datetime.now().replace(
                hour=hour, minute=minute, second=0, microsecond=0
            )
            return scheduler.add_scheduled_task(
                name=func.__name__,
                callback=func,
                run_at=run_at,
                repeat_daily=True
            )
        wrapper._is_daily = True
        wrapper._hour = hour
        wrapper._minute = minute
        return wrapper
    return decorator


# Instância global do scheduler
_scheduler: Optional[Scheduler] = None


def get_scheduler() -> Scheduler:
    """Retorna instância global do scheduler"""
    global _scheduler
    if _scheduler is None:
        _scheduler = Scheduler()
    return _scheduler
