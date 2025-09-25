import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def mask_cpf(cpf: str) -> str:
    """
    Mascara CPF para conformidade LGPD.

    Args:
        cpf: CPF original

    Returns:
        str: CPF mascarado (ex: ***.***.***-10)
    """
    if cpf and len(cpf) == 11:
        return f"***.***.***.{cpf[-2:]}"
    return "***.***.***-**"

def format_client_service_info(client_data: dict) -> str:
    """
    Formata os dados do cliente em uma mensagem informativa (conforme LGPD).

    Args:
        client_data: Dados do cliente retornados pela API HubSoft

    Returns:
        str: Mensagem formatada com informações do serviço
    """
    try:
        # Informações básicas do cliente (LGPD - dados minimizados)
        nome = client_data.get('nome_razaosocial', 'Nome não informado')
        cpf = client_data.get('cpf_cnpj', '')
        cpf_mascarado = mask_cpf(cpf)

        # Informações do serviço
        servicos = client_data.get('servicos', [])
        if not servicos:
            return "❌ Nenhum serviço ativo encontrado."

        servico = servicos[0]  # Pega o primeiro serviço ativo
        nome_plano = servico.get('nome', 'Plano não informado')
        status = servico.get('status', 'Status não informado')
        tecnologia = servico.get('tecnologia', 'Não informado')

        # Data de habilitação
        data_habilitacao = servico.get('data_habilitacao_br', 'Não informado')

        # Endereço de instalação (LGPD - apenas bairro e cidade)
        endereco_info = "Não informado"
        if 'endereco_instalacao' in servico:
            endereco = servico['endereco_instalacao']
            bairro = endereco.get('bairro', '')
            cidade = endereco.get('cidade', '')
            uf = endereco.get('uf', '')
            if bairro and cidade:
                endereco_info = f"{bairro}, {cidade}/{uf}"
            elif cidade:
                endereco_info = f"{cidade}/{uf}"

        # Monta a mensagem (conforme LGPD)
        mensagem = f"""🎮 <b>CONTRATO VERIFICADO COM SUCESSO!</b>

👤 <b>IDENTIFICAÇÃO:</b>
📝 Nome: {nome}
🆔 CPF: {cpf_mascarado}

🌐 <b>DADOS DO SERVIÇO:</b>
📋 Plano: {nome_plano}
⚡ Status: {status}
🔧 Tecnologia: {tecnologia}
📅 Ativo desde: {data_habilitacao}

📍 <b>LOCALIZAÇÃO:</b>
{endereco_info}

---
💬 <b>PRÓXIMOS PASSOS:</b>
Seu contrato Gamer está ativo! Houve um problema técnico para gerar seu link automaticamente.

Entre em contato com nosso suporte para receber acesso ao <b>Grupo Gamer OnCabo</b>:

📞 <b>Contatos OnCabo:</b>
• WhatsApp: (99) 3199-4444
• Telefones: (99) 3014-0025 // 0800 099 0025
• Email: suporte@oncabo.com.br

🕐 <b>Horário de Atendimento:</b>
Segunda a Sexta: 8h às 00h
Sábado: 8h às 12h

🚀 <i>Aguardamos você na comunidade gamer!</i>

---
🔒 <i>Dados protegidos conforme LGPD</i>"""

        return mensagem

    except Exception as e:
        logger.error(f"Erro ao formatar informações do cliente: {e}")
        return "❌ Erro ao processar informações do cliente. Entre em contato com o suporte."

def format_client_service_summary(client_data: dict) -> str:
    """
    Formata um resumo simplificado dos dados do cliente.

    Args:
        client_data: Dados do cliente retornados pela API HubSoft

    Returns:
        str: Resumo formatado
    """
    try:
        nome = client_data.get('nome_razaosocial', 'Nome não informado')
        servicos = client_data.get('servicos', [])

        if not servicos:
            return f"❌ Cliente {nome} encontrado, mas sem serviços ativos."

        servico = servicos[0]
        nome_plano = servico.get('nome', 'Plano não informado')
        status = servico.get('status', 'Status não informado')

        return f"🎮 Cliente: {nome}\n📋 Plano: {nome_plano}\n⚡ Status: {status}"

    except Exception as e:
        logger.error(f"Erro ao formatar resumo do cliente: {e}")
        return "❌ Erro ao processar dados do cliente."