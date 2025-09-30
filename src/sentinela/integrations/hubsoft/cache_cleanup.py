#!/usr/bin/env python3
"""
Script de limpeza automática do cache HubSoft.

Este script deve ser executado periodicamente para:
- Remover entradas expiradas
- Gerar relatórios de performance do cache
- Monitorar uso de memória

Pode ser executado via cron ou chamado por outros serviços.
"""

import logging
import asyncio
from datetime import datetime
from .cache_manager import cache_manager, get_cache_stats, cleanup_cache

logger = logging.getLogger(__name__)


def run_cache_cleanup() -> dict:
    """
    Executa limpeza do cache e retorna estatísticas.

    Returns:
        dict: Relatório da limpeza
    """
    logger.info("Iniciando limpeza automática do cache HubSoft...")

    # Estatísticas antes da limpeza
    stats_before = get_cache_stats()

    # Remove entradas expiradas
    removed_count = cleanup_cache()

    # Estatísticas após limpeza
    stats_after = get_cache_stats()

    report = {
        'cleanup_time': datetime.now().isoformat(),
        'entries_removed': removed_count,
        'entries_before': stats_before['total_entries'],
        'entries_after': stats_after['total_entries'],
        'hit_rate': stats_after['hit_rate'],
        'total_hits': stats_after['hits'],
        'total_misses': stats_after['misses'],
        'memory_usage': stats_after['memory_usage_estimate'],
        'categories': stats_after['categories']
    }

    logger.info(f"Limpeza concluída: {removed_count} entradas removidas")
    logger.info(f"Cache stats: {stats_after['total_entries']} entradas, "
               f"hit rate: {stats_after['hit_rate']:.2%}")

    return report


def generate_cache_report() -> dict:
    """
    Gera relatório detalhado do cache.

    Returns:
        dict: Relatório completo do cache
    """
    stats = get_cache_stats()

    # Análise de eficiência
    efficiency_analysis = {
        'excellent': stats['hit_rate'] >= 0.8,
        'good': 0.6 <= stats['hit_rate'] < 0.8,
        'needs_improvement': stats['hit_rate'] < 0.6,
        'recommendations': []
    }

    # Recomendações baseadas nas estatísticas
    if stats['hit_rate'] < 0.6:
        efficiency_analysis['recommendations'].append(
            "Hit rate baixo - considere aumentar TTL para dados estáveis"
        )

    if stats['total_entries'] > stats['max_entries'] * 0.9:
        efficiency_analysis['recommendations'].append(
            "Cache próximo do limite - considere aumentar max_entries ou reduzir TTL"
        )

    if stats['evictions'] > stats['hits'] * 0.1:
        efficiency_analysis['recommendations'].append(
            "Muitas evicções - cache pode estar muito pequeno"
        )

    return {
        'report_time': datetime.now().isoformat(),
        'stats': stats,
        'efficiency': efficiency_analysis,
        'performance_grade': _calculate_performance_grade(stats)
    }


def _calculate_performance_grade(stats: dict) -> str:
    """
    Calcula nota de performance do cache.

    Args:
        stats: Estatísticas do cache

    Returns:
        str: Nota (A, B, C, D, F)
    """
    hit_rate = stats['hit_rate']

    if hit_rate >= 0.9:
        return 'A'  # Excelente
    elif hit_rate >= 0.8:
        return 'B'  # Muito bom
    elif hit_rate >= 0.7:
        return 'C'  # Bom
    elif hit_rate >= 0.6:
        return 'D'  # Satisfatório
    else:
        return 'F'  # Precisa melhorar


async def monitor_cache_health():
    """
    Monitora a saúde do cache em tempo real.

    Esta função pode ser executada em background para alertar
    sobre problemas de performance do cache.
    """
    while True:
        try:
            stats = get_cache_stats()

            # Verifica condições de alerta
            if stats['hit_rate'] < 0.5:
                logger.warning(f"Cache hit rate muito baixo: {stats['hit_rate']:.2%}")

            if stats['total_entries'] > stats['max_entries'] * 0.95:
                logger.warning(f"Cache quase cheio: {stats['total_entries']}/{stats['max_entries']}")

            # Aguarda 5 minutos antes da próxima verificação
            await asyncio.sleep(300)

        except Exception as e:
            logger.error(f"Erro no monitoramento do cache: {e}")
            await asyncio.sleep(60)  # Espera menos em caso de erro


def main():
    """Função principal do script de limpeza."""
    import sys
    import os

    # Configura logging se executado diretamente
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    if len(sys.argv) > 1 and sys.argv[1] == '--report':
        # Modo relatório
        report = generate_cache_report()
        print("=" * 50)
        print("RELATÓRIO DO CACHE HUBSOFT")
        print("=" * 50)
        print(f"Data/Hora: {report['report_time']}")
        print(f"Performance: {report['performance_grade']}")
        print(f"Hit Rate: {report['stats']['hit_rate']:.2%}")
        print(f"Entradas: {report['stats']['total_entries']}")
        print(f"Uso de Memória: {report['stats']['memory_usage_estimate']}")

        if report['efficiency']['recommendations']:
            print("\nRecomendações:")
            for rec in report['efficiency']['recommendations']:
                print(f"  • {rec}")

    else:
        # Modo limpeza
        report = run_cache_cleanup()
        print(f"Limpeza concluída: {report['entries_removed']} entradas removidas")


if __name__ == "__main__":
    main()