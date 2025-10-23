"""
Migration Manager.

Gerencia o processo de migração gradual do sistema legado
para a nova arquitetura, incluindo rollback e monitoring.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from enum import Enum
from dataclasses import dataclass

from ...infrastructure.config.dependency_injection import get_container

# Legacy adapter has been removed - 100% new architecture
def get_legacy_adapter_safe():
    """Legacy adapter has been removed - system now uses 100% new architecture."""
    return None

logger = logging.getLogger(__name__)


class MigrationPhase(Enum):
    """Fases da migração."""
    PREPARATION = "preparation"
    INFRASTRUCTURE = "infrastructure"
    SERVICES = "services"
    PRESENTATION = "presentation"
    VALIDATION = "validation"
    COMPLETE = "complete"


class MigrationStrategy(Enum):
    """Estratégias de migração."""
    BLUE_GREEN = "blue_green"
    CANARY = "canary"
    GRADUAL = "gradual"
    FEATURE_TOGGLE = "feature_toggle"


@dataclass
class MigrationStep:
    """Define um passo da migração."""
    name: str
    description: str
    phase: MigrationPhase
    execute_func: Callable
    rollback_func: Optional[Callable] = None
    validation_func: Optional[Callable] = None
    dependencies: List[str] = None
    timeout_seconds: int = 300
    critical: bool = False


@dataclass
class MigrationStatus:
    """Status da migração."""
    current_phase: MigrationPhase
    completed_steps: List[str]
    failed_steps: List[str]
    active_features: Dict[str, bool]
    rollback_available: bool
    health_check: Dict[str, Any]
    started_at: datetime
    last_update: datetime


class MigrationManager:
    """Gerenciador de migração do sistema."""

    def __init__(self):
        self._steps: Dict[str, MigrationStep] = {}
        self._status = MigrationStatus(
            current_phase=MigrationPhase.PREPARATION,
            completed_steps=[],
            failed_steps=[],
            active_features={},
            rollback_available=True,
            health_check={},
            started_at=datetime.now(),
            last_update=datetime.now()
        )
        self._feature_flags: Dict[str, bool] = {}
        self._rollback_points: List[Dict[str, Any]] = []

    def register_step(self, step: MigrationStep) -> None:
        """Registra um passo de migração."""
        self._steps[step.name] = step
        logger.info(f"Passo de migração registrado: {step.name}")

    def set_feature_flag(self, feature: str, enabled: bool) -> None:
        """Define flag de feature."""
        self._feature_flags[feature] = enabled
        self._status.active_features[feature] = enabled
        self._status.last_update = datetime.now()
        logger.info(f"Feature flag '{feature}' definida como {enabled}")

    def is_feature_enabled(self, feature: str) -> bool:
        """Verifica se feature está habilitada."""
        return self._feature_flags.get(feature, False)

    async def execute_migration(
        self,
        target_phase: MigrationPhase = MigrationPhase.COMPLETE,
        strategy: MigrationStrategy = MigrationStrategy.GRADUAL
    ) -> Dict[str, Any]:
        """Executa migração até fase target."""
        logger.info(f"Iniciando migração até fase {target_phase.value} com estratégia {strategy.value}")

        try:
            # Cria ponto de rollback
            await self._create_rollback_point()

            # Obtém passos para executar
            steps_to_execute = self._get_steps_for_phase(target_phase)

            results = []
            for step_name in steps_to_execute:
                if step_name in self._status.completed_steps:
                    continue

                step = self._steps[step_name]
                result = await self._execute_step(step, strategy)
                results.append(result)

                if not result["success"]:
                    if step.critical:
                        logger.error(f"Passo crítico falhou: {step_name}")
                        await self._handle_migration_failure(step_name)
                        break
                    else:
                        logger.warning(f"Passo não-crítico falhou: {step_name}")
                        self._status.failed_steps.append(step_name)

            # Atualiza status final
            self._update_migration_status()

            return {
                "success": len(self._status.failed_steps) == 0,
                "completed_steps": len(self._status.completed_steps),
                "failed_steps": len(self._status.failed_steps),
                "current_phase": self._status.current_phase.value,
                "results": results
            }

        except Exception as e:
            logger.error(f"Erro durante migração: {e}")
            return {
                "success": False,
                "error": str(e),
                "rollback_available": self._status.rollback_available
            }

    async def _execute_step(
        self,
        step: MigrationStep,
        strategy: MigrationStrategy
    ) -> Dict[str, Any]:
        """Executa um passo individual da migração."""
        logger.info(f"Executando passo: {step.name}")

        start_time = datetime.now()

        try:
            # Verifica dependências
            if step.dependencies:
                for dep in step.dependencies:
                    if dep not in self._status.completed_steps:
                        return {
                            "success": False,
                            "step": step.name,
                            "error": f"Dependência não satisfeita: {dep}"
                        }

            # Executa com timeout
            result = await asyncio.wait_for(
                step.execute_func(),
                timeout=step.timeout_seconds
            )

            # Valida resultado se função de validação existir
            if step.validation_func:
                validation_result = await step.validation_func()
                if not validation_result.get("success", True):
                    raise Exception(f"Validação falhou: {validation_result.get('error')}")

            # Marca como completado
            self._status.completed_steps.append(step.name)
            duration = (datetime.now() - start_time).total_seconds()

            logger.info(f"Passo {step.name} executado com sucesso em {duration:.2f}s")

            return {
                "success": True,
                "step": step.name,
                "duration": duration,
                "result": result
            }

        except asyncio.TimeoutError:
            error_msg = f"Timeout ao executar passo {step.name}"
            logger.error(error_msg)
            return {
                "success": False,
                "step": step.name,
                "error": error_msg
            }

        except Exception as e:
            error_msg = f"Erro ao executar passo {step.name}: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "step": step.name,
                "error": error_msg
            }

    async def rollback_migration(
        self,
        to_point: Optional[str] = None
    ) -> Dict[str, Any]:
        """Executa rollback da migração."""
        logger.warning("Iniciando rollback da migração")

        try:
            if not self._status.rollback_available:
                return {
                    "success": False,
                    "error": "Rollback não disponível"
                }

            # Determina ponto de rollback
            rollback_point = None
            if to_point:
                rollback_point = next(
                    (rp for rp in self._rollback_points if rp["name"] == to_point),
                    None
                )
            else:
                rollback_point = self._rollback_points[-1] if self._rollback_points else None

            if not rollback_point:
                return {
                    "success": False,
                    "error": "Ponto de rollback não encontrado"
                }

            # Executa rollback dos passos em ordem reversa
            steps_to_rollback = [
                step for step in reversed(self._status.completed_steps)
                if step not in rollback_point["completed_steps"]
            ]

            rollback_results = []
            for step_name in steps_to_rollback:
                step = self._steps.get(step_name)
                if step and step.rollback_func:
                    try:
                        result = await step.rollback_func()
                        rollback_results.append({
                            "step": step_name,
                            "success": True,
                            "result": result
                        })
                        self._status.completed_steps.remove(step_name)
                    except Exception as e:
                        rollback_results.append({
                            "step": step_name,
                            "success": False,
                            "error": str(e)
                        })

            # Restaura feature flags
            self._feature_flags = rollback_point["feature_flags"].copy()
            self._status.active_features = rollback_point["feature_flags"].copy()

            # Atualiza status
            self._status.current_phase = MigrationPhase(rollback_point["phase"])
            self._status.last_update = datetime.now()

            logger.info(f"Rollback executado para ponto: {rollback_point['name']}")

            return {
                "success": True,
                "rollback_point": rollback_point["name"],
                "steps_rolled_back": len(steps_to_rollback),
                "results": rollback_results
            }

        except Exception as e:
            logger.error(f"Erro durante rollback: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def health_check(self) -> Dict[str, Any]:
        """Executa health check completo do sistema."""
        logger.info("Executando health check da migração")

        try:
            health_data = {
                "timestamp": datetime.now().isoformat(),
                "migration_status": {
                    "current_phase": self._status.current_phase.value,
                    "completed_steps": len(self._status.completed_steps),
                    "failed_steps": len(self._status.failed_steps),
                    "active_features": self._status.active_features
                },
                "components": {}
            }

            # Testa nova arquitetura
            try:
                container = await get_container()
                health_data["components"]["new_architecture"] = {
                    "status": "healthy",
                    "available": True
                }

                # Testa HubSoft integration
                hubsoft_use_case = container.get("hubsoft_integration_use_case")
                hubsoft_health = await hubsoft_use_case.check_hubsoft_health()
                health_data["components"]["hubsoft_api"] = {
                    "status": "healthy" if hubsoft_health.success else "unhealthy",
                    "available": hubsoft_health.success,
                    "data": hubsoft_health.data
                }

            except Exception as e:
                health_data["components"]["new_architecture"] = {
                    "status": "unhealthy",
                    "available": False,
                    "error": str(e)
                }

            # Testa sistema legado
            try:
                adapter = get_legacy_adapter_safe()
                if adapter:
                    legacy_status = await adapter.get_system_status()
                    health_data["components"]["legacy_system"] = {
                        "status": "healthy",
                        "available": True,
                        "data": legacy_status
                    }
                else:
                    health_data["components"]["legacy_system"] = {
                        "status": "unavailable",
                        "available": False,
                        "message": "Legacy adapter not available (dependencies missing)"
                    }
            except Exception as e:
                health_data["components"]["legacy_system"] = {
                    "status": "unhealthy",
                    "available": False,
                    "error": str(e)
                }

            # Calcula status geral
            all_healthy = all(
                comp.get("status") == "healthy"
                for comp in health_data["components"].values()
            )

            health_data["overall_status"] = "healthy" if all_healthy else "degraded"
            self._status.health_check = health_data

            return health_data

        except Exception as e:
            logger.error(f"Erro no health check: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "overall_status": "unhealthy",
                "error": str(e)
            }

    async def _create_rollback_point(self) -> None:
        """Cria ponto de rollback."""
        rollback_point = {
            "name": f"rollback_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "timestamp": datetime.now().isoformat(),
            "phase": self._status.current_phase.value,
            "completed_steps": self._status.completed_steps.copy(),
            "feature_flags": self._feature_flags.copy()
        }

        self._rollback_points.append(rollback_point)

        # Mantém apenas últimos 5 pontos
        if len(self._rollback_points) > 5:
            self._rollback_points = self._rollback_points[-5:]

        logger.info(f"Ponto de rollback criado: {rollback_point['name']}")

    def _get_steps_for_phase(self, target_phase: MigrationPhase) -> List[str]:
        """Obtém passos necessários para chegar à fase target."""
        phase_order = [
            MigrationPhase.PREPARATION,
            MigrationPhase.INFRASTRUCTURE,
            MigrationPhase.SERVICES,
            MigrationPhase.PRESENTATION,
            MigrationPhase.VALIDATION,
            MigrationPhase.COMPLETE
        ]

        target_index = phase_order.index(target_phase)
        current_index = phase_order.index(self._status.current_phase)

        if target_index <= current_index:
            return []

        # Obtém passos das fases necessárias
        steps = []
        for phase in phase_order[current_index:target_index + 1]:
            phase_steps = [
                name for name, step in self._steps.items()
                if step.phase == phase
            ]
            steps.extend(sorted(phase_steps))

        return steps

    def _update_migration_status(self) -> None:
        """Atualiza status da migração baseado nos passos completados."""
        completed_by_phase = {}
        for phase in MigrationPhase:
            phase_steps = [
                name for name, step in self._steps.items()
                if step.phase == phase
            ]
            completed_phase_steps = [
                step for step in phase_steps
                if step in self._status.completed_steps
            ]
            completed_by_phase[phase] = len(completed_phase_steps) == len(phase_steps)

        # Determina fase atual
        for phase in reversed(list(MigrationPhase)):
            if completed_by_phase.get(phase, False):
                self._status.current_phase = phase
                break

        self._status.last_update = datetime.now()

    async def _handle_migration_failure(self, failed_step: str) -> None:
        """Trata falha em passo crítico."""
        logger.error(f"Tratando falha em passo crítico: {failed_step}")

        self._status.failed_steps.append(failed_step)

        # Considera rollback automático para passos críticos
        if self._status.rollback_available:
            logger.warning("Executando rollback automático devido a falha crítica")
            await self.rollback_migration()

    def get_status(self) -> Dict[str, Any]:
        """Obtém status atual da migração."""
        return {
            "current_phase": self._status.current_phase.value,
            "completed_steps": self._status.completed_steps,
            "failed_steps": self._status.failed_steps,
            "active_features": self._status.active_features,
            "rollback_available": self._status.rollback_available,
            "started_at": self._status.started_at.isoformat(),
            "last_update": self._status.last_update.isoformat(),
            "rollback_points": [rp["name"] for rp in self._rollback_points]
        }


# Instância global do migration manager
_migration_manager: Optional[MigrationManager] = None


def get_migration_manager() -> MigrationManager:
    """Obtém instância global do migration manager."""
    global _migration_manager

    if _migration_manager is None:
        _migration_manager = MigrationManager()

    return _migration_manager