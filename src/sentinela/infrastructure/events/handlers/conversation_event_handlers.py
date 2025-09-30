"""
Event Handlers para eventos relacionados a conversas de suporte.

Processa eventos de domínio para implementar funcionalidades
como limpeza automática, métricas de UX e otimização de fluxos.
"""

import asyncio
import logging
from typing import Type

from ..event_bus import EventHandler, DomainEvent
from ....domain.events.conversation_events import (
    ConversationStarted,
    ConversationCompleted,
    ConversationCancelled
)

logger = logging.getLogger(__name__)


class ConversationStartedHandler(EventHandler):
    """
    Handler para evento de conversa iniciada.

    Responsabilidades:
    - Log de início de conversa
    - Configuração de timeout automático
    - Métricas de engajamento
    - Preparação de contexto
    """

    @property
    def event_type(self) -> Type[DomainEvent]:
        return ConversationStarted

    async def handle(self, event: ConversationStarted) -> None:
        """
        Processa evento de conversa iniciada.

        Args:
            event: Evento de conversa iniciada
        """
        logger.info(
            f"💬 CONVERSA INICIADA: {event.conversation_id} "
            f"por usuário {event.username} (ID: {event.user_id}) "
            f"em {event.started_at.strftime('%H:%M:%S')}"
        )

        # Configura timeout automático
        await self._setup_conversation_timeout(event)

        # Atualiza métricas de engajamento
        await self._update_engagement_metrics(event)

        # Prepara contexto da conversa
        await self._prepare_conversation_context(event)

    async def _setup_conversation_timeout(self, event: ConversationStarted) -> None:
        """
        Configura timeout automático para a conversa.

        Args:
            event: Evento de conversa iniciada
        """
        try:
            # Em produção, configuraria timer real para cancelar conversa inativa
            logger.debug(
                f"⏰ TIMEOUT: Configurado timeout de 30min para conversa {event.conversation_id}"
            )

            # Simula configuração de timeout
            await asyncio.sleep(0.05)

        except Exception as e:
            logger.error(f"Erro ao configurar timeout para conversa {event.conversation_id}: {e}")

    async def _update_engagement_metrics(self, event: ConversationStarted) -> None:
        """
        Atualiza métricas de engajamento.

        Args:
            event: Evento de conversa iniciada
        """
        try:
            logger.debug(
                f"📈 ENGAGEMENT: Nova conversa contabilizada "
                f"- Total de sessões incrementado"
            )

            # Em produção, atualizaria dashboard de UX metrics

        except Exception as e:
            logger.error(f"Erro ao atualizar métricas para conversa {event.conversation_id}: {e}")

    async def _prepare_conversation_context(self, event: ConversationStarted) -> None:
        """
        Prepara contexto inicial da conversa.

        Args:
            event: Evento de conversa iniciada
        """
        try:
            logger.debug(
                f"🎯 CONTEXTO: Preparando ambiente para {event.username} "
                f"- Histórico e preferências carregados"
            )

            # Em produção, carregaria histórico de tickets, preferências, etc.

        except Exception as e:
            logger.error(f"Erro ao preparar contexto para conversa {event.conversation_id}: {e}")


