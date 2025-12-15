# Lingua: Advanced Language Learning Platform

## Local Development Setup

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Node.js 18+

### Quick Start

1. **Start Infrastructure**
   ```bash
   docker-compose up -d
   ```

2. **Backend Setup**
   ```bash
   # Create virtual environment
   python3 -m venv venv
   source venv/bin/activate
   
   # Install dependencies
   pip install -r backend/requirements.txt
   
   # Run migrations (after DB is ready)
   cd backend
   alembic upgrade head
   cd ..
   
   # Start server
   uvicorn backend.main:app --reload
   ```

3. **Frontend Setup**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

   Access the app at `http://localhost:3000`.

## Architecture

- **Backend**: FastAPI (Python)
- **Frontend**: React + Vite + Tailwind CSS
- **Database**: PostgreSQL (Structured data + JSONB for graph)
- **Audio**: WebAudio API (Frontend) + librosa (Backend)

## Features

1. **Morphological Pattern Recognition**: Generative rules instead of rote memory
2. **Etymology Graph**: Visual word origins and connections
3. **Phonetics Trainer**: Real-time spectrogram feedback
4. **SRS**: Sentence-level spaced repetition with syntactic tagging
5. **Gloss Reader**: Interlinear morpheme breakdowns
6. **Production Practice**: Output-focused exercises with correction

