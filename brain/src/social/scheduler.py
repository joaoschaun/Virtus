"""
VIRTUS Social Media - Post Scheduler
=====================================

Agendador de posts para redes sociais.
Gerencia fila de posts e horários estratégicos de publicação.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, time
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
import asyncio
import logging
import json
from collections import deque

from .content_generator import PostContent, PostType

logger = logging.getLogger(__name__)


class ScheduleType(Enum):
    """Tipos de agendamento."""
    IMMEDIATE = "immediate"       # Publicar imediatamente
    SCHEDULED = "scheduled"       # Publicar em horário específico
    OPTIMAL = "optimal"           # Publicar no próximo horário ótimo
    QUEUE = "queue"               # Adicionar à fila


@dataclass
class ScheduledPost:
    """Post agendado."""
    content: PostContent
    schedule_type: ScheduleType
    scheduled_time: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    # Status
    published: bool = False
    published_at: Optional[datetime] = None
    post_id: Optional[str] = None
    error: Optional[str] = None
    attempts: int = 0
    max_attempts: int = 3
    
    # Metadata
    id: str = field(default_factory=lambda: f"post_{datetime.now().strftime('%Y%m%d%H%M%S')}")
    
    def can_retry(self) -> bool:
        """Verifica se pode tentar novamente."""
        return not self.published and self.attempts < self.max_attempts


class SocialScheduler:
    """
    Agendador de posts para redes sociais.
    
    Gerencia:
    - Fila de posts
    - Horários estratégicos de publicação
    - Rate limiting
    - Retentativas em caso de falha
    """
    
    def __init__(self):
        # Fila de posts
        self._queue: deque[ScheduledPost] = deque()
        self._scheduled: List[ScheduledPost] = []
        self._published: List[ScheduledPost] = []
        
        # Configuração de horários ótimos (hora em UTC-3)
        self._optimal_times = {
            # Manhã (abertura de mercado)
            "morning_1": time(7, 30),
            "morning_2": time(9, 0),
            "morning_3": time(10, 30),
            
            # Almoço
            "lunch": time(12, 0),
            
            # Tarde
            "afternoon_1": time(14, 0),
            "afternoon_2": time(16, 0),
            
            # Noite (engajamento social)
            "evening_1": time(18, 30),
            "evening_2": time(20, 0),
            "evening_3": time(21, 30),
        }
        
        # Limites por tipo de post
        self._daily_limits = {
            PostType.MARKET_ALERT: 5,
            PostType.DAILY_SUMMARY: 1,
            PostType.NEWS_HIGHLIGHT: 3,
            PostType.TRADING_TIP: 2,
            PostType.EDUCATIONAL: 2,
            PostType.TECHNICAL_ANALYSIS: 3,
            PostType.WEEKLY_OUTLOOK: 1,
            PostType.PERFORMANCE: 1,
        }
        
        # Contadores diários
        self._daily_counts: Dict[PostType, int] = {}
        self._last_reset = datetime.now().date()
        
        # Intervalo mínimo entre posts (minutos)
        self._min_interval = 30
        self._last_post_time: Optional[datetime] = None
        
        # Callback para publicação (será definido pelo SocialMediaManager)
        self._publish_callback: Optional[Callable] = None
        
        # Flag de execução
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    def _reset_daily_counts(self):
        """Reseta contadores diários se necessário."""
        today = datetime.now().date()
        if today > self._last_reset:
            self._daily_counts = {}
            self._last_reset = today
    
    def _check_daily_limit(self, post_type: PostType) -> bool:
        """Verifica se ainda pode postar este tipo."""
        self._reset_daily_counts()
        current = self._daily_counts.get(post_type, 0)
        limit = self._daily_limits.get(post_type, 10)
        return current < limit
    
    def _can_post_now(self) -> bool:
        """Verifica se pode postar agora (intervalo mínimo)."""
        if self._last_post_time is None:
            return True
        
        elapsed = datetime.now() - self._last_post_time
        return elapsed.total_seconds() >= self._min_interval * 60
    
    def _get_next_optimal_time(self) -> datetime:
        """Retorna o próximo horário ótimo de publicação."""
        now = datetime.now()
        current_time = now.time()
        
        # Ordena horários
        sorted_times = sorted(self._optimal_times.values())
        
        # Encontra próximo horário
        for optimal in sorted_times:
            if optimal > current_time:
                return datetime.combine(now.date(), optimal)
        
        # Se passou de todos os horários, agenda para amanhã
        tomorrow = now.date() + timedelta(days=1)
        return datetime.combine(tomorrow, sorted_times[0])
    
    def add_to_queue(self, content: PostContent) -> ScheduledPost:
        """
        Adiciona post à fila.
        
        Args:
            content: Conteúdo do post
            
        Returns:
            Post agendado
        """
        scheduled = ScheduledPost(
            content=content,
            schedule_type=ScheduleType.QUEUE,
        )
        
        # Posts de alta prioridade vão para o início da fila
        if content.priority in ["high", "urgent"]:
            self._queue.appendleft(scheduled)
        else:
            self._queue.append(scheduled)
        
        logger.info(f"Post adicionado à fila: {scheduled.id}")
        return scheduled
    
    def schedule_post(
        self,
        content: PostContent,
        scheduled_time: datetime,
    ) -> ScheduledPost:
        """
        Agenda post para horário específico.
        
        Args:
            content: Conteúdo do post
            scheduled_time: Horário de publicação
            
        Returns:
            Post agendado
        """
        scheduled = ScheduledPost(
            content=content,
            schedule_type=ScheduleType.SCHEDULED,
            scheduled_time=scheduled_time,
        )
        
        self._scheduled.append(scheduled)
        
        # Ordena por horário
        self._scheduled.sort(key=lambda x: x.scheduled_time or datetime.max)
        
        logger.info(
            f"Post agendado para {scheduled_time.strftime('%d/%m %H:%M')}: "
            f"{scheduled.id}"
        )
        return scheduled
    
    def schedule_optimal(self, content: PostContent) -> ScheduledPost:
        """
        Agenda post para próximo horário ótimo.
        
        Args:
            content: Conteúdo do post
            
        Returns:
            Post agendado
        """
        optimal_time = self._get_next_optimal_time()
        return self.schedule_post(content, optimal_time)
    
    def post_immediately(self, content: PostContent) -> ScheduledPost:
        """
        Marca post para publicação imediata.
        
        Args:
            content: Conteúdo do post
            
        Returns:
            Post agendado
        """
        scheduled = ScheduledPost(
            content=content,
            schedule_type=ScheduleType.IMMEDIATE,
            scheduled_time=datetime.now(),
        )
        
        # Adiciona no início da fila
        self._queue.appendleft(scheduled)
        
        logger.info(f"Post marcado para publicação imediata: {scheduled.id}")
        return scheduled
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Retorna status da fila."""
        self._reset_daily_counts()
        
        return {
            "queue_size": len(self._queue),
            "scheduled_count": len(self._scheduled),
            "published_today": sum(self._daily_counts.values()),
            "daily_counts": {t.value: c for t, c in self._daily_counts.items()},
            "daily_limits": {t.value: l for t, l in self._daily_limits.items()},
            "next_optimal_time": self._get_next_optimal_time().isoformat(),
            "last_post": self._last_post_time.isoformat() if self._last_post_time else None,
            "can_post_now": self._can_post_now(),
        }
    
    def get_pending_posts(self) -> List[Dict[str, Any]]:
        """Retorna lista de posts pendentes."""
        pending = []
        
        # Posts na fila
        for post in self._queue:
            pending.append({
                "id": post.id,
                "type": post.content.post_type.value,
                "title": post.content.title,
                "schedule_type": post.schedule_type.value,
                "scheduled_time": None,
                "priority": post.content.priority,
            })
        
        # Posts agendados
        for post in self._scheduled:
            if not post.published:
                pending.append({
                    "id": post.id,
                    "type": post.content.post_type.value,
                    "title": post.content.title,
                    "schedule_type": post.schedule_type.value,
                    "scheduled_time": post.scheduled_time.isoformat() if post.scheduled_time else None,
                    "priority": post.content.priority,
                })
        
        return pending
    
    def get_published_posts(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Retorna últimos posts publicados."""
        return [
            {
                "id": post.id,
                "post_id": post.post_id,
                "type": post.content.post_type.value,
                "title": post.content.title,
                "published_at": post.published_at.isoformat() if post.published_at else None,
            }
            for post in self._published[-limit:]
        ]
    
    def cancel_post(self, post_id: str) -> bool:
        """
        Cancela post agendado.
        
        Args:
            post_id: ID do post
            
        Returns:
            True se cancelado
        """
        # Remove da fila
        for i, post in enumerate(list(self._queue)):
            if post.id == post_id:
                del self._queue[i]
                logger.info(f"Post removido da fila: {post_id}")
                return True
        
        # Remove dos agendados
        self._scheduled = [
            p for p in self._scheduled 
            if p.id != post_id
        ]
        
        return False
    
    def set_publish_callback(self, callback: Callable):
        """
        Define callback para publicação.
        
        O callback deve ser uma função async que recebe um ScheduledPost
        e retorna um PostResult.
        """
        self._publish_callback = callback
    
    async def process_queue(self) -> Optional[ScheduledPost]:
        """
        Processa próximo post da fila.
        
        Returns:
            Post processado ou None
        """
        if not self._publish_callback:
            logger.warning("Callback de publicação não definido")
            return None
        
        if not self._can_post_now():
            logger.debug("Intervalo mínimo não atingido")
            return None
        
        # Verifica posts agendados primeiro
        now = datetime.now()
        for post in self._scheduled:
            if (not post.published and 
                post.scheduled_time and 
                post.scheduled_time <= now):
                
                if post.can_retry():
                    return await self._publish_post(post)
        
        # Depois processa fila
        if self._queue:
            post = self._queue.popleft()
            
            # Verifica limite diário
            if not self._check_daily_limit(post.content.post_type):
                logger.warning(
                    f"Limite diário atingido para {post.content.post_type.value}"
                )
                # Recoloca no fim da fila
                self._queue.append(post)
                return None
            
            return await self._publish_post(post)
        
        return None
    
    async def _publish_post(self, post: ScheduledPost) -> ScheduledPost:
        """Executa publicação de um post."""
        post.attempts += 1
        
        try:
            result = await self._publish_callback(post)
            
            if result.success:
                post.published = True
                post.published_at = datetime.now()
                post.post_id = result.post_id
                
                self._last_post_time = datetime.now()
                
                # Incrementa contador diário
                post_type = post.content.post_type
                self._daily_counts[post_type] = self._daily_counts.get(post_type, 0) + 1
                
                # Move para publicados
                if post in self._scheduled:
                    self._scheduled.remove(post)
                self._published.append(post)
                
                logger.info(f"Post publicado: {post.id} -> {result.post_id}")
            else:
                post.error = result.error
                logger.error(f"Falha ao publicar {post.id}: {result.error}")
                
                # Se pode tentar novamente, recoloca na fila
                if post.can_retry():
                    self._queue.append(post)
                    
        except Exception as e:
            post.error = str(e)
            logger.error(f"Erro ao publicar {post.id}: {e}")
            
            if post.can_retry():
                self._queue.append(post)
        
        return post
    
    async def run(self, interval: int = 60):
        """
        Inicia loop de processamento.
        
        Args:
            interval: Intervalo entre verificações (segundos)
        """
        self._running = True
        logger.info("Scheduler iniciado")
        
        while self._running:
            try:
                await self.process_queue()
            except Exception as e:
                logger.error(f"Erro no scheduler: {e}")
            
            await asyncio.sleep(interval)
    
    def stop(self):
        """Para o scheduler."""
        self._running = False
        logger.info("Scheduler parado")
    
    async def start(self, interval: int = 60):
        """
        Inicia scheduler em background.
        
        Args:
            interval: Intervalo entre verificações
        """
        self._task = asyncio.create_task(self.run(interval))
    
    def save_state(self, filepath: Path):
        """Salva estado para persistência."""
        state = {
            "queue": [
                {
                    "id": p.id,
                    "content": {
                        "type": p.content.post_type.value,
                        "title": p.content.title,
                        "caption": p.content.caption,
                    },
                    "schedule_type": p.schedule_type.value,
                    "scheduled_time": p.scheduled_time.isoformat() if p.scheduled_time else None,
                    "attempts": p.attempts,
                }
                for p in self._queue
            ],
            "scheduled": [
                {
                    "id": p.id,
                    "content": {
                        "type": p.content.post_type.value,
                        "title": p.content.title,
                        "caption": p.content.caption,
                    },
                    "schedule_type": p.schedule_type.value,
                    "scheduled_time": p.scheduled_time.isoformat() if p.scheduled_time else None,
                    "attempts": p.attempts,
                }
                for p in self._scheduled if not p.published
            ],
            "daily_counts": {t.value: c for t, c in self._daily_counts.items()},
            "last_reset": self._last_reset.isoformat(),
        }
        
        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2)
        
        logger.info(f"Estado salvo em {filepath}")
