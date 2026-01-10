# Autonomous City Traffic Intelligence System - Frontend

**Digital Twin UI & Visualization Dashboard**

Built for AutonomousHacks 2026 (24-Hour Hackathon)

## 🚀 Quick Start

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Open http://localhost:5173
```

## 📋 Features

### Digital Twin Visualization
- **Canvas-based City Map** - Real-time 2D visualization of traffic simulation
- **60 FPS Animation** - Smooth vehicle movement and signal transitions
- **Interactive Junctions** - Hover to see metrics, click to control
- **Density Overlays** - Color-coded traffic density visualization

### Control Panel
- **Simulation Controls** - Play/Pause/Reset functionality
- **Speed Control** - 1x, 2x, 5x, 10x simulation speed
- **RL Agent Control** - Start/Stop/Switch between RL and Rule-based strategies
- **Time Display** - Real-time simulation clock

### Statistics Dashboard
- **Live Metrics** - Vehicle count, density, throughput, violations
- **Performance Monitoring** - FPS, agent latency, congestion points
- **Real-time Updates** - WebSocket-powered live data

### Emergency & Safety
- **Emergency Indicators** - Visual alerts for active emergencies
- **System Mode Display** - NORMAL/EMERGENCY/INCIDENT/FAIL_SAFE
- **Health Monitoring** - Component health checks
- **Safety Features Status** - Active/Standby indicators

### Violations Panel
- **Violation Tracking** - Red light, speeding, wrong direction
- **Challan Management** - Issued challans with payment status
- **Filtering** - Filter by violation type

## 🏗️ Project Structure

```
frontend/
├── src/
│   ├── components/       # Reusable UI components
│   │   ├── CityMap.tsx          # Canvas-based city visualization
│   │   ├── ControlPanel.tsx     # Simulation controls
│   │   ├── StatisticsPanel.tsx  # Metrics dashboard
│   │   ├── EmergencySafetyPanel.tsx  # Safety indicators
│   │   ├── ViolationsPanel.tsx  # Violations & challans
│   │   ├── Navbar.tsx           # Top navigation
│   │   └── Sidebar.tsx          # Side navigation
│   ├── pages/            # Page components
│   │   ├── Dashboard.tsx        # Main dashboard
│   │   ├── Analytics.tsx        # Historical analytics
│   │   └── SafetyPage.tsx       # Safety controls
│   ├── services/         # API & WebSocket clients
│   │   ├── api.ts               # REST API client
│   │   ├── websocket.ts         # WebSocket service
│   │   └── websocketIntegration.ts  # Store integration
│   ├── store/            # State management (Zustand)
│   │   └── useSystemStore.ts    # Global state store
│   ├── types/            # TypeScript definitions
│   │   └── models.ts            # Data models
│   ├── hooks/            # Custom React hooks
│   │   └── useDemoMode.ts       # Demo mode animation
│   ├── data/             # Mock data for demos
│   │   └── mockData.ts          # Demo data generator
│   └── config/           # Configuration
│       └── env.ts               # Environment config
├── public/               # Static assets
└── package.json
```

## 🎨 Tech Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool & dev server
- **TailwindCSS** - Utility-first CSS
- **Zustand** - State management
- **Socket.IO Client** - Real-time WebSocket
- **Lucide React** - Icons
- **React Router** - Navigation

## 🔧 Configuration

### Environment Variables

Create a `.env` file:

```env
VITE_API_URL=http://localhost:8000/api
VITE_WS_URL=http://localhost:8000
VITE_DEBUG=true
```

### Backend Connection

The frontend connects to the backend at `http://localhost:8000`. Make sure the backend is running:

```bash
cd backend
python -m uvicorn app.main:sio_app --reload
```

## 🎬 Demo Mode

If the backend is not available, the frontend automatically enables **Demo Mode**:
- Animated mock vehicles
- Simulated signal changes
- Dynamic density updates
- Full UI functionality

This allows showcasing the UI without requiring the backend.

## 📦 Build

```bash
# Production build
npm run build

# Preview production build
npm run preview
```

## 🎯 Key Components

### CityMap Component
- Canvas-based 2D rendering
- Grid overlay with major/minor lines
- Roads with density color-coding
- Junctions with traffic signals
- Animated vehicles with direction indicators
- Hover tooltips for junction details

### Control Panel
- Play/Pause/Reset buttons
- Speed slider (0.5x - 5x)
- Agent strategy toggle (RL/Rules)
- Real-time status indicators

### Statistics Panel
- 4 primary stat cards
- 4 performance metric cards
- Density distribution bar
- Auto-refresh every 2 seconds

## 🌈 UI Theme

The UI uses a cyberpunk/tech aesthetic with:
- **Primary**: Cyan (#06B6D4)
- **Secondary**: Purple (#8B5CF6)
- **Background**: Slate (#0F172A)
- **Custom fonts**: Outfit (sans), JetBrains Mono (mono), Orbitron (display)

## 📄 License

MIT License - AutonomousHacks 2026
