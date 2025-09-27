import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

class HubSoftMonitorService:
    """
    Serviço de monitoramento contínuo da conectividade HubSoft
    e execução automática de sincronização e recovery.
    """

    def __init__(self):
        self._monitoring_task = None
        self._is_monitoring = False
        self._last_status = None
        self._monitor_interval = 300  # 5 minutos
        self._quick_check_interval = 60  # 1 minuto para checks rápidos
        self._recovery_in_progress = False

    async def start_monitoring(self):
        """Inicia o monitoramento contínuo do HubSoft"""
        if self._is_monitoring:
            logger.warning("Monitoramento HubSoft já está ativo")
            return

        try:
            from src.sentinela.core.config import HUBSOFT_ENABLED

            if not HUBSOFT_ENABLED:
                logger.info("HubSoft desabilitado - monitoramento não iniciado")
                return

            self._is_monitoring = True
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())
            logger.info("🔄 Monitoramento HubSoft iniciado")

        except Exception as e:
            logger.error(f"Erro ao iniciar monitoramento HubSoft: {e}")
            self._is_monitoring = False

    async def stop_monitoring(self):
        """Para o monitoramento contínuo"""
        if not self._is_monitoring:
            return

        self._is_monitoring = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass

        logger.info("⏹️ Monitoramento HubSoft parado")

    async def _monitoring_loop(self):
        """Loop principal de monitoramento"""
        logger.info("🎯 Iniciando loop de monitoramento HubSoft")

        while self._is_monitoring:
            try:
                await self._perform_health_check()
                await asyncio.sleep(self._monitor_interval)

            except asyncio.CancelledError:
                logger.info("Monitoramento HubSoft cancelado")
                break
            except Exception as e:
                logger.error(f"Erro no loop de monitoramento HubSoft: {e}")
                # Em caso de erro, aguarda menos tempo antes de tentar novamente
                await asyncio.sleep(60)

    async def _perform_health_check(self):
        """Executa verificação de saúde e ações baseadas no status"""
        try:
            from src.sentinela.services.hubsoft_sync_service import hubsoft_sync_service

            # Executa health check
            is_online = await hubsoft_sync_service.check_hubsoft_health()
            current_time = datetime.now()

            # Detecta mudança de status
            status_changed = self._last_status is not None and self._last_status != is_online

            if status_changed:
                if is_online:
                    # HubSoft voltou online
                    await self._handle_hubsoft_back_online()
                else:
                    # HubSoft ficou offline
                    await self._handle_hubsoft_went_offline()

            # Executa ações regulares baseadas no status
            if is_online:
                await self._handle_online_maintenance()
            else:
                await self._handle_offline_maintenance()

            self._last_status = is_online

            # Log de status (apenas a cada 30 minutos para não poluir)
            if current_time.minute % 30 == 0:
                status_text = "ONLINE" if is_online else "OFFLINE"
                logger.info(f"🔍 HubSoft Health Check: {status_text}")

        except Exception as e:
            logger.error(f"Erro durante health check automático: {e}")

    async def _handle_hubsoft_back_online(self):
        """Executa ações quando HubSoft volta online"""
        logger.info("🟢 HubSoft voltou ONLINE - iniciando processo de recovery")

        try:
            # Evita múltiplos recovery simultâneos
            if self._recovery_in_progress:
                logger.info("Recovery já em andamento - pulando")
                return

            self._recovery_in_progress = True

            # Notifica admins sobre volta online
            await self._notify_admins_status_change("online")

            # Inicia recovery de tickets offline
            await self._execute_automatic_recovery()

        except Exception as e:
            logger.error(f"Erro durante processo de recovery: {e}")
        finally:
            self._recovery_in_progress = False

    async def _handle_hubsoft_went_offline(self):
        """Executa ações quando HubSoft fica offline"""
        logger.warning("🔴 HubSoft ficou OFFLINE")

        try:
            # Notifica admins sobre indisponibilidade
            await self._notify_admins_status_change("offline")

            # Ativa monitoramento mais frequente quando offline
            logger.info("Ativando verificações mais frequentes durante indisponibilidade")

        except Exception as e:
            logger.error(f"Erro ao processar HubSoft offline: {e}")

    async def _handle_online_maintenance(self):
        """Executa manutenção regular quando HubSoft está online"""
        try:
            current_time = datetime.now()

            # Sincronização automática a cada 15 minutos
            if current_time.minute % 15 == 0:
                logger.info("🔄 Executando sincronização automática de status")
                from src.sentinela.services.hubsoft_sync_service import hubsoft_sync_service
                await hubsoft_sync_service.sync_all_active_tickets_status()

            # Verifica tickets offline para recovery a cada 30 minutos
            if current_time.minute % 30 == 0:
                from src.sentinela.clients.db_client import get_offline_tickets
                offline_count = len(get_offline_tickets())

                if offline_count > 0:
                    logger.info(f"📤 {offline_count} tickets offline encontrados - iniciando recovery")
                    await self._execute_automatic_recovery()

        except Exception as e:
            logger.error(f"Erro durante manutenção online: {e}")

    async def _handle_offline_maintenance(self):
        """Executa manutenção quando HubSoft está offline"""
        try:
            # Verifica se é uma indisponibilidade prolongada
            # Se offline por mais de 1 hora, verifica com mais frequência
            # (Esta lógica pode ser expandida conforme necessário)
            pass

        except Exception as e:
            logger.error(f"Erro durante manutenção offline: {e}")

    async def _execute_automatic_recovery(self):
        """Executa recovery automático de tickets offline"""
        try:
            from src.sentinela.services.hubsoft_sync_service import hubsoft_sync_service

            logger.info("🚀 Iniciando recovery automático de tickets offline")

            # Executa sincronização de tickets offline
            result = await hubsoft_sync_service.sync_offline_tickets_to_hubsoft()

            if result.get("status") == "completed":
                stats = result.get("results", {})
                success_count = stats.get("success_count", 0)
                failed_count = stats.get("failed_count", 0)

                if success_count > 0:
                    logger.info(f"✅ Recovery automático: {success_count} tickets sincronizados")
                    await self._notify_admins_recovery_success(success_count, failed_count)

                if failed_count > 0:
                    logger.warning(f"⚠️ Recovery automático: {failed_count} tickets falharam")

            else:
                logger.error(f"❌ Falha no recovery automático: {result.get('message', 'Erro desconhecido')}")

        except Exception as e:
            logger.error(f"Erro durante recovery automático: {e}")

    async def _notify_admins_status_change(self, new_status: str):
        """Notifica administradores sobre mudança de status do HubSoft"""
        try:
            from src.sentinela.core.config import ADMIN_USER_IDS, TELEGRAM_TOKEN
            from telegram import Bot

            if not ADMIN_USER_IDS:
                return

            status_icon = "🟢" if new_status == "online" else "🔴"
            status_text = "ONLINE" if new_status == "online" else "OFFLINE"

            message = (
                f"{status_icon} <b>ALERTA - MUDANÇA DE STATUS HUBSOFT</b>\n\n"
                f"📡 <b>Status:</b> {status_text}\n"
                f"⏰ <b>Detectado:</b> {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}\n\n"
            )

            if new_status == "online":
                message += (
                    "✅ <b>Sistema voltou online!</b>\n"
                    "🔄 Recovery automático foi iniciado\n"
                    "📊 Tickets offline serão sincronizados automaticamente"
                )
            else:
                message += (
                    "⚠️ <b>Sistema indisponível</b>\n"
                    "💾 Tickets continuarão sendo criados localmente\n"
                    "🔄 Sincronização automática quando voltar online"
                )

            # Envia para todos os admins
            bot = Bot(token=TELEGRAM_TOKEN)
            async with bot:
                for admin_id in ADMIN_USER_IDS:
                    try:
                        await bot.send_message(
                            chat_id=admin_id,
                            text=message,
                            parse_mode='HTML'
                        )
                    except Exception as e:
                        logger.warning(f"Erro ao notificar admin {admin_id}: {e}")

        except Exception as e:
            logger.error(f"Erro ao notificar admins sobre mudança de status: {e}")

    async def _notify_admins_recovery_success(self, success_count: int, failed_count: int):
        """Notifica administradores sobre sucesso no recovery"""
        try:
            from src.sentinela.core.config import ADMIN_USER_IDS, TELEGRAM_TOKEN
            from telegram import Bot

            if not ADMIN_USER_IDS or success_count == 0:
                return

            message = (
                f"🚀 <b>RECOVERY AUTOMÁTICO CONCLUÍDO</b>\n\n"
                f"✅ <b>Tickets sincronizados:</b> {success_count}\n"
            )

            if failed_count > 0:
                message += f"⚠️ <b>Falhas:</b> {failed_count}\n"

            message += (
                f"⏰ <b>Executado:</b> {datetime.now().strftime('%d/%m/%Y às %H:%M')}\n\n"
                f"💡 <b>Todos os tickets offline foram processados automaticamente!</b>"
            )

            # Envia apenas para o primeiro admin para não spammar
            bot = Bot(token=TELEGRAM_TOKEN)
            async with bot:
                try:
                    await bot.send_message(
                        chat_id=ADMIN_USER_IDS[0],
                        text=message,
                        parse_mode='HTML'
                    )
                except Exception as e:
                    logger.warning(f"Erro ao notificar admin sobre recovery: {e}")

        except Exception as e:
            logger.error(f"Erro ao notificar recovery success: {e}")

    def get_monitoring_status(self) -> dict:
        """Retorna status atual do monitoramento"""
        return {
            "is_monitoring": self._is_monitoring,
            "last_status": self._last_status,
            "recovery_in_progress": self._recovery_in_progress,
            "monitor_interval": self._monitor_interval,
            "started_at": getattr(self, '_started_at', None)
        }

# Instância global do serviço de monitoramento
hubsoft_monitor_service = HubSoftMonitorService()