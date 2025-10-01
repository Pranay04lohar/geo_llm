# Chat History Feature Implementation

## Overview

This implementation adds persistent chat history functionality to the GeoLLM application, allowing users to save, load, and manage their conversations across sessions.

## Features Implemented

### Backend (Python/FastAPI)

1. **Database Models** (`backend/dynamic_rag/app/models/chat_models.py`)
   - `ChatConversation`: Stores conversation metadata (title, user_id, timestamps)
   - `ChatMessage`: Stores individual messages (role, content, metadata)

2. **Database Configuration** (`backend/dynamic_rag/app/database.py`)
   - SQLAlchemy async setup with SQLite
   - Connection pooling and session management
   - Database initialization and cleanup

3. **API Endpoints** (`backend/dynamic_rag/app/routers/chat_router.py`)
   - `GET /api/v1/conversations` - List user conversations
   - `POST /api/v1/conversations` - Create new conversation
   - `GET /api/v1/conversations/{id}` - Get specific conversation
   - `GET /api/v1/conversations/{id}/messages` - Get conversation messages
   - `POST /api/v1/conversations/{id}/messages` - Add message to conversation
   - `PUT /api/v1/conversations/{id}` - Update conversation
   - `DELETE /api/v1/conversations/{id}` - Delete conversation

### Frontend (React/Next.js)

1. **API Integration** (`frontend/src/utils/api.js`)
   - Chat history API functions with authentication
   - Error handling and user feedback

2. **Custom Hook** (`frontend/src/hooks/useChatHistory.js`)
   - Centralized chat history state management
   - CRUD operations for conversations and messages
   - Automatic loading on user authentication

3. **UI Integration** (`frontend/src/app/page.js`)
   - Real-time chat history in left sidebar
   - Conversation selection and loading
   - Message persistence to database
   - User authentication integration

## Key Features

### ✅ User-Specific Chat History
- Each user sees only their own conversations
- Firebase authentication integration
- Automatic loading on sign-in

### ✅ Persistent Storage
- Messages saved to SQLite database
- Conversation metadata (title, timestamps, message count)
- Cross-session persistence

### ✅ Real-Time UI Updates
- Dynamic sidebar with conversation list
- Message count and last updated timestamps
- Loading states and error handling

### ✅ Message Management
- Automatic saving of user and assistant messages
- Metadata storage for RAG retrieval results
- Error message handling

### ✅ Conversation Management
- Create new conversations with custom titles
- Delete conversations
- Load existing conversations
- Clear current conversation

## Database Schema

```sql
-- Conversations table
CREATE TABLE chat_conversations (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(128) NOT NULL,
    title VARCHAR(255) NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    is_active BOOLEAN DEFAULT TRUE
);

-- Messages table
CREATE TABLE chat_messages (
    id VARCHAR(36) PRIMARY KEY,
    conversation_id VARCHAR(36) NOT NULL,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    created_at DATETIME NOT NULL,
    metadata TEXT,
    FOREIGN KEY (conversation_id) REFERENCES chat_conversations(id)
);
```

## Setup Instructions

### Backend Setup

1. **Install Dependencies**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Start the Backend Server**
   ```bash
   cd backend/dynamic_rag
   python main.py
   ```

3. **Test the API** (optional)
   ```bash
   cd backend
   python test_chat_api.py
   ```

### Frontend Setup

1. **Install Dependencies**
   ```bash
   cd frontend
   npm install
   ```

2. **Start the Frontend**
   ```bash
   npm run dev
   ```

## Usage

1. **Sign In**: Users must be authenticated to use chat history
2. **Create Conversation**: Click "New Chat" button to create a new conversation
3. **View History**: Left sidebar shows all user conversations
4. **Load Conversation**: Click on any conversation to load its messages
5. **Automatic Saving**: Messages are automatically saved to the database
6. **Delete Conversations**: Hover over conversations to see delete button

## Technical Details

### Authentication Flow
- Firebase ID tokens used for user identification
- User ID extracted from JWT token
- All API calls include authentication headers

### Message Flow
1. User sends message → Saved to local state + database
2. Assistant responds → Saved to local state + database
3. Conversation selection → Loads messages from database
4. New conversation → Creates new conversation in database

### Error Handling
- Graceful fallback to localStorage if database unavailable
- User-friendly error messages
- Automatic retry mechanisms

## Future Enhancements

- [ ] Search functionality in conversations
- [ ] Conversation export/import
- [ ] Message editing capabilities
- [ ] Conversation sharing
- [ ] Advanced filtering and sorting
- [ ] Message threading
- [ ] File attachments in messages

## Files Modified/Created

### Backend
- `backend/dynamic_rag/app/models/chat_models.py` (new)
- `backend/dynamic_rag/app/database.py` (new)
- `backend/dynamic_rag/app/routers/chat_router.py` (new)
- `backend/dynamic_rag/app/main.py` (modified)
- `backend/dynamic_rag/app/config.py` (modified)
- `backend/requirements.txt` (modified)

### Frontend
- `frontend/src/hooks/useChatHistory.js` (new)
- `frontend/src/utils/api.js` (modified)
- `frontend/src/app/page.js` (modified)

### Documentation
- `CHAT_HISTORY_README.md` (new)
- `backend/test_chat_api.py` (new)
