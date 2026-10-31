#!/bin/sh
# Alertmanager de Terrnova: arma su configuración con el destino del entorno y arranca.
# Con ALERTAS_TELEGRAM_TOKEN y ALERTAS_TELEGRAM_CHAT, cada alerta llega por Telegram al dueño
# (sin ellos, las alertas solo se ven en la interfaz de Alertmanager, y se dice al arrancar).
# Con un primer argumento «revisar», solo escribe la configuración en /tmp y la valida (CI).
set -eu

CONFIG=/tmp/alertmanager.yml

if [ -n "${ALERTAS_TELEGRAM_TOKEN:-}" ] && [ -n "${ALERTAS_TELEGRAM_CHAT:-}" ]; then
  RECEPTOR=$(cat <<FIN
  - name: duenio
    telegram_configs:
      - bot_token: '${ALERTAS_TELEGRAM_TOKEN}'
        chat_id: ${ALERTAS_TELEGRAM_CHAT}
        parse_mode: ''
        send_resolved: true
        message: '{{ if eq .Status "firing" }}ALERTA{{ else }}RESUELTA{{ end }} · {{ range .Alerts }}{{ .Labels.alertname }} ({{ .Labels.severidad }}): {{ .Annotations.resumen }}{{ "\n" }}{{ end }}'
FIN
)
else
  echo "aviso: sin ALERTAS_TELEGRAM_TOKEN y ALERTAS_TELEGRAM_CHAT, las alertas no llegan a nadie" >&2
  RECEPTOR="  - name: duenio"
fi

cat > "$CONFIG" <<FIN
# generado por arrancar.sh; no se edita a mano
route:
  receiver: duenio
  group_by: [alertname]
  group_wait: 30s
  group_interval: 5m
  # una alerta que sigue activa se repite cada 4 h: suficiente para una persona sin guardia
  repeat_interval: 4h
receivers:
${RECEPTOR}
FIN

if [ "${1:-}" = "revisar" ]; then
  exec amtool check-config "$CONFIG"
fi
exec /bin/alertmanager --config.file="$CONFIG" --storage.path=/alertmanager
