#!/bin/sh
# Entrypoint para o servico de cron

# Criar arquivo de log
touch /var/log/cron.log

# Copiar crontab
crontab /etc/cron.d/euromilhoes-cron

echo "Cron service iniciado. Agendamento:"
crontab -l

# Executar cron em foreground e mostrar logs
crond -f -l 2 &

# Seguir o arquivo de log
tail -f /var/log/cron.log
