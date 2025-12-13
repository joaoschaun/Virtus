"""
BRAIN - Scheduler
Agendador de tarefas periódicas
"""

import asyncio
from datetime import datetime, time, timedelta
from typing import Callable, Dict, List, Optional, Any
from dataclasses import dataclass, field
import pytz

from .config import Config
from .logger import get_logger

logger = get_logger("scheduler")


@dataclass
class ScheduledTask:
    """Representa uma tarefa agendada"""
    id: str
    name: str
    callback: Callable
    schedule_type: str  # "cron", "interval", "daily"
    enabled: bool = True
    
    # Para schedule_type = "interval"
    interval_seconds: int = 0
    
    # Para schedule_type = "daily" ou "cron"
    hour: int = 0
    minute: int = 0
    day_of_week: Optional[str] = None  # "monday", "tuesday", etc.
    
    # Timezone
    timezone: str = "America/Sao_Paulo"
    
    # Estado
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    error_count: int = 0
    
    # Args para o callback
    args: tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)


class TaskScheduler:
    """
    Agendador de tarefas do sistema BRAIN
    
    Suporta:
    - Tarefas com intervalo fixo
    - Tarefas diárias em horário específico
    - Tarefas semanais (cron-like)
    """
    
    def __init__(self):
        self._config = Config()
        self._tasks: Dict[str, ScheduledTask] = {}
        self._running = False
        self._task_loop: Optional[asyncio.Task] = None
    
    def add_task(
        self,
        task_id: str,
        name: str,
        callback: Callable,
        schedule_type: str = "interval",
        interval_seconds: int = 60,
        hour: int = 0,
        minute: int = 0,
        day_of_week: Optional[str] = None,
        timezone: str = "America/Sao_Paulo",
        args: tuple = (),
        kwargs: Optional[Dict[str, Any]] = None
    ) -> ScheduledTask:
        """
        Adiciona uma tarefa ao agendador
        
        Args:
            task_id: ID único da tarefa
            name: Nome descritivo
            callback: Função a ser executada (async ou sync)
            schedule_type: "interval", "daily" ou "weekly"
            interval_seconds: Intervalo em segundos (para type=interval)
            hour: Hora de execução (para type=daily/weekly)
            minute: Minuto de execução
            day_of_week: Dia da semana (para type=weekly)
            timezone: Timezone para agendamento
            args: Argumentos posicionais para o callback
            kwargs: Argumentos nomeados para o callback
            
        Returns:
            ScheduledTask criada
        """
        task = ScheduledTask(
            id=task_id,
            name=name,
            callback=callback,
            schedule_type=schedule_type,
            interval_seconds=interval_seconds,
            hour=hour,
            minute=minute,
            day_of_week=day_of_week,
            timezone=timezone,
            args=args,
            kwargs=kwargs or {}
        )
        
        # Calcular próxima execução
        task.next_run = self._calculate_next_run(task)
        
        self._tasks[task_id] = task
        logger.info(f"📅 Tarefa agendada: {name} ({schedule_type})")
        
        return task
    
    def remove_task(self, task_id: str) -> bool:
        """Remove uma tarefa do agendador"""
        if task_id in self._tasks:
            del self._tasks[task_id]
            logger.info(f"📅 Tarefa removida: {task_id}")
            return True
        return False
    
    def enable_task(self, task_id: str) -> bool:
        """Habilita uma tarefa"""
        if task_id in self._tasks:
            self._tasks[task_id].enabled = True
            self._tasks[task_id].next_run = self._calculate_next_run(self._tasks[task_id])
            return True
        return False
    
    def disable_task(self, task_id: str) -> bool:
        """Desabilita uma tarefa"""
        if task_id in self._tasks:
            self._tasks[task_id].enabled = False
            return True
        return False
    
    def _calculate_next_run(self, task: ScheduledTask) -> datetime:
        """Calcula a próxima execução de uma tarefa"""
        tz = pytz.timezone(task.timezone)
        now = datetime.now(tz)
        
        if task.schedule_type == "interval":
            return now + timedelta(seconds=task.interval_seconds)
        
        elif task.schedule_type == "daily":
            # Próxima execução no horário especificado
            target_time = now.replace(
                hour=task.hour,
                minute=task.minute,
                second=0,
                microsecond=0
            )
            
            # Se já passou hoje, agendar para amanhã
            if target_time <= now:
                target_time += timedelta(days=1)
            
            return target_time
        
        elif task.schedule_type == "weekly":
            # Encontrar o próximo dia da semana
            days = {
                "monday": 0, "tuesday": 1, "wednesday": 2,
                "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6
            }
            target_day = days.get(task.day_of_week.lower(), 0)
            current_day = now.weekday()
            
            days_ahead = target_day - current_day
            if days_ahead <= 0:  # Já passou esta semana
                days_ahead += 7
            
            target_date = now + timedelta(days=days_ahead)
            target_time = target_date.replace(
                hour=task.hour,
                minute=task.minute,
                second=0,
                microsecond=0
            )
            
            return target_time
        
        return now + timedelta(hours=1)  # Fallback
    
    async def _run_task(self, task: ScheduledTask):
        """Executa uma tarefa"""
        try:
            logger.debug(f"⏰ Executando tarefa: {task.name}")
            
            # Verificar se é async
            if asyncio.iscoroutinefunction(task.callback):
                await task.callback(*task.args, **task.kwargs)
            else:
                task.callback(*task.args, **task.kwargs)
            
            task.run_count += 1
            task.last_run = datetime.now(pytz.timezone(task.timezone))
            
            logger.debug(f"✅ Tarefa concluída: {task.name}")
            
        except Exception as e:
            task.error_count += 1
            logger.error(f"❌ Erro na tarefa {task.name}: {e}")
    
    async def _scheduler_loop(self):
        """Loop principal do agendador"""
        logger.info("⏰ Scheduler iniciado")
        
        while self._running:
            now = datetime.now(pytz.timezone("America/Sao_Paulo"))
            
            for task in self._tasks.values():
                if not task.enabled:
                    continue
                
                if task.next_run and now >= task.next_run:
                    # Executar tarefa
                    asyncio.create_task(self._run_task(task))
                    
                    # Calcular próxima execução
                    task.next_run = self._calculate_next_run(task)
            
            # Aguardar 1 segundo antes de verificar novamente
            await asyncio.sleep(1)
        
        logger.info("⏰ Scheduler parado")
    
    async def start(self):
        """Inicia o agendador"""
        if self._running:
            logger.warning("Scheduler já está rodando")
            return
        
        self._running = True
        self._task_loop = asyncio.create_task(self._scheduler_loop())
        
        logger.info(f"⏰ Scheduler iniciado com {len(self._tasks)} tarefas")
    
    async def stop(self):
        """Para o agendador"""
        self._running = False
        
        if self._task_loop:
            self._task_loop.cancel()
            try:
                await self._task_loop
            except asyncio.CancelledError:
                pass
        
        logger.info("⏰ Scheduler parado")
    
    def get_status(self) -> Dict[str, Any]:
        """Retorna status do agendador"""
        return {
            "running": self._running,
            "total_tasks": len(self._tasks),
            "enabled_tasks": sum(1 for t in self._tasks.values() if t.enabled),
            "tasks": [
                {
                    "id": t.id,
                    "name": t.name,
                    "enabled": t.enabled,
                    "schedule_type": t.schedule_type,
                    "next_run": t.next_run.isoformat() if t.next_run else None,
                    "run_count": t.run_count,
                    "error_count": t.error_count
                }
                for t in self._tasks.values()
            ]
        }


# Instância global do scheduler
_scheduler: Optional[TaskScheduler] = None


def get_scheduler() -> TaskScheduler:
    """Retorna instância singleton do scheduler"""
    global _scheduler
    if _scheduler is None:
        _scheduler = TaskScheduler()
    return _scheduler
