import logging
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from urllib.parse import urljoin
import aiohttp

from .config import (
    HUBSOFT_HOST,
    HUBSOFT_ENDPOINT_ATENDIMENTO,
    HUBSOFT_ENDPOINT_ATENDIMENTO_MENSAGEM,
    HUBSOFT_ENDPOINT_ATENDIMENTO_ANEXO,
    HUBSOFT_ENDPOINT_CLIENTE_ATENDIMENTO,
    HUBSOFT_TIPO_ATENDIMENTO_GAMING,
    HUBSOFT_STATUS_ATENDIMENTO_ABERTO,
    get_status_display
)
from .token_manager import get_hubsoft_token
from .cliente import get_client_info

logger = logging.getLogger(__name__)

class HubSoftAtendimentoClient:
    """Cliente para gerenciar atendimentos na API HubSoft"""

    def __init__(self):
        self.base_url = HUBSOFT_HOST

    async def _make_async_request(self, method: str, endpoint: str, data: Dict = None,
                                files: Dict = None) -> Dict[str, Any]:
        """Faz requisição assíncrona autenticada para API"""
        try:
            # Usa função síncrona existente para obter token
            token = get_hubsoft_token()
            if not token:
                raise Exception("Não foi possível obter token de acesso")

            url = urljoin(self.base_url, endpoint.lstrip('/'))
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json"
            }

            # Para uploads, não definir Content-Type
            if not files:
                headers["Content-Type"] = "application/json"

            async with aiohttp.ClientSession() as session:
                request_kwargs = {"headers": headers}

                if files:
                    # Upload com arquivos
                    form_data = aiohttp.FormData()

                    if data:
                        for key, value in data.items():
                            if isinstance(value, (dict, list)):
                                form_data.add_field(key, json.dumps(value))
                            else:
                                form_data.add_field(key, str(value))

                    for field_name, file_data in files.items():
                        form_data.add_field(
                            field_name,
                            file_data['content'],
                            filename=file_data['filename'],
                            content_type=file_data.get('content_type', 'application/octet-stream')
                        )

                    request_kwargs['data'] = form_data

                elif data:
                    request_kwargs['data'] = json.dumps(data)

                timeout = aiohttp.ClientTimeout(total=15)
                async with getattr(session, method.lower())(url, timeout=timeout, **request_kwargs) as response:
                    response_text = await response.text()

                    if response.status not in [200, 201]:
                        # Log sem expor dados sensíveis da resposta
                        logger.error(f"Erro na requisição {method} {endpoint}: HTTP {response.status}")
                        logger.debug(f"Resposta completa (debug): {response_text}")  # Só em debug
                        raise Exception(f"Erro HubSoft API: HTTP {response.status}")

                    try:
                        return await response.json() if response_text else {}
                    except json.JSONDecodeError:
                        return {"raw_response": response_text}

        except Exception as e:
            logger.error(f"Erro na requisição {method} {endpoint}: {e}")
            raise

    async def create_atendimento(self, client_cpf: str, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cria um novo atendimento no HubSoft

        Args:
            client_cpf: CPF do cliente
            ticket_data: Dados do ticket do formulário

        Returns:
            Dados do atendimento criado com ID oficial
        """
        try:
            # Busca dados do cliente
            client_data = get_client_info(client_cpf, full_data=True)
            if not client_data:
                raise Exception("Cliente não encontrado ou sem serviço ativo")

            # Extrai dados necessários
            id_cliente_servico = client_data.get('id_cliente_servico')
            if not id_cliente_servico:
                # Tenta extrair dos serviços
                servicos = client_data.get('servicos', [])
                if servicos:
                    id_cliente_servico = servicos[0].get('id')

                if not id_cliente_servico:
                    raise Exception("ID do serviço do cliente não encontrado")

            client_name = client_data.get('nome', client_data.get('client_name', 'Cliente'))
            client_phone = client_data.get('telefone', client_data.get('celular', '11999999999'))

            # Monta descrição formatada
            description = self._format_ticket_description(ticket_data, client_data)

            # Dados para criação
            atendimento_data = {
                "id_cliente_servico": int(id_cliente_servico),
                "id_tipo_atendimento": int(HUBSOFT_TIPO_ATENDIMENTO_GAMING),
                "id_atendimento_status": int(HUBSOFT_STATUS_ATENDIMENTO_ABERTO),
                "descricao": description,
                "nome": client_name,
                "telefone": str(client_phone).replace('+', '').replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
            }

            logger.info(f"Criando atendimento HubSoft para cliente {client_name}")
            logger.debug(f"Dados do atendimento: {atendimento_data}")

            response = await self._make_async_request("POST", HUBSOFT_ENDPOINT_ATENDIMENTO, atendimento_data)

            # Estrutura correta baseada na documentação real
            if response.get('status') == 'success' and response.get('atendimento'):
                atendimento_data = response['atendimento']
                atendimento_id = atendimento_data.get('id_atendimento')
                protocolo_oficial = atendimento_data.get('protocolo')

                logger.info(f"Atendimento HubSoft criado: ID {atendimento_id}, Protocolo: {protocolo_oficial}")

                # Retorna dados estruturados para o bot
                return {
                    'id_atendimento': atendimento_id,
                    'protocolo': protocolo_oficial,
                    'status': atendimento_data.get('status', 'Aguardando Análise'),
                    'data_cadastro': atendimento_data.get('data_cadastro'),
                    'cliente': atendimento_data.get('cliente', {}),
                    'ordens_servico': atendimento_data.get('ordens_servico', [])
                }
            else:
                logger.error(f"Resposta inesperada da API: {response}")
                raise Exception(f"Falha ao criar atendimento: {response}")

        except Exception as e:
            logger.error(f"Erro ao criar atendimento no HubSoft: {e}")
            raise

    async def get_client_atendimentos(self, client_cpf: str, apenas_pendente: bool = True, tipo_atendimento: str = None) -> List[Dict[str, Any]]:
        """
        Consulta atendimentos do cliente

        Args:
            client_cpf: CPF do cliente
            apenas_pendente: Se True, traz apenas atendimentos abertos
            tipo_atendimento: ID do tipo de atendimento para filtrar (ex: "101" para Gaming)

        Returns:
            Lista de atendimentos do cliente
        """
        try:
            formatted_cpf = "".join(filter(str.isdigit, client_cpf))

            # Constrói URL com parâmetros
            endpoint = HUBSOFT_ENDPOINT_CLIENTE_ATENDIMENTO
            params = [
                f"busca=cpf_cnpj",
                f"termo_busca={formatted_cpf}",
                f"apenas_pendente={'sim' if apenas_pendente else 'nao'}",
                f"limit=20"
            ]

            # Adiciona filtro de tipo se especificado
            if tipo_atendimento:
                params.append(f"tipo_atendimento={tipo_atendimento}")

            endpoint_with_params = f"{endpoint}?{'&'.join(params)}"

            logger.info(f"Consultando atendimentos do cliente CPF {formatted_cpf[:3]}***")
            response = await self._make_async_request("GET", endpoint_with_params)

            # Estrutura correta baseada na documentação real
            if response.get('status') == 'suscess' and response.get('atendimentos'):  # Note: API retorna "suscess" com 's' duplo
                atendimentos = response['atendimentos']
                logger.info(f"Encontrados {len(atendimentos)} atendimentos para o cliente")

                # Enriquece dados para exibição usando campos corretos
                for atendimento in atendimentos:
                    # Campo 'status' já vem como string na resposta
                    status_name = atendimento.get('status', 'Status Desconhecido')

                    # Adiciona informações de display enriquecidas
                    atendimento['status_display'] = {
                        'name': status_name,
                        'emoji': self._get_status_emoji(status_name),
                        'message': f"Atendimento {status_name.lower()}"
                    }

                    # Formatar protocolo para exibição amigável
                    protocolo = atendimento.get('protocolo')
                    if protocolo:
                        atendimento['protocolo_display'] = f"#{protocolo}"

                return atendimentos

            return []

        except Exception as e:
            logger.error(f"Erro ao consultar atendimentos do cliente {client_cpf[:3]}***: {e}")
            return []

    async def add_message_to_atendimento(self, atendimento_id: str, message: str) -> bool:
        """
        Adiciona mensagem ao atendimento

        Args:
            atendimento_id: ID do atendimento
            message: Mensagem a ser adicionada

        Returns:
            True se sucesso, False caso contrário
        """
        try:
            endpoint = f"{HUBSOFT_ENDPOINT_ATENDIMENTO_MENSAGEM}/{atendimento_id}"
            data = {"mensagem": message}

            response = await self._make_async_request("POST", endpoint, data)
            success = response.get('success', False)

            if success:
                logger.info(f"Mensagem adicionada ao atendimento {atendimento_id}")
            else:
                logger.warning(f"Falha ao adicionar mensagem ao atendimento {atendimento_id}: {response}")

            return success

        except Exception as e:
            logger.error(f"Erro ao adicionar mensagem ao atendimento {atendimento_id}: {e}")
            return False

    async def add_attachment_to_atendimento(self, atendimento_id: str,
                                          file_content: bytes, filename: str) -> bool:
        """
        Adiciona anexo ao atendimento

        Args:
            atendimento_id: ID do atendimento
            file_content: Conteúdo do arquivo em bytes
            filename: Nome do arquivo

        Returns:
            True se sucesso, False caso contrário
        """
        try:
            endpoint = f"{HUBSOFT_ENDPOINT_ATENDIMENTO_ANEXO}/{atendimento_id}"

            files = {
                "files[0]": {
                    "content": file_content,
                    "filename": filename,
                    "content_type": "application/octet-stream"
                }
            }

            response = await self._make_async_request("POST", endpoint, files=files)
            success = response.get('success', False)

            if success:
                logger.info(f"Anexo {filename} adicionado ao atendimento {atendimento_id}")
            else:
                logger.warning(f"Falha ao adicionar anexo ao atendimento {atendimento_id}: {response}")

            return success

        except Exception as e:
            logger.error(f"Erro ao adicionar anexo ao atendimento {atendimento_id}: {e}")
            return False

    def _format_ticket_description(self, ticket_data: Dict[str, Any], client_data: Dict[str, Any]) -> str:
        """
        Formata descrição completa do ticket para o HubSoft

        Args:
            ticket_data: Dados do ticket do formulário
            client_data: Dados do cliente do HubSoft

        Returns:
            Descrição formatada para o atendimento
        """
        try:
            current_time = datetime.now().strftime("%d/%m/%Y às %H:%M")

            # Mapear categorias e jogos para nomes amigáveis
            category_names = {
                "connectivity": "Conectividade/Ping Alto",
                "performance": "Performance em Jogos",
                "configuration": "Configuração/Otimização",
                "equipment": "Problema com Equipamento",
                "other": "Outro"
            }

            game_names = {
                "valorant": "Valorant",
                "cs2": "Counter-Strike 2",
                "lol": "League of Legends",
                "fortnite": "Fortnite",
                "apex": "Apex Legends",
                "overwatch": "Overwatch 2",
                "mobile_legends": "Mobile Legends",
                "dota2": "Dota 2",
                "all_games": "Múltiplos Jogos",
                "other_game": "Outro Jogo"
            }

            timing_names = {
                "now": "Agora mesmo",
                "yesterday": "Ontem",
                "this_week": "Esta semana",
                "last_week": "Semana passada",
                "long_time": "Há mais tempo",
                "always": "Sempre foi assim"
            }

            category = category_names.get(ticket_data.get('category'), ticket_data.get('category', 'Não especificado'))
            game = game_names.get(ticket_data.get('affected_game'), ticket_data.get('affected_game', 'Não especificado'))
            timing = timing_names.get(ticket_data.get('problem_started'), ticket_data.get('problem_started', 'Não especificado'))

            # Calcular prioridade
            priority = self._calculate_priority(ticket_data.get('category'), ticket_data.get('affected_game'))

            # Foca na descrição do cliente como informação principal
            client_description = ticket_data.get('description', 'Descrição não fornecida')

            description = f"""📝 PROBLEMA RELATADO PELO CLIENTE:
"{client_description}"

🎮 INFORMAÇÕES DO ATENDIMENTO:
• Categoria: {category} | Jogo: {game}
• Quando começou: {timing} | Prioridade: {priority}
• Cliente: {client_data.get('nome', client_data.get('client_name', 'N/A'))}

🤖 ORIGEM: Bot Telegram OnCabo ({current_time})"""

            return description

        except Exception as e:
            logger.error(f"Erro ao formatar descrição do ticket: {e}")
            return f"Erro ao formatar descrição: {str(e)}"

    def _calculate_priority(self, category: str, game: str) -> str:
        """Calcula prioridade baseada na categoria e jogo"""
        competitive_games = ["valorant", "cs2", "lol", "overwatch", "dota2"]

        if category == "connectivity":
            if game in competitive_games:
                return "⚡ ALTA (Jogo Competitivo + Conectividade)"
            return "🔶 MÉDIA (Conectividade)"

        if category == "performance" and game in competitive_games:
            return "🔶 MÉDIA (Performance Gaming)"

        if category == "equipment":
            return "🔶 MÉDIA (Equipamento)"

        return "🔵 NORMAL"

    def _mask_cpf(self, cpf: str) -> str:
        """Mascara CPF para segurança"""
        if not cpf or len(cpf) < 11:
            return "***.***.***-**"

        clean_cpf = ''.join(filter(str.isdigit, cpf))
        if len(clean_cpf) == 11:
            return f"{clean_cpf[:3]}.{clean_cpf[3:6]}.***-{clean_cpf[9:]}"

        return "***.***.***-**"

    def _get_status_emoji(self, status_name: str) -> str:
        """Retorna emoji apropriado para o status"""
        status_emojis = {
            'Pendente': '🟣',
            'Aguardando Análise': '🟠',
            'Em Andamento': '🔄',
            'Resolvido': '✅',
            'Fechado': '🔒',
            'Cancelado': '❌'
        }
        return status_emojis.get(status_name, '❓')

    async def get_atendimentos_paginado(self, pagina: int = 0, itens_por_pagina: int = 20,
                                      data_inicio: str = None, data_fim: str = None,
                                      tipo_atendimento: str = None, status_atendimento: str = None,
                                      relacoes: str = None) -> Dict[str, Any]:
        """
        Consulta atendimentos com paginação e filtros avançados
        Usa o endpoint /api/v1/integracao/atendimento/todos para maior eficiência

        Args:
            pagina: Página atual (começando em 0)
            itens_por_pagina: Quantidade de itens por página
            data_inicio: Data início no formato YYYY-MM-DD
            data_fim: Data fim no formato YYYY-MM-DD
            tipo_atendimento: IDs dos tipos separados por vírgula
            status_atendimento: IDs dos status separados por vírgula
            relacoes: Relações a incluir (ex: "atendimento_mensagem,cliente_servico")

        Returns:
            Dados paginados com atendimentos e metadados de paginação
        """
        try:
            # Usar endpoint mais eficiente para consultas gerais
            endpoint = "/api/v1/integracao/atendimento/todos"

            params = [
                f"pagina={pagina}",
                f"itens_por_pagina={itens_por_pagina}"
            ]

            # Adicionar filtros opcionais
            if data_inicio:
                params.append(f"data_inicio={data_inicio}")
            if data_fim:
                params.append(f"data_fim={data_fim}")
            if relacoes:
                params.append(f"relacoes={relacoes}")

            endpoint_with_params = f"{endpoint}?{'&'.join(params)}"

            logger.info(f"Consultando atendimentos paginados - Página {pagina}, {itens_por_pagina} itens")
            response = await self._make_async_request("GET", endpoint_with_params)

            # Processa resposta conforme documentação
            if response.get('status') == 'success' and response.get('atendimentos'):
                result = {
                    'atendimentos': response['atendimentos'],
                    'paginacao': response.get('paginacao', {}),
                    'status': 'success',
                    'msg': response.get('msg', 'Dados consultados com sucesso')
                }

                # Enriquece dados dos atendimentos
                for atendimento in result['atendimentos']:
                    self._enrich_atendimento_data(atendimento)

                logger.info(f"Consulta paginada concluída: {len(result['atendimentos'])} atendimentos retornados")
                return result

            return {
                'atendimentos': [],
                'paginacao': {'total_registros': 0},
                'status': 'success',
                'msg': 'Nenhum atendimento encontrado'
            }

        except Exception as e:
            logger.error(f"Erro na consulta paginada de atendimentos: {e}")
            return {
                'atendimentos': [],
                'paginacao': {'total_registros': 0},
                'status': 'error',
                'msg': str(e)
            }

    def _enrich_atendimento_data(self, atendimento: Dict[str, Any]) -> None:
        """Enriquece dados do atendimento para melhor exibição"""
        try:
            # Status com emoji
            if 'status' in atendimento and isinstance(atendimento['status'], dict):
                status_display = atendimento['status'].get('display', 'Status Desconhecido')
                atendimento['status_emoji'] = self._get_status_emoji(status_display)
                atendimento['status_name'] = status_display

            # Protocolo formatado
            protocolo = atendimento.get('protocolo')
            if protocolo:
                atendimento['protocolo_display'] = f"#{protocolo}"

            # Tempo em aberto formatado
            minutos_aberto = atendimento.get('minutos_em_aberto', 0)
            if minutos_aberto:
                atendimento['tempo_aberto_formatado'] = self._format_tempo_aberto(minutos_aberto)

            # Dados do cliente formatados
            if 'cliente_servico' in atendimento and 'cliente' in atendimento['cliente_servico']:
                cliente = atendimento['cliente_servico']['cliente']
                atendimento['cliente_display'] = cliente.get('display', cliente.get('nome_razaosocial', 'Cliente'))

        except Exception as e:
            logger.warning(f"Erro ao enriquecer dados do atendimento: {e}")

    def _format_tempo_aberto(self, minutos: int) -> str:
        """Formata tempo em aberto de forma amigável"""
        if minutos < 60:
            return f"{minutos}min"
        elif minutos < 1440:  # menos que 24h
            horas = minutos // 60
            mins = minutos % 60
            return f"{horas}h {mins}min" if mins > 0 else f"{horas}h"
        else:
            dias = minutos // 1440
            horas = (minutos % 1440) // 60
            return f"{dias}d {horas}h" if horas > 0 else f"{dias}d"

# Instância global do cliente
hubsoft_atendimento_client = HubSoftAtendimentoClient()