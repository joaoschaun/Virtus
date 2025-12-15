# VIRTUS Dashboard - Configuração de Produção
================================================

## Arquitetura

```
                    ┌─────────────────────────────────────────────────────┐
                    │                   CLOUDFLARE                        │
                    │  dashboard.virtusinvestimentos.com.br               │
                    │  - DNS                                              │
                    │  - SSL/TLS (Flexible)                               │
                    │  - CDN & Cache                                      │
                    │  - DDoS Protection                                  │
                    └─────────────────────────────────────────────────────┘
                                           │
                                           │ HTTP (:80)
                                           ▼
                    ┌─────────────────────────────────────────────────────┐
                    │                    SERVIDOR                         │
                    │                                                     │
                    │   ┌───────────────────────────────────────────┐    │
                    │   │              NGINX (:80)                  │    │
                    │   │  - Serve Frontend (React Build)          │    │
                    │   │  - Proxy /api → Backend (:8000)          │    │
                    │   │  - Proxy /ws → WebSocket                 │    │
                    │   └───────────────────────────────────────────┘    │
                    │                      │                              │
                    │          ┌───────────┴───────────┐                 │
                    │          ▼                       ▼                 │
                    │   ┌─────────────┐      ┌─────────────────────┐    │
                    │   │  Frontend   │      │  Backend (FastAPI)  │    │
                    │   │   /dist/    │      │    :8000            │    │
                    │   │  (estático) │      │  - API REST         │    │
                    │   └─────────────┘      │  - WebSocket        │    │
                    │                        │  - News/TTS         │    │
                    │                        └─────────────────────┘    │
                    └─────────────────────────────────────────────────────┘
```

## 1. Pré-requisitos

### No Servidor Windows:
- Python 3.11+ instalado
- Node.js 18+ instalado
- Nginx para Windows
- Acesso de Administrador

### Instalar Nginx para Windows:
1. Baixe de: https://nginx.org/en/download.html
2. Escolha a versão "nginx/Windows" (ex: nginx-1.24.0.zip)
3. Extraia para `C:\nginx\`
4. Verifique: deve existir `C:\nginx\nginx.exe`

---

## 2. Deploy Rápido

Execute **como Administrador** no PowerShell:

```powershell
cd C:\Users\Administrator\Desktop\Virtus\brain\dashboard
.\deploy.ps1 -Deploy full
```

Isso irá:
- ✅ Instalar dependências Python
- ✅ Criar serviço Windows para o Backend
- ✅ Fazer build do Frontend
- ✅ Configurar Nginx
- ✅ Iniciar todos os serviços

---

## 3. Configuração do Cloudflare

### 3.1. Acessar o Cloudflare
1. Entre em: https://dash.cloudflare.com
2. Selecione o domínio: `virtusinvestimentos.com.br`

### 3.2. Configurar DNS
Vá em **DNS** > **Records** > **Add record**

| Tipo | Nome | Conteúdo | Proxy | TTL |
|------|------|----------|-------|-----|
| A | dashboard | `SEU_IP_PÚBLICO` | ☁️ Proxied | Auto |

> **Para descobrir seu IP público**: acesse https://whatismyipaddress.com

### 3.3. Configurar SSL/TLS
Vá em **SSL/TLS** > **Overview**

- **Encryption mode**: `Flexible`

> ⚠️ **Flexible** significa: 
> - HTTPS entre visitante ↔ Cloudflare ✅
> - HTTP entre Cloudflare ↔ Seu servidor

### 3.4. Configurar Page Rules (Opcional)
Vá em **Rules** > **Page Rules** > **Create Page Rule**

**Regra 1 - Forçar HTTPS:**
- URL: `*dashboard.virtusinvestimentos.com.br/*`
- Setting: Always Use HTTPS

**Regra 2 - Cache de Assets:**
- URL: `*dashboard.virtusinvestimentos.com.br/*.js`
- Setting: Cache Level = Cache Everything

### 3.5. Configurar Firewall (Recomendado)
Vá em **Security** > **WAF**

- Habilite proteção contra ataques comuns
- Configure rate limiting para a API

---

## 4. Comandos Úteis

### Gerenciar Backend:
```powershell
# Status
.\backend\install_service.ps1 -Action status

# Reiniciar
.\backend\install_service.ps1 -Action restart

# Parar
.\backend\install_service.ps1 -Action stop

# Ver logs
Get-Content ..\data\logs\dashboard_service.log -Tail 50
```

### Gerenciar Nginx:
```powershell
# Recarregar configuração
cd C:\nginx
.\nginx.exe -s reload

# Testar configuração
.\nginx.exe -t

# Parar
.\nginx.exe -s stop

# Ver logs
Get-Content C:\nginx\logs\dashboard_error.log -Tail 50
```

### Rebuild Frontend:
```powershell
cd frontend
npm run build
```

### Status Geral:
```powershell
.\deploy.ps1 -Deploy status
```

---

## 5. Firewall do Windows

Libere as portas necessárias:

```powershell
# Porta 80 (HTTP)
New-NetFirewallRule -DisplayName "HTTP" -Direction Inbound -Protocol TCP -LocalPort 80 -Action Allow

# Porta 443 (HTTPS) - se usar SSL local
New-NetFirewallRule -DisplayName "HTTPS" -Direction Inbound -Protocol TCP -LocalPort 443 -Action Allow
```

---

## 6. Testando

### Local:
```
http://localhost/
http://localhost/api/health
http://localhost/api/news
```

### Externo (após Cloudflare):
```
https://dashboard.virtusinvestimentos.com.br/
https://dashboard.virtusinvestimentos.com.br/api/health
```

---

## 7. Troubleshooting

### Backend não inicia:
```powershell
# Verificar logs
Get-Content ..\data\logs\dashboard_stderr.log -Tail 100

# Testar manualmente
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### Nginx não inicia:
```powershell
# Testar configuração
cd C:\nginx
.\nginx.exe -t

# Ver erros
Get-Content logs\error.log -Tail 50
```

### 502 Bad Gateway:
- Backend pode estar parado
- Verifique se porta 8000 está ativa:
```powershell
Get-NetTCPConnection -LocalPort 8000
```

---

## 8. Segurança

### Mudar credenciais de login:
Edite `backend/main.py`, seção `USERS`:
```python
USERS: Dict[str, Dict] = {
    "admin": {
        "password_hash": hashlib.sha256("SUA_NOVA_SENHA".encode()).hexdigest(),
        ...
    }
}
```
