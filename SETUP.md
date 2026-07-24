## Setup (run once)
1. `cd backend && python -m venv venv && source venv/bin/activate`
2. `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and add your GEMINI_API_KEY
4. `uvicorn main:app --reload --port 8000` (only works once main.py mounts your router — 
   until then, test your router standalone per your role's test script)

## Frontend
1. `cd frontend && npm install`
2. `npm run dev`