class ConversationCompletedHandler(EventHandler):
    """
    Handler para evento de conversa completada com sucesso.

    Responsabilidades:
    - Log de sucesso
    - Métricas de conversão
    - Análise de performance do fluxo
    - Preparação para feedback
    """

    @property
    def event_type(self) -> Type[DomainEvent]:
        return ConversationCompleted

    async def handle(self, event: ConversationCompleted) -> None:
        """
        Processa evento de conversa completada.

        Args:
            event: Evento de conversa completada
        """
        # Calcula duração da conversa
        duration_seconds = (event.completed_at - event.started_at).total_seconds()
        duration_str = f"{int(duration_seconds//60)}m{int(duration_seconds%60):02d}s"

        logger.info(
            f"✅ CONVERSA COMPLETADA: {event.conversation_id} "
            f"por {event.username} - Duração: {duration_str} "
            f"- Ticket criado: {event.ticket_id}"
        )

        # Atualiza métricas de conversão
        await self._update_conversion_metrics(event, duration_seconds)

        # Análise de performance do fluxo
        await self._analyze_flow_performance(event, duration_seconds)

        # Prepara feedback automático
        await self._prepare_feedback_request(event)

        # Limpeza de dados temporários
        await self._cleanup_conversation_data(event)

    async def _update_conversion_metrics(self, event: ConversationCompleted, duration_seconds: float) -> None:
        """
        Atualiza métricas de conversão.

        Args:
            event: Evento de conversa completada
            duration_seconds: Duração da conversa em segundos
        """
        try:
            logger.debug(
                f"📊 CONVERSÃO: Conversa bem-sucedida registrada "
                f"- Taxa de conversão atualizada - Duração: {duration_seconds:.1f}s"
            )

            # Em produção, atualizaria métricas de UX e conversão

        except Exception as e:
            logger.error(f"Erro ao atualizar métricas de conversão para conversa {event.conversation_id}: {e}")

    async def _analyze_flow_performance(self, event: ConversationCompleted, duration_seconds: float) -> None:
        """
        Analisa performance do fluxo conversacional.

        Args:
            event: Evento de conversa completada
            duration_seconds: Duração da conversa em segundos
        """
        try:
            # Classifica performance baseada na duração
            if duration_seconds < 120:  # < 2 minutos
                performance = "EXCELENTE"
            elif duration_seconds < 300:  # < 5 minutos
                performance = "BOM"
            elif duration_seconds < 600:  # < 10 minutos
                performance = "ACEITÁVEL"
            else:
                performance = "LENTO"

            logger.debug(
                f"⚡ PERFORMANCE: Fluxo {performance} "
                f"({duration_seconds:.1f}s) para conversa {event.conversation_id}"
            )

            # Em produção, usaria para otimizar UX

        except Exception as e:
            logger.error(f"Erro na análise de performance para conversa {event.conversation_id}: {e}")

    async def _prepare_feedback_request(self, event: ConversationCompleted) -> None:
        """
        Prepara solicitação de feedback automática.

        Args:
            event: Evento de conversa completada
        """
        try:
            logger.debug(
                f"💭 FEEDBACK: Preparando solicitação de feedback "
                f"para usuário {event.username} em 24h"
            )

            # Em produção, agendaria mensagem de feedback

        except Exception as e:
            logger.error(f"Erro ao preparar feedback para conversa {event.conversation_id}: {e}")

    async def _cleanup_conversation_data(self, event: ConversationCompleted) -> None:
        """
        Limpa dados temporários da conversa.

        Args:
            event: Evento de conversa completada
        """
        try:
            logger.debug(
                f"🧹 CLEANUP: Limpando dados temporários da conversa {event.conversation_id}"
            )

            # Em produção, removeria cache, sessões temporárias, etc.

        except Exception as e:
            logger.error(f"Erro na limpeza para conversa {event.conversation_id}: {e}")


