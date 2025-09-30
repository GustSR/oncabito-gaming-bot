"""
Gaming Diagnostic Service.

Serviço de domínio para diagnósticos específicos de problemas gaming.
"""

import logging
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class GamePlatform(Enum):
    """Plataformas de jogos suportadas."""

    PC = "pc"
    CONSOLE = "console"
    MOBILE = "mobile"
    WEB = "web"


class ConnectionType(Enum):
    """Tipos de conexão."""

    WIFI = "wifi"
    ETHERNET = "ethernet"
    MOBILE_DATA = "mobile_data"


@dataclass
class DiagnosticResult:
    """Resultado de diagnóstico."""

    issue_detected: str
    severity: str  # low, medium, high, critical
    likely_cause: str
    recommendations: List[str]
    technical_details: Optional[str] = None


class GamingDiagnosticService:
    """
    Serviço de domínio para diagnósticos gaming.

    Analisa problemas relatados e fornece diagnósticos
    específicos baseados em padrões conhecidos.
    """

    # Padrões de problemas conhecidos
    LATENCY_PATTERNS = {
        'high_ping': {
            'keywords': ['lag', 'ping alto', 'delay', 'latência', 'travando'],
            'severity': 'high',
            'causes': [
                'Distância do servidor',
                'Conexão WiFi instável',
                'Congestionamento de rede',
                'QoS não configurado'
            ]
        },
        'packet_loss': {
            'keywords': ['perdendo pacote', 'desconecta', 'timeout', 'rubber band'],
            'severity': 'critical',
            'causes': [
                'Perda de pacotes na rede',
                'Problemas no roteador',
                'Interferência WiFi',
                'Cabo ethernet defeituoso'
            ]
        }
    }

    CONNECTION_PATTERNS = {
        'cannot_connect': {
            'keywords': ['não conecta', 'não entra', 'connection failed', 'timeout'],
            'severity': 'critical',
            'causes': [
                'Firewall bloqueando',
                'Portas não abertas',
                'DNS incorreto',
                'Servidor em manutenção'
            ]
        },
        'frequent_disconnects': {
            'keywords': ['cai', 'desconecta', 'disconnect', 'kicked'],
            'severity': 'high',
            'causes': [
                'Instabilidade de conexão',
                'NAT restritivo',
                'Timeout do servidor',
                'Problema com IP dinâmico'
            ]
        }
    }

    PERFORMANCE_PATTERNS = {
        'low_fps': {
            'keywords': ['fps baixo', 'travando', 'lento', 'engasga'],
            'severity': 'medium',
            'causes': [
                'Hardware insuficiente',
                'Drivers desatualizados',
                'Superaquecimento',
                'Processos em background'
            ]
        },
        'stuttering': {
            'keywords': ['stuttering', 'engasgo', 'freeze', 'trava'],
            'severity': 'high',
            'causes': [
                'RAM insuficiente',
                'Disco lento (HDD)',
                'Background downloads',
                'Problemas de shader'
            ]
        }
    }

    def diagnose_from_description(
        self,
        problem_description: str,
        game_title: Optional[str] = None,
        platform: Optional[GamePlatform] = None
    ) -> List[DiagnosticResult]:
        """
        Analisa descrição e retorna possíveis diagnósticos.

        Args:
            problem_description: Descrição do problema
            game_title: Nome do jogo (opcional)
            platform: Plataforma (opcional)

        Returns:
            List[DiagnosticResult]: Lista de diagnósticos possíveis
        """
        try:
            logger.info(f"Iniciando diagnóstico para: {problem_description[:50]}...")

            description_lower = problem_description.lower()
            results = []

            # Verifica padrões de latência
            latency_results = self._check_latency_issues(description_lower)
            results.extend(latency_results)

            # Verifica padrões de conexão
            connection_results = self._check_connection_issues(description_lower)
            results.extend(connection_results)

            # Verifica padrões de performance
            performance_results = self._check_performance_issues(description_lower)
            results.extend(performance_results)

            # Se não encontrou padrões, retorna diagnóstico genérico
            if not results:
                results.append(self._generic_diagnostic(problem_description))

            # Adiciona recomendações específicas do jogo se disponível
            if game_title:
                results = self._enhance_with_game_specific_tips(results, game_title)

            logger.info(f"Diagnóstico concluído: {len(results)} possíveis causas")
            return results

        except Exception as e:
            logger.error(f"Erro ao diagnosticar problema: {e}")
            return [self._generic_diagnostic(problem_description)]

    def get_optimization_tips(
        self,
        game_title: str,
        platform: GamePlatform
    ) -> List[str]:
        """
        Retorna dicas de otimização para jogo específico.

        Args:
            game_title: Nome do jogo
            platform: Plataforma

        Returns:
            List[str]: Lista de dicas
        """
        game_lower = game_title.lower()
        tips = []

        # Dicas gerais por plataforma
        if platform == GamePlatform.PC:
            tips.extend([
                "✅ Atualize drivers gráficos para a versão mais recente",
                "✅ Desative programas em background (Discord overlay, gravadores)",
                "✅ Configure prioridade do processo como 'Alto' no Gerenciador",
                "✅ Verifique temperatura da GPU/CPU durante gameplay"
            ])
        elif platform == GamePlatform.CONSOLE:
            tips.extend([
                "✅ Use conexão Ethernet ao invés de WiFi",
                "✅ Libere espaço de armazenamento (mínimo 10% livre)",
                "✅ Limpe cache do sistema periodicamente",
                "✅ Mantenha sistema atualizado"
            ])

        # Dicas específicas por jogo
        game_specific = self._get_game_specific_tips(game_lower)
        tips.extend(game_specific)

        return tips

    def get_connection_troubleshooting(
        self,
        connection_type: ConnectionType
    ) -> List[str]:
        """
        Retorna passos de troubleshooting para tipo de conexão.

        Args:
            connection_type: Tipo de conexão

        Returns:
            List[str]: Lista de passos
        """
        if connection_type == ConnectionType.WIFI:
            return [
                "1. Aproxime-se do roteador ou use repetidor",
                "2. Troque para canal menos congestionado (use app WiFi Analyzer)",
                "3. Use banda 5GHz se disponível (menos interferência)",
                "4. Desabilite outros dispositivos conectados durante gameplay",
                "5. Considere upgrade para roteador gaming (QoS inteligente)"
            ]
        elif connection_type == ConnectionType.ETHERNET:
            return [
                "1. Teste com outro cabo ethernet (Cat 5e ou superior)",
                "2. Conecte direto no modem (bypass roteador temporário)",
                "3. Verifique luz indicadora de link na porta",
                "4. Teste em outra porta do roteador/switch",
                "5. Atualize firmware do roteador"
            ]
        else:  # MOBILE_DATA
            return [
                "1. Verifique cobertura 4G/5G na região",
                "2. Desabilite economia de dados para jogos",
                "3. Use DNS alternativo (1.1.1.1 ou 8.8.8.8)",
                "4. Evite horários de pico (18h-22h)",
                "5. Considere plano com prioridade de tráfego"
            ]

    # Private helper methods

    def _check_latency_issues(self, description: str) -> List[DiagnosticResult]:
        """Verifica problemas de latência."""
        results = []

        for issue_type, pattern in self.LATENCY_PATTERNS.items():
            if any(keyword in description for keyword in pattern['keywords']):
                recommendations = [
                    "📊 Teste sua latência: ping 8.8.8.8 -t",
                    "🔌 Prefira conexão Ethernet ao invés de WiFi",
                    "📡 Conecte em servidor mais próximo geograficamente",
                    "⚙️ Configure QoS no roteador priorizando tráfego gaming",
                    "🔄 Reinicie modem e roteador (power cycle completo)"
                ]

                results.append(DiagnosticResult(
                    issue_detected=f"Problema de Latência: {issue_type.replace('_', ' ').title()}",
                    severity=pattern['severity'],
                    likely_cause=pattern['causes'][0],
                    recommendations=recommendations,
                    technical_details=f"Possíveis causas: {', '.join(pattern['causes'])}"
                ))

        return results

    def _check_connection_issues(self, description: str) -> List[DiagnosticResult]:
        """Verifica problemas de conexão."""
        results = []

        for issue_type, pattern in self.CONNECTION_PATTERNS.items():
            if any(keyword in description for keyword in pattern['keywords']):
                recommendations = [
                    "🔓 Abra portas necessárias no roteador",
                    "🛡️ Adicione jogo como exceção no firewall",
                    "🌐 Teste DNS alternativo (1.1.1.1 ou 8.8.8.8)",
                    "🔄 Configure NAT para tipo Aberto/Moderado",
                    "📞 Contate suporte se problema persistir"
                ]

                results.append(DiagnosticResult(
                    issue_detected=f"Problema de Conexão: {issue_type.replace('_', ' ').title()}",
                    severity=pattern['severity'],
                    likely_cause=pattern['causes'][0],
                    recommendations=recommendations,
                    technical_details=f"Possíveis causas: {', '.join(pattern['causes'])}"
                ))

        return results

    def _check_performance_issues(self, description: str) -> List[DiagnosticResult]:
        """Verifica problemas de performance."""
        results = []

        for issue_type, pattern in self.PERFORMANCE_PATTERNS.items():
            if any(keyword in description for keyword in pattern['keywords']):
                recommendations = [
                    "🎮 Reduza configurações gráficas (sombras, anti-aliasing)",
                    "🖥️ Atualize drivers gráficos",
                    "🌡️ Monitore temperaturas (use HWMonitor)",
                    "💾 Considere upgrade de RAM ou SSD",
                    "🔧 Desabilite VSync e limite de FPS"
                ]

                results.append(DiagnosticResult(
                    issue_detected=f"Problema de Performance: {issue_type.replace('_', ' ').title()}",
                    severity=pattern['severity'],
                    likely_cause=pattern['causes'][0],
                    recommendations=recommendations,
                    technical_details=f"Possíveis causas: {', '.join(pattern['causes'])}"
                ))

        return results

    def _generic_diagnostic(self, description: str) -> DiagnosticResult:
        """Retorna diagnóstico genérico."""
        return DiagnosticResult(
            issue_detected="Problema Gaming Geral",
            severity="medium",
            likely_cause="Causa ainda não identificada",
            recommendations=[
                "📝 Forneça mais detalhes: quando ocorre, frequência, mensagens de erro",
                "🔍 Verifique logs do jogo em busca de erros",
                "🔄 Reinicie jogo e sistema",
                "✅ Verifique integridade dos arquivos do jogo",
                "📞 Entre em contato com suporte técnico com mais informações"
            ],
            technical_details="Análise automática não detectou padrão específico"
        )

    def _enhance_with_game_specific_tips(
        self,
        results: List[DiagnosticResult],
        game_title: str
    ) -> List[DiagnosticResult]:
        """Adiciona dicas específicas do jogo aos resultados."""
        # Em produção, teria base de dados de dicas por jogo
        # Por enquanto, apenas retorna os resultados
        return results

    def _get_game_specific_tips(self, game_title: str) -> List[str]:
        """Retorna dicas específicas do jogo."""
        # Mapeamento de jogos populares
        game_tips = {
            'valorant': [
                "🎯 Use taxa de atualização nativa do monitor",
                "🖱️ Desabilite aceleração do mouse no Windows",
                "📊 Configure FOV adequado para seu estilo"
            ],
            'fortnite': [
                "🏗️ Use modo Performance ao invés de DX12",
                "📦 Desabilite replays automáticos",
                "🎨 Configure Distance View como Medium"
            ],
            'league of legends': [
                "⚡ Desabilite sombras de personagens",
                "🖼️ Use modo Borderless Window",
                "📉 Reduza qualidade de efeitos"
            ],
            'cs:go': [
                "📊 Use launch options: -tickrate 128 -novid",
                "🖱️ Desabilite Xbox DVR do Windows",
                "🔊 Configure áudio para Headphones"
            ]
        }

        for game_key, tips in game_tips.items():
            if game_key in game_title:
                return tips

        return ["💡 Consulte guias de otimização específicos do jogo"]
