# Scripts de Operação e Manutenção

Este diretório contém scripts para automação, manutenção, deploy e diagnóstico do bot Sentinela.

## Estrutura

A estrutura foi organizada para separar os scripts por sua finalidade:

-   `db/`: Contém scripts para interagir diretamente com o banco de dados, como `backup_database.sh` e `restore_database.sh`.

-   `deploy/`: Agrupa scripts relacionados ao processo de deploy e provisionamento, como `deploy_safe.sh` (deploy seguro), `docker-build.sh` (build da imagem) e `server_setup.sh` (configuração inicial do servidor).

-   `diagnostics/`: Scripts para verificar a saúde e o estado da aplicação em execução.
    -   `health_check.py`: Verifica se a aplicação consegue se conectar ao banco de dados. Usado pelo script de deploy.
    -   `test_cron.sh`: Simula a execução de um cron job para validar a configuração do ambiente.

-   `setup/`: Scripts para configurar partes do ambiente operacional.
    -   `setup_monitoring.sh`: Configura os cron jobs para as tarefas de monitoramento.

-   `tasks/`: Contém as tarefas de negócio que são executadas de forma agendada (via cron).
    -   `daily_cpf_checkup.py`: A principal tarefa diária, que executa múltiplas fases de verificação (CPFs, regras, contratos).
    -   `export_critical_data.py`: Exporta dados críticos para um backup em JSON.
    -   `verify_data_integrity.py`: Verifica a integridade dos dados no banco para detectar anomalias.
