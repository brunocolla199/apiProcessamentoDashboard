# Configurações nos serviços do Linux que usei para rodar a aplicação em background
[Unit]
Description=Dashboards customizados WeeHealth
[Install]
WantedBy=multi-user.target
[Service]
User=root
PermissionsStartOnly=true
ExecStart=/opt/dashboards-customizados-weecode/venv/bin/python3.6 /opt/dashboards-customizados-weecode/app.py
TimeoutSec=600
Restart=on-failure
RuntimeDirectoryMode=755
Environment=PYTHONUNBUFFERED=1