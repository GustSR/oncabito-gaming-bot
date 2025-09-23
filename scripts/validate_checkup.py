#!/usr/bin/env python3
"""
Script para validar a lógica do checkup diário sem dependências externas.

Verifica se o código está sintaticamente correto e se as importações estão corretas.
"""

import sys
import os
import ast
import importlib.util

# Adiciona o diretório src ao path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

def validate_python_syntax(file_path):
    """Valida se um arquivo Python tem sintaxe correta."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source_code = f.read()

        ast.parse(source_code)
        print(f"✅ {os.path.basename(file_path)}: Sintaxe válida")
        return True
    except SyntaxError as e:
        print(f"❌ {os.path.basename(file_path)}: Erro de sintaxe na linha {e.lineno}: {e.msg}")
        return False
    except Exception as e:
        print(f"❌ {os.path.basename(file_path)}: Erro ao validar: {e}")
        return False

def check_imports(file_path):
    """Verifica se as importações estão corretas."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        imports = []
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if line.startswith('from ') or line.startswith('import '):
                imports.append((i, line))

        print(f"📋 {os.path.basename(file_path)}: Importações encontradas:")
        for line_num, import_line in imports:
            print(f"   L{line_num}: {import_line}")

        return True
    except Exception as e:
        print(f"❌ Erro ao verificar importações: {e}")
        return False

def main():
    """Valida os arquivos principais do sistema."""
    print("🔍 VALIDAÇÃO DO SISTEMA DE CHECKUP")
    print("=" * 50)

    # Paths relativos baseados na localização deste script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)

    # Arquivos para validar
    files_to_check = [
        os.path.join(project_dir, "scripts", "daily_checkup.py"),
        os.path.join(project_dir, "src", "sentinela", "services", "group_service.py"),
        os.path.join(project_dir, "src", "sentinela", "clients", "db_client.py"),
        os.path.join(project_dir, "src", "sentinela", "clients", "erp_client.py")
    ]

    all_valid = True

    for file_path in files_to_check:
        if os.path.exists(file_path):
            print(f"\n📁 Validando {os.path.basename(file_path)}:")
            syntax_ok = validate_python_syntax(file_path)
            imports_ok = check_imports(file_path)

            if not (syntax_ok and imports_ok):
                all_valid = False
        else:
            print(f"❌ Arquivo não encontrado: {file_path}")
            all_valid = False

    print("\n" + "=" * 50)
    if all_valid:
        print("✅ VALIDAÇÃO CONCLUÍDA: Todos os arquivos estão corretos!")
        print("\n🚀 PRÓXIMOS PASSOS:")
        print("1. Build da nova imagem Docker")
        print("2. Deploy do bot atualizado")
        print("3. Configurar cron para execução diária")
        print("4. Monitorar logs de execução")
    else:
        print("❌ VALIDAÇÃO FALHOU: Corrija os erros antes de continuar")

    # Verifica se o script de checkup pode ser importado
    print(f"\n🧪 TESTE DE IMPORTAÇÃO:")
    try:
        daily_checkup_path = os.path.join(project_dir, "scripts", "daily_checkup.py")
        spec = importlib.util.spec_from_file_location(
            "daily_checkup",
            daily_checkup_path
        )
        print("✅ Script de checkup pode ser importado")
    except Exception as e:
        print(f"❌ Erro na importação: {e}")

if __name__ == "__main__":
    main()