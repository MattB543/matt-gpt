# DigitalOcean Deployment Guide

This guide walks you through deploying Matt-GPT on DigitalOcean and testing the system.

## Prerequisites

- DigitalOcean account
- Domain name (optional but recommended)
- OpenRouter API key
- OpenAI API key

## Step 1: Create DigitalOcean Droplet

1. **Create a new Droplet:**
   - Choose Ubuntu 22.04 LTS
   - Minimum: 2 GB RAM, 1 vCPU (Basic plan $18/month)
   - Recommended: 4 GB RAM, 2 vCPU ($24/month)
   - Add SSH key for secure access

2. **Access your droplet:**
   ```bash
   ssh root@your-droplet-ip
   ```

## Step 2: Install Dependencies

```bash
# Update system
apt update && apt upgrade -y

# Install Python 3.11
apt install software-properties-common -y
add-apt-repository ppa:deadsnakes/ppa -y
apt update
apt install python3.11 python3.11-venv python3.11-dev -y

# Install PostgreSQL 15 with pgvector
apt install wget ca-certificates
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add -
echo "deb http://apt.postgresql.org/pub/repos/apt/ jammy-pgdg main" > /etc/apt/sources.list.d/pgdg.list
apt update
apt install postgresql-15 postgresql-client-15 postgresql-contrib-15 -y

# Install pgvector extension
apt install postgresql-15-pgvector -y

# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -
export PATH="/root/.local/bin:$PATH"
echo 'export PATH="/root/.local/bin:$PATH"' >> ~/.bashrc

# Install Git and other tools
apt install git nginx certbot python3-certbot-nginx -y
```

## Step 3: Setup PostgreSQL

```bash
# Start PostgreSQL
systemctl start postgresql
systemctl enable postgresql

# Create database and user
sudo -u postgres psql << EOF
CREATE DATABASE mattgpt;
CREATE USER mattgpt WITH PASSWORD 'your-secure-password';
GRANT ALL PRIVILEGES ON DATABASE mattgpt TO mattgpt;
ALTER USER mattgpt CREATEDB;
\q
EOF

# Enable pgvector extension
sudo -u postgres psql -d mattgpt << EOF
CREATE EXTENSION vector;
\q
EOF
```

## Step 4: Deploy Application

```bash
# Clone repository
cd /opt
git clone https://github.com/yourusername/matt-gpt.git
cd matt-gpt

# Install dependencies
poetry install

# Create environment file
cat > .env << EOF
DATABASE_URL=postgresql://mattgpt:your-secure-password@localhost:5432/mattgpt
OPENROUTER_API_KEY=sk-or-v1-your-openrouter-key
OPENAI_API_KEY=sk-your-openai-key
MATT_GPT_BEARER_TOKEN=your-secure-bearer-token
EOF

# Initialize database
poetry run python init_db.py
```

## Step 5: Setup Systemd Service

```bash
# Create service file
cat > /etc/systemd/system/mattgpt.service << EOF
[Unit]
Description=Matt-GPT API Server
After=network.target postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/matt-gpt
Environment=PATH=/root/.local/bin
ExecStart=/root/.local/bin/poetry run uvicorn main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
systemctl daemon-reload
systemctl enable mattgpt
systemctl start mattgpt
systemctl status mattgpt
```

## Step 6: Setup Nginx Reverse Proxy

```bash
# Create Nginx configuration
cat > /etc/nginx/sites-available/mattgpt << EOF
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Enable site
ln -s /etc/nginx/sites-available/mattgpt /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

## Step 7: Setup SSL Certificate (Optional)

```bash
# Get SSL certificate
certbot --nginx -d your-domain.com
```

## Testing the Deployment

### 1. Health Check
```bash
curl http://your-domain.com/health
# Expected: {"status":"healthy","timestamp":"..."}
```

### 2. Basic Chat Test
```bash
curl -X POST http://your-domain.com/chat \
  -H "Authorization: Bearer your-secure-bearer-token" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello Matt! How are you doing?",
    "openrouter_api_key": "sk-or-v1-your-openrouter-key"
  }'
```

### 3. Expected Response Format
```json
{
  "response": "Hey! I'm doing great, thanks for asking...",
  "query_id": "uuid-string",
  "latency_ms": 1234.56,
  "context_items_used": 5
}
```

### 4. Test RAG Functionality
```bash
# Test personality retrieval
curl -X POST http://your-domain.com/chat \
  -H "Authorization: Bearer your-secure-bearer-token" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are your thoughts on AI development?",
    "openrouter_api_key": "sk-or-v1-your-openrouter-key"
  }'

# Test message context retrieval
curl -X POST http://your-domain.com/chat \
  -H "Authorization: Bearer your-secure-bearer-token" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Tell me about a recent project you worked on",
    "openrouter_api_key": "sk-or-v1-your-openrouter-key"
  }'
```

## Verification Steps

### 1. Check System Status
```bash
# Service status
systemctl status mattgpt postgresql nginx

# Check logs
journalctl -u mattgpt -f

# Database connectivity
sudo -u postgres psql -d mattgpt -c "SELECT COUNT(*) FROM messages;"
```

### 2. Test Authentication
```bash
# Should fail without token
curl -X POST http://your-domain.com/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "test"}'

# Should return 401 Unauthorized
```

### 3. Test Vector Search
```bash
# Check if embeddings exist
sudo -u postgres psql -d mattgpt -c "SELECT COUNT(*) FROM messages WHERE embedding IS NOT NULL;"
```

## Troubleshooting

### Common Issues

1. **Service won't start:**
   ```bash
   journalctl -u mattgpt --no-pager
   ```

2. **Database connection issues:**
   ```bash
   sudo -u postgres psql -d mattgpt -c "\dt"
   ```

3. **Memory issues:**
   ```bash
   free -h
   htop
   ```

4. **API key issues:**
   - Check .env file permissions and content
   - Verify OpenRouter API key format starts with `sk-or-v1-`
   - Test OpenAI API key with curl

### Performance Monitoring

```bash
# Monitor resource usage
htop

# Check API response times
tail -f /var/log/nginx/access.log

# Monitor database performance
sudo -u postgres psql -d mattgpt -c "SELECT * FROM pg_stat_activity;"
```

## Load Data (Optional)

If you have data to import:

```bash
# Add sample data
poetry run python add_sample_data.py

# Import your own data (customize scripts as needed)
poetry run python import_slack_data.py
poetry run python import_text_data.py
```

## Security Considerations

1. **Firewall setup:**
   ```bash
   ufw allow ssh
   ufw allow 80
   ufw allow 443
   ufw enable
   ```

2. **Regular updates:**
   ```bash
   apt update && apt upgrade -y
   ```

3. **Backup database:**
   ```bash
   sudo -u postgres pg_dump mattgpt > backup.sql
   ```

## Scaling Considerations

- **Horizontal scaling:** Use load balancer with multiple droplets
- **Database scaling:** Consider managed PostgreSQL database
- **Caching:** Add Redis for response caching
- **CDN:** Use DigitalOcean Spaces + CDN for static assets