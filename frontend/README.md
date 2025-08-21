# GeoLLM Frontend

A modern, interactive geospatial LLM interface built with Next.js, React, and Three.js. Features a beautiful animated Earth background with a sophisticated chat interface for geospatial data analysis.

## 🌍 Features

- **Animated 3D Earth**: Realistic Earth visualization with Three.js
- **Interactive Chat Interface**: Modern chat UI with geospatial query capabilities
- **Collapsible Sidebars**: Left sidebar for chat history, right sidebar for map tools
- **Responsive Design**: Fully responsive layout that works on all devices
- **Modern UI/UX**: Glassmorphism effects, smooth animations, and hover interactions
- **Blue-Cyan Theme**: Consistent color scheme throughout the application

## 🚀 Getting Started

### Prerequisites

- Node.js 18+ 
- npm or yarn

### Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd geo_llm/frontend
```

2. Install dependencies:
```bash
npm install
```

3. Run the development server:
```bash
npm run dev
```

4. Open [http://localhost:3000](http://localhost:3000) in your browser

## 🛠️ Tech Stack

- **Framework**: Next.js 15.4.5
- **React**: 19.1.0
- **3D Graphics**: Three.js with @react-three/fiber
- **Styling**: Tailwind CSS 4
- **Animations**: CSS transitions and Three.js animations

## 📁 Project Structure

```
frontend/
├── src/
│   ├── app/
│   │   ├── page.js          # Main application page
│   │   ├── layout.js        # Root layout component
│   │   └── globals.css      # Global styles
│   └── components/
│       ├── AnimatedEarth.jsx    # 3D Earth component
│       └── CollapsibleSidebar.jsx # Sidebar component
├── public/
│   └── textures/            # Earth texture files
└── package.json
```

## 🎨 UI Components

### Navigation Bar
- Centered "GeoLLM" title
- "Get Plus" button on the left
- Settings icon on the right
- Transparent background with backdrop blur

### Left Sidebar (Chat)
- Chat history with recent conversations
- New chat button
- Search functionality
- User profile section
- Notification indicators

### Right Sidebar (Map Tools)
- Drawing tools (Draw ROI, Select)
- Navigation tools (Zoom In, Reset)
- Map mode toggle (Satellite, Street)
- Map container for visualizations

### Main Chat Area
- Welcome message with animated Earth background
- Floating chat input with microphone and send buttons
- Tools button for additional functionality

## 🎯 Key Features

- **Hover Effects**: All buttons have smooth scale and shadow hover effects
- **Local Storage**: Sidebar collapse states are persisted
- **Responsive**: Mobile-friendly design with proper breakpoints
- **Accessibility**: Proper focus states and keyboard navigation
- **Performance**: Optimized Three.js rendering with proper cleanup

## 📦 Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint

## 🌟 Design Highlights

- **Color Scheme**: Blue-to-cyan gradient (`bg-gradient-to-r from-blue-600 to-cyan-600`)
- **Glassmorphism**: Subtle transparency and backdrop blur effects
- **Smooth Animations**: 200ms transitions for all interactive elements
- **3D Earth**: Realistic Earth texture with proper lighting and rotation
- **Star Field**: Animated background stars for immersive experience

## 🔧 Configuration

The project uses:
- **Tailwind CSS** for styling with custom configuration
- **ESLint** for code quality
- **Next.js** for routing and optimization
- **Three.js** for 3D graphics

## 📄 License

This project is part of the GeoLLM application suite.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run linting: `npm run lint`
5. Submit a pull request

---

Built with ❤️ for geospatial data analysis
