## Project Structure

GeoLLM/
│
├── backend/ # FastAPI backend
│ ├── app/
│ │ ├── main.py # FastAPI entrypoint
│ │ ├── routers/
│ │ │ └── query_router.py # /query endpoint
│ │ ├── services/
│ │ │ ├── classifier.py # LangChain + Mistral classification
│ │ │ ├── geospatial.py # GEE & ROI handling
│ │ │ ├── rag.py # RAG (pgvector search)
│ │ │ └── llm.py # LLM prompt assembly
│ │ ├── utils/
│ │ │ ├── geojson_utils.py # ROI validation, conversion
│ │ │ └── embedding_utils.py # SentenceTransformer helpers
│ │ ├── config.py # Env vars, model paths, DB configs
│ │ └── models.py # Pydantic models
│ ├── requirements.txt # Python dependencies
│ ├── Dockerfile # Optional deployment
│ └── README.md
│
├── frontend/ # Next.js frontend (App Router)
│ ├── app/
│ │ ├── page.js # Home page layout
│ │ ├── layout.js # Root layout
│ │ └── globals.css # Global styles
│ ├── components/ # UI components
│ │ ├── ChatInput.js # User query input
│ │ ├── MapView.js # MapLibre ROI view
│ │ └── ResultPanel.js # Display API response
│ ├── services/
│ │ └── api.js # API call functions (Axios/fetch)
│ ├── public/ # Static assets
│ ├── .gitignore # Already included by Next.js
│ ├── package.json # Frontend dependencies
│ ├── next.config.js # Next.js config
│ └── README.md
│
├── .gitignore # Root ignore file (optional)
└── README.md # Main project instructions
