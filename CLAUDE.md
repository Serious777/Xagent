# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Xagent is an AI-powered innovation analysis system for power battery PACK design, implementing the TRIZ ARIZ methodology through a 9-step structured workflow. The system guides users from problem identification to innovative solution generation.

## Commands

### Backend
```bash
# Start backend server
cd backend
source venv/bin/activate
python app.py

# Run tests
cd backend
source venv/bin/activate
python -m pytest tests/ -v

# Run specific test
python -m pytest tests/test_agent_persist.py -v

# Seed component database
python seed_components.py
```

### Frontend
```bash
# Install dependencies
cd frontend
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Lint
npm run lint
```

### Full Stack
```bash
# Start both backend and frontend
./start.sh

# Stop all services
./stop.sh
```

## Architecture

### Backend (Python/Flask)
- **Entry point**: `backend/app.py` - Flask server with CORS, routes, error handlers
- **Agent system**: `backend/agent.py` - XagentAgent class implementing single-step execution with SQLite persistence
- **ARIZ flow**: `backend/ariz_graph.py` - LangGraph StateGraph defining the 9-step workflow with conditional routing
- **State management**: `backend/ariz_state.py` - TypedDict state definition and step utilities
- **Step implementations**: `backend/ariz_nodes.py` - Node functions for each ARIZ step
- **Component database**: `backend/component_db.py` - SQLite operations for battery PACK component knowledge base
- **LLM integration**: `backend/llm.py` - LangChain ChatOpenAI wrapper for Xiaomi MiMo v2.5
- **Prompts**: `backend/prompts/` - Markdown templates for each ARIZ step
- **Sub-agents**: `backend/sub_agents.py` - Specialized agents for database queries and supersystem analysis
- **Observability**: `backend/observability.py` - Tracing and logging utilities

### Frontend (Next.js/React)
- **Entry point**: `frontend/app/page.tsx` - Main page with chat interface and ARIZ step visualization
- **Components**: `frontend/components/` - React components for UI rendering
  - `ArizStepCard.tsx` - Step progress visualization
  - `ArizDetailPanel.tsx` - Detailed step analysis panel
  - `Sidebar.tsx` - Conversation list management
  - `Message.tsx` - Chat message bubbles
- **Styling**: Tailwind CSS with PostCSS
- **State**: React hooks (useState, useRef, useEffect)

### Data Flow
1. User sends message via frontend → Flask `/api/chat` endpoint
2. Backend Agent processes message through current ARIZ step node
3. Step node queries component database if needed (via sub-agents)
4. LLM generates analysis based on step-specific prompts
5. Results persisted to SQLite (`xagent.db`) and returned as card data
6. Frontend parses response and renders ARIZ step visualization

### Key Patterns
- **Single-step execution**: Each user message triggers exactly one ARIZ step
- **State persistence**: Agent state stored in SQLite for conversation continuity
- **Component knowledge base**: Separate SQLite DB (`components.db`) with battery PACK components
- **Conditional routing**: Step 6 (summary) can skip step 7 (causal) if few problems found
- **Streaming responses**: Backend streams text/plain with `X-Vercel-AI-Data-Stream` header

## Environment Variables

Backend `.env` configuration:
- `XIAOMI_API_KEY` (required) - API key for Xiaomi MiMo
- `XIAOMI_BASE_URL` (optional) - API endpoint, defaults to `https://token-plan-cn.xiaomimimo.com/v1`
- `XIAOMI_MODEL` (optional) - Model name, defaults to `mimo-v2.5`
- `FLASK_PORT` (optional) - Server port, defaults to `8000`
- `FLASK_DEBUG` (optional) - Debug mode, defaults to `true`

## Testing

Tests use pytest with the following structure:
- Unit tests for individual modules (agent, state, component_db)
- Integration tests for Flask API endpoints
- No external dependencies required - tests use mocks and in-memory SQLite

Run all tests: `cd backend && python -m pytest tests/ -v`
