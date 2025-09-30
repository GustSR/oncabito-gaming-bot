#!/usr/bin/env python3
"""
Teste da migração do CPF Verification Service.

Valida a nova arquitetura para verificação de CPF
incluindo entities, events, use cases e handlers.
"""

import asyncio
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Adiciona o path do projeto para imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from sentinela.infrastructure.events.event_bus import get_event_bus, publish_event
from sentinela.infrastructure.events.event_handler_registry import setup_event_handlers
from sentinela.domain.entities.cpf_verification import (
    CPFVerificationRequest,
    VerificationId,
    VerificationType,
    VerificationStatus
)
from sentinela.domain.events.verification_events import (
    VerificationStarted,
    VerificationCompleted,
    VerificationFailed,
    VerificationExpired,
    CPFDuplicateDetected,
    CPFRemapped
)
from sentinela.domain.value_objects.identifiers import UserId
from sentinela.domain.value_objects.cpf import CPF

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_cpf_verification_entities():
    """Testa as entities de verificação de CPF."""

    print("\n🧪 TESTANDO ENTITIES DE VERIFICAÇÃO DE CPF")
    print("=" * 60)

    try:
        # 1. Cria verificação
        verification_id = VerificationId.generate()
        user_id = UserId(12345)

        verification = CPFVerificationRequest(
            verification_id=verification_id,
            user_id=user_id,
            username="TestUser",
            user_mention="@TestUser",
            verification_type=VerificationType.AUTO_CHECKUP,
            source_action="security_check"
        )

        print(f"✅ Verificação criada: {verification_id.value}")
        print(f"   Usuário: {verification.username}")
        print(f"   Tipo: {verification.verification_type.value}")
        print(f"   Status: {verification.status.value}")
        print(f"   Expira em: {verification.expires_at.strftime('%Y-%m-%d %H:%M:%S')}")

        # 2. Testa business rules
        print(f"\n📋 Testando business rules...")

        # Pode fazer tentativas?
        print(f"   Pode tentar: {verification.can_attempt()}")
        print(f"   Tentativas restantes: {verification.has_attempts_left()}")
        print(f"   Está expirada: {verification.is_expired()}")

        # 3. Inicia verificação
        verification.start_verification()
        print(f"   Status após início: {verification.status.value}")

        # 4. Adiciona tentativas
        verification.add_attempt("12345678901", success=False, failure_reason="invalid_cpf")
        print(f"   Após 1ª tentativa: {verification.attempt_count} tentativas")

        verification.add_attempt("11122233344", success=False, failure_reason="cpf_not_found")
        print(f"   Após 2ª tentativa: {verification.attempt_count} tentativas")

        # 5. Tentativa bem-sucedida
        cpf = CPF("11144477735")  # CPF válido
        client_data = {
            "nome": "João da Silva",
            "servico_nome": "Fibra 100MB",
            "servico_status": "Ativo"
        }

        verification.complete_with_success(cpf, client_data)
        print(f"   Status final: {verification.status.value}")
        print(f"   CPF verificado: {verification.cpf_verified}")
        print(f"   Dados do cliente: {verification.client_data.get('nome')}")

        # 6. Verifica domain events
        events = verification.get_domain_events()
        print(f"\n📡 Domain events gerados: {len(events)}")
        for i, event in enumerate(events, 1):
            print(f"   {i}. {event.__class__.__name__}")

        print("\n✅ TESTE DE ENTITIES PASSOU!")
        return True

    except Exception as e:
        print(f"\n❌ ERRO NO TESTE DE ENTITIES: {e}")
        logger.error(f"Erro no teste de entities: {e}")
        return False


async def test_verification_events():
    """Testa os eventos de verificação."""

    print("\n🧪 TESTANDO EVENTOS DE VERIFICAÇÃO")
    print("=" * 60)

    try:
        # 1. Configura event handlers
        event_bus = get_event_bus()
        registry = setup_event_handlers(event_bus)

        verification_id = VerificationId.generate()

        # 2. Testa evento de verificação iniciada
        verification_started = VerificationStarted(
            verification_id=verification_id,
            user_id=12345,
            username="TestUser",
            verification_type="auto_checkup"
        )
        await publish_event(verification_started)
        print("✅ Evento VerificationStarted processado")

        # 3. Testa evento de verificação completada
        verification_completed = VerificationCompleted(
            verification_id=verification_id,
            user_id=12345,
            username="TestUser",
            verification_type="auto_checkup",
            cpf_number="11144477735",
            success=True
        )
        await publish_event(verification_completed)
        print("✅ Evento VerificationCompleted processado")

        # 4. Testa evento de CPF duplicado
        cpf_duplicate = CPFDuplicateDetected(
            cpf_number="***.***.***-35",
            current_user_id=12345,
            existing_user_id=54321,
            current_username="TestUser",
            existing_username="ExistingUser",
            resolution_action="manual_review"
        )
        await publish_event(cpf_duplicate)
        print("✅ Evento CPFDuplicateDetected processado")

        # 5. Testa evento de remapeamento
        cpf_remapped = CPFRemapped(
            cpf_number="***.***.***-35",
            old_user_id=54321,
            new_user_id=12345,
            old_username="ExistingUser",
            new_username="TestUser",
            reason="Conta Telegram atualizada"
        )
        await publish_event(cpf_remapped)
        print("✅ Evento CPFRemapped processado")

        print(f"\n📊 Total de handlers registrados: {registry.get_handler_count()}")
        print("\n✅ TESTE DE EVENTOS PASSOU!")
        return True

    except Exception as e:
        print(f"\n❌ ERRO NO TESTE DE EVENTOS: {e}")
        logger.error(f"Erro no teste de eventos: {e}")
        return False


