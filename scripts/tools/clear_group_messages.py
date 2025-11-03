#!/usr/bin/env python3
"""
Script para limpar TODAS as mensagens do grupo EXCETO as fixadas.

ATENÇÃO: Este script deleta mensagens permanentemente!
Use com cuidado e apenas quando realmente necessário.

Uso:
    python3 scripts/tools/clear_group_messages.py [--dry-run] [--limit LIMIT]

Opções:
    --dry-run    Mostra o que seria deletado sem realmente deletar
    --limit N    Limita quantas mensagens processar (padrão: 1000)
"""

import sys
import os
import asyncio
import argparse
from pathlib import Path
from datetime import datetime

# Adiciona o diretório raiz ao path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

from telegram import Bot
from telegram.error import TelegramError
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

async def clear_group_messages(dry_run: bool = True, limit: int = 1000):
    """
    Deleta todas as mensagens do grupo exceto as fixadas.

    Args:
        dry_run: Se True, apenas mostra o que seria deletado
        limit: Número máximo de mensagens a processar
    """
    # Configuração
    token = os.getenv("TELEGRAM_TOKEN")
    group_id_str = os.getenv("TELEGRAM_GROUP_ID", "0").strip('"').strip("'")
    group_id = int(group_id_str)

    if not token or not group_id:
        print("❌ ERRO: TELEGRAM_TOKEN e TELEGRAM_GROUP_ID são obrigatórios")
        sys.exit(1)

    bot = Bot(token=token)

    print("=" * 60)
    print("🧹 LIMPEZA DE MENSAGENS DO GRUPO")
    print("=" * 60)
    print(f"📅 Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"🆔 Group ID: {group_id}")
    print(f"🔍 Modo: {'DRY RUN (simulação)' if dry_run else 'PRODUÇÃO (deletando)'}")
    print(f"📊 Limite: {limit} mensagens")
    print("=" * 60)
    print()

    try:
        # Busca informações do grupo
        chat = await bot.get_chat(group_id)
        print(f"✅ Grupo encontrado: {chat.title}")
        print()

        # Busca mensagens fixadas
        pinned_message = chat.pinned_message
        pinned_ids = []

        if pinned_message:
            pinned_ids.append(pinned_message.message_id)
            print(f"📌 Mensagem fixada encontrada: ID {pinned_message.message_id}")
            print()
        else:
            print("⚠️  Nenhuma mensagem fixada encontrada")
            print()

        # O Telegram API não tem método direto para listar todas as mensagens
        # Precisamos conhecer o range de IDs ou usar getUpdates
        # Vamos usar uma abordagem iterativa

        print("🔍 Buscando mensagens para deletar...")
        print()

        # Estratégia: tenta deletar mensagens em um range de IDs
        # Pega a última mensagem visível e tenta deletar de trás pra frente

        # Envia mensagem temporária para saber o ID atual
        temp_msg = await bot.send_message(
            chat_id=group_id,
            text="🔍 Detectando range de mensagens... (será deletada)"
        )
        current_id = temp_msg.message_id
        await bot.delete_message(chat_id=group_id, message_id=current_id)

        print(f"📊 ID da última mensagem: {current_id}")
        print(f"🎯 Tentando deletar mensagens do ID 1 até {current_id}")
        print()

        deleted_count = 0
        skipped_count = 0
        error_count = 0

        # Itera do ID mais recente para o mais antigo
        for message_id in range(current_id, max(0, current_id - limit), -1):
            # Pula mensagens fixadas
            if message_id in pinned_ids:
                print(f"📌 Pulando mensagem fixada: ID {message_id}")
                skipped_count += 1
                continue

            try:
                if dry_run:
                    # Modo simulação: só tenta pegar a mensagem
                    try:
                        # Não há método direto para checar se existe
                        # Então tentamos deletar mesmo em dry-run (mas não deletamos de verdade)
                        print(f"[DRY-RUN] Deletaria mensagem ID {message_id}")
                        deleted_count += 1
                    except:
                        pass
                else:
                    # Modo produção: realmente deleta
                    await bot.delete_message(chat_id=group_id, message_id=message_id)
                    deleted_count += 1

                    if deleted_count % 10 == 0:
                        print(f"🗑️  Deletadas {deleted_count} mensagens...")

                    # Rate limit: aguarda um pouco para não bater nos limites do Telegram
                    await asyncio.sleep(0.1)

            except TelegramError as e:
                # Mensagem não existe ou não pode ser deletada
                if "message to delete not found" in str(e).lower():
                    # Mensagem não existe, não precisa logar
                    pass
                elif "message can't be deleted" in str(e).lower():
                    # Não pode deletar (ex: muito antiga)
                    error_count += 1
                else:
                    # Outro erro
                    error_count += 1
                    if error_count < 5:  # Mostra apenas primeiros erros
                        print(f"⚠️  Erro ao deletar ID {message_id}: {e}")

            except Exception as e:
                print(f"❌ Erro inesperado no ID {message_id}: {e}")
                error_count += 1

        print()
        print("=" * 60)
        print("📊 RESULTADO FINAL")
        print("=" * 60)
        print(f"✅ Mensagens deletadas: {deleted_count}")
        print(f"📌 Mensagens fixadas puladas: {skipped_count}")
        print(f"⚠️  Erros/não encontradas: {error_count}")
        print()

        if dry_run:
            print("⚠️  MODO DRY-RUN: Nenhuma mensagem foi realmente deletada")
            print("💡 Execute sem --dry-run para deletar de verdade")
        else:
            print("✅ LIMPEZA CONCLUÍDA!")

        print("=" * 60)

    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        # Fecha sessão do bot
        try:
            if hasattr(bot, '_request'):
                request = bot._request
                if hasattr(request, '_client') and request._client:
                    await request._client.aclose()
        except:
            pass


def main():
    parser = argparse.ArgumentParser(
        description="Limpa mensagens do grupo Telegram (exceto fixadas)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Modo simulação (não deleta realmente)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=1000,
        help="Número máximo de mensagens a processar (padrão: 1000)"
    )

    args = parser.parse_args()

    # Confirmação em modo produção
    if not args.dry_run:
        print("⚠️  ATENÇÃO: Você está prestes a DELETAR mensagens do grupo!")
        print("⚠️  Esta ação é IRREVERSÍVEL!")
        print()
        confirm = input("Digite 'CONFIRMO' para continuar: ")
        if confirm != "CONFIRMO":
            print("❌ Operação cancelada")
            sys.exit(0)
        print()

    asyncio.run(clear_group_messages(dry_run=args.dry_run, limit=args.limit))


if __name__ == "__main__":
    main()
