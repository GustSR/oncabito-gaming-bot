"""
Gaming Support Use Case.

Use case especializado para suporte técnico gaming,
integrando diagnósticos e recomendações específicas.
"""

import logging
from typing import List, Optional
from dataclasses import dataclass

from ..use_cases.base import UseCase, UseCaseResult
from ...domain.services.gaming_diagnostic_service import (
    GamingDiagnosticService,
    GamePlatform,
    ConnectionType,
    DiagnosticResult
)
from ...domain.value_objects.game_title import GameTitle
from ...domain.value_objects.problem_category import ProblemCategory

logger = logging.getLogger(__name__)


@dataclass
class GamingDiagnosisResult:
    """Resultado de diagnóstico gaming."""

    success: bool
    message: str
    diagnostics: List[DiagnosticResult]
    formatted_response: str
    severity_level: str


@dataclass
class OptimizationResult:
    """Resultado de recomendações de otimização."""

    success: bool
    message: str
    tips: List[str]
    formatted_response: str


class GamingSupportUseCase(UseCase):
    """
    Use Case para suporte técnico gaming especializado.

    Combina análise de problemas com base de conhecimento
    específica para jogos e plataformas.
    """

    def __init__(self):
        """Inicializa o use case."""
        self.diagnostic_service = GamingDiagnosticService()

    async def diagnose_problem(
        self,
        problem_description: str,
        game_title: Optional[GameTitle] = None,
        category: Optional[ProblemCategory] = None,
        platform: Optional[GamePlatform] = None
    ) -> GamingDiagnosisResult:
        """
        Analisa problema e fornece diagnóstico.

        Args:
            problem_description: Descrição do problema
            game_title: Jogo afetado (opcional)
            category: Categoria do problema (opcional)
            platform: Plataforma (opcional)

        Returns:
            GamingDiagnosisResult: Diagnóstico completo
        """
        try:
            logger.info(f"Diagnosticando problema gaming: {problem_description[:50]}...")

            # Obtém diagnósticos
            game_name = game_title.display_name if game_title else None

            diagnostics = self.diagnostic_service.diagnose_from_description(
                problem_description=problem_description,
                game_title=game_name,
                platform=platform
            )

            if not diagnostics:
                return GamingDiagnosisResult(
                    success=False,
                    message="Não foi possível diagnosticar o problema",
                    diagnostics=[],
                    formatted_response="❌ Não consegui identificar o problema. Forneça mais detalhes.",
                    severity_level="unknown"
                )

            # Determina severidade geral
            severity_level = self._determine_overall_severity(diagnostics)

            # Formata resposta
            formatted_response = self._format_diagnosis_response(
                diagnostics,
                game_title,
                severity_level
            )

            logger.info(f"Diagnóstico concluído: {len(diagnostics)} possíveis causas")

            return GamingDiagnosisResult(
                success=True,
                message=f"Identificadas {len(diagnostics)} possíveis causas",
                diagnostics=diagnostics,
                formatted_response=formatted_response,
                severity_level=severity_level
            )

        except Exception as e:
            logger.error(f"Erro ao diagnosticar problema: {e}")
            return GamingDiagnosisResult(
                success=False,
                message=f"Erro ao diagnosticar: {str(e)}",
                diagnostics=[],
                formatted_response="❌ Erro ao processar diagnóstico. Tente novamente.",
                severity_level="unknown"
            )

    async def get_optimization_recommendations(
        self,
        game_title: GameTitle,
        platform: GamePlatform
    ) -> OptimizationResult:
        """
        Retorna recomendações de otimização.

        Args:
            game_title: Jogo
            platform: Plataforma

        Returns:
            OptimizationResult: Recomendações
        """
        try:
            logger.info(f"Gerando recomendações de otimização para {game_title.display_name}")

            tips = self.diagnostic_service.get_optimization_tips(
                game_title=game_title.display_name,
                platform=platform
            )

            if not tips:
                return OptimizationResult(
                    success=False,
                    message="Nenhuma recomendação disponível",
                    tips=[],
                    formatted_response="❌ Sem recomendações específicas para este jogo."
                )

            # Formata resposta
            formatted_response = self._format_optimization_response(
                tips,
                game_title,
                platform
            )

            logger.info(f"Geradas {len(tips)} recomendações de otimização")

            return OptimizationResult(
                success=True,
                message=f"{len(tips)} recomendações disponíveis",
                tips=tips,
                formatted_response=formatted_response
            )

        except Exception as e:
            logger.error(f"Erro ao gerar recomendações: {e}")
            return OptimizationResult(
                success=False,
                message=f"Erro: {str(e)}",
                tips=[],
                formatted_response="❌ Erro ao gerar recomendações."
            )

    async def get_connection_troubleshooting(
        self,
        connection_type: ConnectionType
    ) -> UseCaseResult:
        """
        Retorna guia de troubleshooting de conexão.

        Args:
            connection_type: Tipo de conexão

        Returns:
            UseCaseResult: Guia de troubleshooting
        """
        try:
            logger.info(f"Gerando troubleshooting para conexão {connection_type.value}")

            steps = self.diagnostic_service.get_connection_troubleshooting(
                connection_type
            )

            formatted_message = self._format_troubleshooting_response(
                steps,
                connection_type
            )

            return UseCaseResult(
                success=True,
                message=f"Guia de troubleshooting para {connection_type.value}",
                data={
                    'steps': steps,
                    'formatted': formatted_message
                }
            )

        except Exception as e:
            logger.error(f"Erro ao gerar troubleshooting: {e}")
            return UseCaseResult(
                success=False,
                message=f"Erro: {str(e)}"
            )

    async def analyze_ticket_and_suggest_solution(
        self,
        ticket_description: str,
        game_title: Optional[GameTitle] = None,
        category: Optional[ProblemCategory] = None
    ) -> UseCaseResult:
        """
        Analisa ticket e sugere solução completa.

        Args:
            ticket_description: Descrição do ticket
            game_title: Jogo (opcional)
            category: Categoria (opcional)

        Returns:
            UseCaseResult: Análise e sugestão
        """
        try:
            logger.info("Analisando ticket para sugestão de solução")

            # Realiza diagnóstico
            diagnosis = await self.diagnose_problem(
                problem_description=ticket_description,
                game_title=game_title,
                category=category
            )

            if not diagnosis.success:
                return UseCaseResult(
                    success=False,
                    message="Não foi possível analisar o ticket"
                )

            # Monta resposta completa
            complete_response = self._build_complete_solution(
                diagnosis,
                game_title
            )

            return UseCaseResult(
                success=True,
                message="Análise e solução sugerida",
                data={
                    'diagnosis': diagnosis,
                    'formatted_solution': complete_response
                }
            )

        except Exception as e:
            logger.error(f"Erro ao analisar ticket: {e}")
            return UseCaseResult(
                success=False,
                message=f"Erro: {str(e)}"
            )

    # Private helper methods

    def _determine_overall_severity(
        self,
        diagnostics: List[DiagnosticResult]
    ) -> str:
        """Determina severidade geral baseado nos diagnósticos."""
        severity_order = ['critical', 'high', 'medium', 'low']

        for severity in severity_order:
            if any(d.severity == severity for d in diagnostics):
                return severity

        return 'low'

    def _format_diagnosis_response(
        self,
        diagnostics: List[DiagnosticResult],
        game_title: Optional[GameTitle],
        severity_level: str
    ) -> str:
        """Formata resposta de diagnóstico."""
        # Emojis por severidade
        severity_emojis = {
            'critical': '🚨',
            'high': '⚠️',
            'medium': '⚡',
            'low': 'ℹ️'
        }

        emoji = severity_emojis.get(severity_level, 'ℹ️')

        response = f"{emoji} <b>DIAGNÓSTICO TÉCNICO</b>\n\n"

        if game_title:
            response += f"🎮 <b>Jogo:</b> {game_title.display_name}\n\n"

        response += f"📊 <b>Severidade:</b> {severity_level.upper()}\n"
        response += f"🔍 <b>Problemas detectados:</b> {len(diagnostics)}\n\n"

        # Lista cada diagnóstico
        for i, diag in enumerate(diagnostics, 1):
            response += f"<b>{i}. {diag.issue_detected}</b>\n"
            response += f"   💡 <b>Causa provável:</b> {diag.likely_cause}\n\n"
            response += f"   <b>Recomendações:</b>\n"

            for rec in diag.recommendations[:5]:  # Limita a 5
                response += f"   {rec}\n"

            if diag.technical_details:
                response += f"\n   📋 <i>{diag.technical_details}</i>\n"

            response += "\n"

        response += "💬 <b>Precisa de mais ajuda? Use /suporte para abrir ticket detalhado</b>"

        return response

    def _format_optimization_response(
        self,
        tips: List[str],
        game_title: GameTitle,
        platform: GamePlatform
    ) -> str:
        """Formata resposta de otimização."""
        response = f"⚡ <b>OTIMIZAÇÃO PARA {game_title.display_name.upper()}</b>\n\n"
        response += f"🖥️ <b>Plataforma:</b> {platform.value.upper()}\n"
        response += f"📊 <b>Dicas encontradas:</b> {len(tips)}\n\n"

        for tip in tips:
            response += f"{tip}\n"

        response += "\n💡 <b>Aplique as dicas gradualmente e teste após cada mudança</b>"

        return response

    def _format_troubleshooting_response(
        self,
        steps: List[str],
        connection_type: ConnectionType
    ) -> str:
        """Formata resposta de troubleshooting."""
        connection_names = {
            ConnectionType.WIFI: "WiFi",
            ConnectionType.ETHERNET: "Ethernet (Cabo)",
            ConnectionType.MOBILE_DATA: "Dados Móveis"
        }

        name = connection_names.get(connection_type, connection_type.value)

        response = f"🔧 <b>TROUBLESHOOTING - {name}</b>\n\n"
        response += f"📋 <b>Passos a seguir:</b>\n\n"

        for step in steps:
            response += f"{step}\n"

        response += "\n✅ <b>Execute os passos em ordem e teste após cada um</b>"

        return response

    def _build_complete_solution(
        self,
        diagnosis: GamingDiagnosisResult,
        game_title: Optional[GameTitle]
    ) -> str:
        """Monta solução completa para ticket."""
        response = "🎯 <b>ANÁLISE COMPLETA E SOLUÇÃO SUGERIDA</b>\n\n"

        response += diagnosis.formatted_response

        response += "\n\n"
        response += "📞 <b>PRÓXIMOS PASSOS:</b>\n"
        response += "1. Aplique as recomendações listadas acima\n"
        response += "2. Teste por 15-30 minutos\n"
        response += "3. Se problema persistir, reabra o ticket com:\n"
        response += "   • Quais soluções você tentou\n"
        response += "   • Screenshots de erros\n"
        response += "   • Resultado de testes (ping, traceroute)\n\n"

        response += "✅ <b>Equipe OnCabo Gaming - Suporte Técnico</b>"

        return response
