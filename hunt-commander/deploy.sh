#!/bin/bash

# Hunt Commander Deployment Script for curak.xyz/hunt

set -e

echo "🎯 Hunt Commander Deployment Script"
echo "======================================"

# Variables
DOMAIN="curak.xyz"
SUBDOMAIN="hunt"
FULL_DOMAIN="${SUBDOMAIN}.${DOMAIN}"
APP_DIR="/var/www/hunt-commander"
NGINX_CONFIG="/etc/nginx/sites-available/hunt-commander"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
   echo "Please run as root (use sudo)"
   exit 1
fi

echo "Step 1: Installing dependencies..."
apt-get update
apt-get install -y python3.11 python3-pip python3-venv nginx postgresql postgresql-contrib certbot python3-certbot-nginx git docker docker-compose

echo "Step 2: Setting up application directory..."
mkdir -p $APP_DIR
cp -r . $APP_DIR/
cd $APP_DIR

echo "Step 3: Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

echo "Step 4: Setting up PostgreSQL database..."
sudo -u postgres psql -c "CREATE DATABASE huntcommander;" || true
sudo -u postgres psql -c "CREATE USER huntcommander WITH PASSWORD 'change_this_password';" || true
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE huntcommander TO huntcommander;" || true

echo "Step 5: Running database migrations..."
python -c "from api.database import init_db; init_db()"

echo "Step 6: Configuring Nginx..."
cat > $NGINX_CONFIG << 'EOF'
server {
    listen 80;
    server_name hunt.curak.xyz;

    # Frontend
    location / {
        root /var/www/hunt-commander/frontend;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # API
    location /api {
        rewrite ^/api(.*) $1 break;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket support
    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF

ln -sf $NGINX_CONFIG /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx

echo "Step 7: Setting up SSL with Let's Encrypt..."
certbot --nginx -d $FULL_DOMAIN --non-interactive --agree-tos --email admin@$DOMAIN || echo "SSL setup skipped (may already exist)"

echo "Step 8: Creating systemd service..."
cat > /etc/systemd/system/hunt-commander.service << EOF
[Unit]
Description=Hunt Commander API
After=network.target postgresql.service

[Service]
Type=simple
User=www-data
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin"
ExecStart=$APP_DIR/venv/bin/uvicorn api.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable hunt-commander
systemctl start hunt-commander

echo "Step 9: Creating scheduler service..."
cat > /etc/systemd/system/hunt-commander-scheduler.service << EOF
[Unit]
Description=Hunt Commander Scheduler
After=network.target postgresql.service

[Service]
Type=simple
User=www-data
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin"
ExecStart=$APP_DIR/venv/bin/python schedule_daily.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable hunt-commander-scheduler
systemctl start hunt-commander-scheduler

echo ""
echo "✅ Hunt Commander deployed successfully!"
echo ""
echo "Access your application at: https://$FULL_DOMAIN"
echo ""
echo "Important next steps:"
echo "1. Update $APP_DIR/.env with your API keys and credentials"
echo "2. Configure Stripe keys for payments"
echo "3. Set up monitoring and backups"
echo "4. Review nginx logs: /var/log/nginx/error.log"
echo "5. Check application logs: journalctl -u hunt-commander -f"
echo ""
echo "Service commands:"
echo "  sudo systemctl status hunt-commander"
echo "  sudo systemctl restart hunt-commander"
echo "  sudo systemctl status hunt-commander-scheduler"
echo ""
echo "🎯 Ready to land that €4k/month Python gig! 🎯"