class ConversationCancelledHandler(EventHandler):
    """
    Handler para evento de conversa cancelada.

    Responsabilidades:
    - Log de cancelamento
    - Análise de abandono
    - Métricas de UX
    - Limpeza de recursos
    """

    @property
    def event_type(self) -> Type[DomainEvent]:
        return ConversationCancelled

    async def handle(self, event: ConversationCancelled) -> None:
        """
        Processa evento de conversa cancelada.

        Args:
            event: Evento de conversa cancelada
        """
        # Calcula duração antes do cancelamento
        duration_seconds = (event.cancelled_at - event.started_at).total_seconds()
        duration_str = f"{int(duration_seconds//60)}m{int(duration_seconds%60):02d}s"

        logger.warning(
            f"❌ CONVERSA CANCELADA: {event.conversation_id} "
            f"por {event.username} - Motivo: {event.reason} "
            f"- Duração antes do cancelamento: {duration_str} "
            f"- Step: {event.step}"
        )

        # Análise de abandono
        await self._analyze_abandonment(event, duration_seconds)

        # Atualiza métricas de UX
        await self._update_ux_metrics(event)

        # Limpeza de recursos
        await self._cleanup_cancelled_conversation(event)

        # Possível reengajamento
        await self._consider_reengagement(event)

    async def _analyze_abandonment(self, event: ConversationCancelled, duration_seconds: float) -> None:
        """
        Analisa padrões de abandono para otimização.

        Args:
            event: Evento de conversa cancelada
            duration_seconds: Duração antes do cancelamento
        """
        try:
            # Identifica ponto crítico de abandono
            critical_steps = {
                "CATEGORY_SELECTION": "Categoria complexa demais?",
                "GAME_SELECTION": "Muitas opções de jogos?",
                "DESCRIPTION_INPUT": "Campo de descrição intimidante?",
                "ATTACHMENTS_OPTIONAL": "Processo de upload confuso?"
            }

            insight = critical_steps.get(event.step, "Abandono em passo não crítico")

            logger.info(
                f"🔍 ABANDONO: Step '{event.step}' após {duration_seconds:.1f}s "
                f"- Insight: {insight}"
            )

            # Em produção, usaria para otimizar UX nos pontos críticos

        except Exception as e:
            logger.error(f"Erro na análise de abandono para conversa {event.conversation_id}: {e}")

    async def _update_ux_metrics(self, event: ConversationCancelled) -> None:
        """
        Atualiza métricas de experiência do usuário.

        Args:
            event: Evento de conversa cancelada
        """
        try:
            logger.debug(
                f"📉 UX METRICS: Abandono registrado em '{event.step}' "
                f"- Taxa de abandono atualizada"
            )

            # Em produção, atualizaria dashboard de UX

        except Exception as e:
            logger.error(f"Erro ao atualizar UX metrics para conversa {event.conversation_id}: {e}")

    async def _cleanup_cancelled_conversation(self, event: ConversationCancelled) -> None:
        """
        Limpa recursos da conversa cancelada.

        Args:
            event: Evento de conversa cancelada
        """
        try:
            logger.debug(
                f"🧹 CLEANUP: Limpando recursos da conversa cancelada {event.conversation_id}"
            )

            # Em produção, removeria locks, cache, timers, etc.

        except Exception as e:
            logger.error(f"Erro na limpeza de conversa cancelada {event.conversation_id}: {e}")

    async def _consider_reengagement(self, event: ConversationCancelled) -> None:
        """
        Considera estratégia de reengajamento.

        Args:
            event: Evento de conversa cancelada
        """
        try:
            # Se cancelamento foi por timeout ou abandono, considera reengajamento
            if event.reason in ("timeout", "abandonment"):
                logger.info(
                    f"🎯 REENGAGEMENT: Usuário {event.username} elegível "
                    f"para campanha de reengajamento (abandono em '{event.step}')"
                )

                # Em produção, adicionaria à campanha de reengajamento

        except Exception as e:
            logger.error(f"Erro ao considerar reengajamento para conversa {event.conversation_id}: {e}")


class ConversationFlowAnalyticsHandler(EventHandler):
    """
    Handler global para analytics de fluxo conversacional.

    Responsabilidades:
    - Análise detalhada de fluxos
    - Identificação de gargalos
    - Otimização automática
    - A/B testing insights
    """

    @property
    def event_type(self) -> Type[DomainEvent]:
        # Handler global para eventos de conversa
        return DomainEvent

    async def handle(self, event: DomainEvent) -> None:
        """
        Processa eventos de conversa para analytics.

        Args:
            event: Qualquer evento de domínio
        """
        # Só processa eventos de conversa
        if not event.__class__.__name__.startswith('Conversation'):
            return

        logger.debug(
            f"📊 FLOW ANALYTICS: {event.__class__.__name__} "
            f"processado para análise de fluxo"
        )

        # Em produção, alimentaria sistema de analytics avançado
        await self._save_flow_analytics(event)

    async def _save_flow_analytics(self, event: DomainEvent) -> None:
        """
        Salva dados para análise de fluxo.

        Args:
            event: Evento de conversa
        """
        try:
            # Em produção, salvaria em data warehouse para análises avançadas
            logger.debug(f"💾 FLOW DATA: {event.__class__.__name__} registrado para analytics")

        except Exception as e:
            logger.error(f"Erro ao salvar flow analytics: {e}")