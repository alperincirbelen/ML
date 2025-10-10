# MoonLight Desktop UI

Flutter-based Windows desktop application for MoonLight Fixed-Time Trading AI.

## 🎨 Design System

### Color Palette
- **Primary (Purple)**: `#6D28D9`
- **Accent (Blue)**: `#2563EB`
- **Success (Green)**: `#10B981`
- **Danger (Red)**: `#EF4444`
- **Dark Background**: `#0B0F17`
- **Light Background**: `#FFFFFF`

### Typography
- **Font Family**: Inter (Google Fonts)
- **Headings**: Bold, Title sizes
- **Body**: Regular, Medium sizes

### Components
- **Cards**: Rounded 16px, elevation 2
- **Buttons**: Rounded 12px
- **Inputs**: Rounded 12px, filled

## 🚀 Development

### Prerequisites
- Flutter SDK 3.x
- Windows 10/11

### Setup

```bash
cd ui_app
flutter pub get
```

### Run

```bash
flutter run -d windows
```

### Build

```bash
flutter build windows
```

## 📁 Structure

```
lib/
├─ app/               # App configuration
├─ core/              # Core services (API client)
├─ features/          # Feature modules
│  ├─ dashboard/
│  ├─ accounts/
│  ├─ products/
│  ├─ strategies/
│  └─ settings/
└─ widgets/           # Shared widgets
```

## 🔌 API Integration

### REST Endpoints
- `GET http://127.0.0.1:8750/status` - System status
- `GET http://127.0.0.1:8750/accounts` - Account list
- `GET http://127.0.0.1:8750/products` - Product list
- `POST http://127.0.0.1:8750/start` - Start workers
- `POST http://127.0.0.1:8750/stop` - Stop workers

### WebSocket
- `ws://127.0.0.1:8751/ws` - Real-time metrics, trade updates, alerts

## 🧪 Testing

```bash
flutter test
```

## 📦 Packaging

### MSIX Package

```bash
flutter pub run msix:create
```

### Portable ZIP
Build output will be in `build/windows/runner/Release/`
