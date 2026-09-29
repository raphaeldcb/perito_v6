"""Jobs assíncronos executados IN-PROCESS via FastAPI BackgroundTasks.

Diferente da fila de polling em app/routes/jobs.py (que existe pra trabalho
que só o agente Windows/Mac pode fazer — Chrome + certificado A3 pro
protocolo eSAJ), os jobs aqui não dependem de nenhuma máquina específica: o
Qwen é alcançável direto via HTTP (settings.ollama_url, Ollama nativo no VPS
ou local no Mac em dev), então rodar em BackgroundTasks no próprio backend é
suficiente — sem a latência de esperar um agente fazer polling.

Cada módulo expõe uma função `executar_<algo>(job_id, ..., db)` que lê o
`Job` correspondente (criado pelo endpoint que disparou o trabalho), faz o
processamento e atualiza `job.status`/`job.resultado`/`job.erro` na mesma
sessão recebida — quem chama decide se essa sessão é a do request ou uma
nova (SessionLocal) aberta especificamente para o background task.
"""
