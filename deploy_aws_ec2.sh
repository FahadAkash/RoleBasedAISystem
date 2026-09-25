#!/bin/bash
# AWS EC2 Free Tier Deployment Script (Ubuntu 22.04 / 24.04)
# Run this on your EC2 instance!

echo "🚀 Starting Deployment Setup for Role-Based AI System..."

# 1. Update system & install dependencies
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv git

# 2. Create Virtual Environment
python3 -m venv venv
source venv/bin/activate

# 3. Install Python requirements
pip install -r requirements.txt

# 4. Create Systemd Service for FastAPI (Backend)
cat <<EOF | sudo tee /etc/systemd/system/fastapi.service
[Unit]
Description=FastAPI Backend
After=network.target

[Service]
User=ubuntu
WorkingDirectory=$(pwd)
ExecStart=$(pwd)/venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# 5. Create Systemd Service for Streamlit (Frontend)
cat <<EOF | sudo tee /etc/systemd/system/streamlit.service
[Unit]
Description=Streamlit Frontend
After=network.target

[Service]
User=ubuntu
WorkingDirectory=$(pwd)
ExecStart=$(pwd)/venv/bin/streamlit run frontend/app.py --server.port 8501
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# 6. Enable and start services
sudo systemctl daemon-reload
sudo systemctl enable fastapi
sudo systemctl enable streamlit
sudo systemctl start fastapi
sudo systemctl start streamlit

echo "✅ Deployment Successful!"
echo "Your backend is running on port 8000"
echo "Your frontend is running on port 8501"
echo ""
echo "⚠️  IMPORTANT AWS STEPS:"
echo "1. Go to your EC2 console -> Security Groups"
echo "2. Edit Inbound Rules"
echo "3. Add Custom TCP rule for port 8000 (Anywhere IPv4)"
echo "4. Add Custom TCP rule for port 8501 (Anywhere IPv4)"
echo "5. In frontend/app.py, make sure BACKEND_URL points to 'http://YOUR_EC2_PUBLIC_IP:8000' if you aren't using localhost."