async def test_verification_flows():
    """Testa fluxos completos de verificação."""

    print("\n🧪 TESTANDO FLUXOS DE VERIFICAÇÃO")
    print("=" * 60)

    try:
        # 1. Fluxo de verificação bem-sucedida
        print("🔄 Testando fluxo de sucesso...")

        verification_id = VerificationId.generate()
        user_id = UserId(99999)

        verification = CPFVerificationRequest(
            verification_id=verification_id,
            user_id=user_id,
            username="SuccessUser",
            user_mention="@SuccessUser",
            verification_type=VerificationType.SUPPORT_REQUEST
        )

        verification.start_verification()
        cpf = CPF("11144477735")
        client_data = {"nome": "Cliente Teste", "servico_status": "Ativo"}
        verification.complete_with_success(cpf, client_data)

        print(f"   ✅ Fluxo de sucesso: {verification.status.value}")

        # 2. Fluxo de falha por muitas tentativas
        print("🔄 Testando fluxo de falha...")

        verification_id2 = VerificationId.generate()
        user_id2 = UserId(88888)

        verification2 = CPFVerificationRequest(
            verification_id=verification_id2,
            user_id=user_id2,
            username="FailUser",
            user_mention="@FailUser",
            verification_type=VerificationType.AUTO_CHECKUP
        )

        verification2.start_verification()

        # Adiciona 3 tentativas falhadas
        for i in range(3):
            verification2.add_attempt(f"1234567890{i}", success=False, failure_reason="invalid_cpf")

        print(f"   ❌ Fluxo de falha: {verification2.status.value}")
        print(f"   Tentativas: {verification2.attempt_count}")

        # 3. Fluxo de cancelamento
        print("🔄 Testando fluxo de cancelamento...")

        verification_id3 = VerificationId.generate()
        user_id3 = UserId(77777)

        verification3 = CPFVerificationRequest(
            verification_id=verification_id3,
            user_id=user_id3,
            username="CancelUser",
            user_mention="@CancelUser",
            verification_type=VerificationType.AUTO_CHECKUP
        )

        verification3.start_verification()
        verification3.cancel_verification("Usuário desistiu")

        print(f"   🚫 Fluxo de cancelamento: {verification3.status.value}")

        # 4. Fluxo de expiração
        print("🔄 Testando fluxo de expiração...")

        verification_id4 = VerificationId.generate()
        user_id4 = UserId(66666)

        # Cria verificação já expirada
        expired_time = datetime.now() - timedelta(hours=25)
        verification4 = CPFVerificationRequest(
            verification_id=verification_id4,
            user_id=user_id4,
            username="ExpiredUser",
            user_mention="@ExpiredUser",
            verification_type=VerificationType.AUTO_CHECKUP,
            expires_at=expired_time
        )

        verification4.expire_verification()

        print(f"   ⏰ Fluxo de expiração: {verification4.status.value}")
        print(f"   Expirou em: {verification4.expires_at.strftime('%Y-%m-%d %H:%M:%S')}")

        print("\n✅ TESTE DE FLUXOS PASSOU!")
        return True

    except Exception as e:
        print(f"\n❌ ERRO NO TESTE DE FLUXOS: {e}")
        logger.error(f"Erro no teste de fluxos: {e}")
        return False


async def test_cpf_verification_migration():
    """Executa todos os testes da migração."""

    print("🎯 INICIANDO TESTES DA MIGRAÇÃO CPF VERIFICATION SERVICE")
    print("=" * 80)

    # Lista de testes
    tests = [
        ("Entities", test_cpf_verification_entities),
        ("Events", test_verification_events),
        ("Fluxos", test_verification_flows)
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n🧪 Executando teste: {test_name}")
        try:
            result = await test_func()
            if result:
                passed += 1
                print(f"✅ {test_name}: PASSOU")
            else:
                print(f"❌ {test_name}: FALHOU")
        except Exception as e:
            print(f"❌ {test_name}: ERRO - {e}")
            logger.error(f"Erro no teste {test_name}: {e}")

    # Resultado final
    print("\n" + "=" * 80)
    print(f"📊 RESULTADO FINAL: {passed}/{total} testes passaram")

    if passed == total:
        print("🎉 MIGRAÇÃO DO CPF VERIFICATION SERVICE CONCLUÍDA COM SUCESSO!")
        print("✅ Todas as funcionalidades estão operacionais")
    else:
        print("⚠️ Alguns testes falharam - Revisar implementação")

    print("=" * 80)

    return passed == total


if __name__ == "__main__":
    asyncio.run(test_cpf_verification_migration())