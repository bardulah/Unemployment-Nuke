# 🎯 Hunt Commander

**Land your €4k/month Python gig in Bratislava with AI-powered job hunting**

Hunt Commander evolves the Multi-Agent Job Matching System into a complete tactical platform with salary negotiation, LinkedIn automation, and comprehensive tracking.

## 🚀 New Features

- 💰 **Negotiation Agent**: Counter-offers using Glassdoor Slovak data
- 🔗 **LinkedIn Infiltrator**: Auto-DM recruiters at scale
- 📊 **Dashboard**: Track apps, prep interviews, analyze rejections
- 💳 **€19/month**: Unlimited access + coaching

## 📦 Quick Start

```bash
# Docker deployment
docker-compose up -d

# Manual setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -c "from api.database import init_db; init_db()"
uvicorn api.main:app --reload
```

Access: http://localhost:3000

## 🌐 Deploy to curak.xyz/hunt

```bash
chmod +x deploy.sh
sudo ./deploy.sh
```

## 📚 Full Documentation

See original README in Multi-Agent-Job-Matching-System for detailed docs.

**Ready to hunt? https://curak.xyz/hunt 🎯**
