# 🏙️ Autonomous City Intelligent System

An AI-powered smart city traffic management system featuring real-time traffic monitoring, reinforcement learning-based signal optimization, emergency vehicle routing, and automated violation detection.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Running the Application](#running-the-application)
- [API Documentation](#api-documentation)
- [Testing](#testing)
- [Contributing](#contributing)
- [License](#license)

---

## 🎯 Overview

The Autonomous City Intelligent System is a comprehensive traffic management platform designed to optimize urban mobility through:

- **Real-time Traffic Density Monitoring** - Track vehicle flow across intersections
- **AI-Powered Signal Optimization** - RL agents that learn optimal signal timing
- **Emergency Green Corridors** - Priority routing for emergency vehicles
- **Automated Violation Detection** - AI-based challan generation system
- **Congestion Prediction** - ML models for traffic forecasting
- **Digital Twin Visualization** - Real-time city traffic visualization

---

## ✨ Features

| Module | Description |
|--------|-------------|
| 🚦 **Traffic Density Modeling** | Real-time vehicle counting and flow analysis |
| 🤖 **Autonomous Agent Loop** | Perception → Decision → Action cycle |
| 🎮 **RL Signal Orchestration** | PPO-based traffic signal optimization |
| 🛡️ **Safety & Fail-Safe** | Monitoring and emergency protocols |
| 📊 **Congestion Prediction** | Time-series forecasting models |
| 🚑 **Emergency Green Corridor** | Priority routing for ambulances/fire trucks |
| 🎫 **Auto Challan System** | Automated traffic violation detection |
| 🌐 **Digital Twin UI** | Interactive traffic visualization dashboard |

---

## 🛠️ Tech Stack

### Backend
- **Framework:** FastAPI
- **Database:** SQLAlchemy + SQLite/PostgreSQL
- **ML/RL:** PyTorch, Stable-Baselines3, TensorBoard
- **WebSocket:** Socket.IO
- **Geospatial:** OSMnx, NetworkX

### Frontend
- **Framework:** React 18 + TypeScript
- **Styling:** Tailwind CSS
- **State Management:** Zustand
- **Charts:** Chart.js
- **Build Tool:** Vite

---

## 📁 Project Structure

```
AutonomusCityIntelligentSystem/
├── backend/
│   ├── app/
│   │   ├── agent/          # Autonomous agent (perception, decision, action)
│   │   ├── api/            # REST API routes
│   │   ├── challan/        # Auto-challan violation system
│   │   ├── database/       # Database models & connections
│   │   ├── density/        # Traffic density tracking
│   │   ├── emergency/      # Emergency vehicle routing
│   │   ├── models/         # Pydantic data models
│   │   ├── prediction/     # Congestion prediction ML
│   │   ├── rl/             # Reinforcement learning environment
│   │   ├── safety/         # Fail-safe monitoring
│   │   ├── services/       # Business logic services
│   │   ├── simulation/     # Traffic simulation
│   │   ├── websocket/      # Real-time WebSocket handlers
│   │   └── main.py         # FastAPI application entry
│   ├── config/             # Configuration files (JSON/YAML)
│   ├── data/               # Database & cache files
│   ├── models/             # Trained ML model files
│   ├── scripts/            # Utility scripts
│   ├── tests/              # Unit & integration tests
│   ├── requirements.txt    # Python dependencies
│   └── train_rl.py         # RL model training script
├── frontend/
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── pages/          # Page components
│   │   ├── services/       # API services
│   │   ├── store/          # Zustand state management
│   │   ├── types/          # TypeScript type definitions
│   │   └── App.tsx         # Main application component
│   ├── package.json        # Node.js dependencies
│   └── vite.config.ts      # Vite configuration
├── .gitignore              # Git ignore rules
└── README.md               # This file
```

---

## 🚀 Installation

### Prerequisites
- Python 3.10+
- Node.js 18+
- Git

### Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install
```

---

## ▶️ Running the Application

### Start Backend Server

```bash
cd backend
venv\Scripts\activate  # Windows
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Start Frontend Development Server

```bash
cd frontend
npm run dev
```

### Access the Application
- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:8000
- **API Docs (Swagger):** http://localhost:8000/docs
- **API Docs (ReDoc):** http://localhost:8000/redoc

---

## 📡 API Documentation

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/traffic/density` | GET | Get traffic density data |
| `/api/traffic/signals` | GET/POST | Manage traffic signals |
| `/api/emergency/route` | POST | Calculate emergency route |
| `/api/prediction/congestion` | GET | Get congestion predictions |
| `/api/challan/violations` | GET | List detected violations |
| `/api/agent/status` | GET | Get agent loop status |
| `/api/rl/action` | POST | Get RL recommended action |
| `/api/simulation/start` | POST | Start traffic simulation |

### WebSocket Events
- `traffic_update` - Real-time traffic data
- `signal_change` - Signal state changes
- `emergency_alert` - Emergency vehicle notifications
- `violation_detected` - New violation alerts

---

## 🧪 Testing

### Run Backend Tests

```bash
cd backend
pytest
```

### Run with Coverage

```bash
pytest --cov=app --cov-report=html
```

### Test Specific Module

```bash
pytest tests/test_rl_system.py -v
```

---

## 🤖 Training RL Model

```bash
cd backend

# Quick training (10,000 timesteps)
python train_rl.py --timesteps 10000

# Full training
python train_rl.py --timesteps 100000
```

---

## 🔧 Configuration

Configuration files are located in `backend/config/`:

- `system.yaml` - System-wide settings
- `traffic.json` - Traffic simulation parameters
- `agent.json` - Agent loop configuration
- `emergency.json` - Emergency routing settings
- `prediction.json` - ML prediction parameters
- `challan.json` - Violation detection rules

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License.

---

## 👥 Authors

- **Development Team** - Autonomous City Intelligent System

---

<p align="center">
  Made with ❤️ for smarter cities
</p>

