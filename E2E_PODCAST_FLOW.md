# End-to-End Podcast Generation Flow

## Flow Overview

```
User Types Message in Chat UI
    ↓
Chat API (/api/chat/message)
    ↓
Intent Detection (detect_agent_intent)
    ↓
MCP Service Called? → YES (if "create podcast" in message)
    ↓
Call MCP Agent: "create_podcast"
    ↓
Document Generator Service
    ↓
Podcast Service
    ↓
LLM (with PodcastService temperature settings)
    ↓
Audio Generation (TTS)
    ↓
Return Audio File
```

---

## Detailed Step-by-Step Flow

### 1. **User Types Message** (Frontend)
```
User: "create podcast about encrypted visibility engine"
```

### 2. **Chat API Receives Request**
**File:** [backend/app/api/chat.py](backend/app/api/chat.py#L155)
**Endpoint:** `POST /api/chat/message`

**Request Model:**
```python
class ChatMessageRequest(BaseModel):
    message: str
    session_id: Optional[int] = None
    model_id: Optional[str] = "auto"
    content_type: Optional[str] = None  # Can be "podcast", "ppt", "mp3", "wav", "speech"
```

### 3. **Intent Detection** (Chat API)
**File:** [backend/app/api/chat.py](backend/app/api/chat.py#L102)
**Function:** `detect_agent_intent(message: str)`

```python
def detect_agent_intent(message: str) -> Optional[Dict[str, Any]]:
    """Detect if message requires an agent call"""
    if any(keyword in message_lower for keyword in 
           ["create podcast", "make podcast", "generate podcast", "podcast"]):
        
        # Returns agent intent
        return {
            "agent": "create_podcast",  # ← MCP AGENT CALLED HERE!
            "params": {
                "topic": topic,
                "description": message
            }
        }
```

**Result:** Detects `create_podcast` MCP agent should be called ✓

### 4. **MCP Service Called**
**File:** [backend/app/api/chat.py](backend/app/api/chat.py#L820)
**Service:** [backend/app/services/mcp_service.py](backend/app/services/mcp_service.py#L1)

```python
# In chat.py - calls MCP agent
agent_result = await mcp_service.call_agent(
    agent_intent["agent"],           # "create_podcast"
    agent_intent["params"],          # {topic, description}
    {"user_id": ..., "role": ...}    # user context
)
```

**MCP Service routes to:** [backend/app/services/mcp_service.py](backend/app/services/mcp_service.py#L150)
```python
async def _handle_local_agent(self, agent_id: str, params: Dict, user_context: Dict):
    if agent_id == "create_podcast":
        # Podcast generation logic
        from app.services.document_generator import DocumentGenerator
        ...
```

### 5. **Document Generator Called**
**File:** [backend/app/services/document_generator.py](backend/app/services/document_generator.py#L24)

```python
class DocumentGenerator:
    async def generate(
        self,
        content: str,
        doc_type: str,  # "podcast" or "mp3" or "wav"
        user_context: Dict[str, Any],
        ...
    ) -> Tuple[bytes, str, str]:
        
        if doc_type == "podcast":
            return await self._generate_podcast(...)
```

### 6. **Podcast Service Called** (Independent Service)
**File:** [backend/app/services/document_generator.py](backend/app/services/document_generator.py#L655)

```python
async def _generate_podcast(self, content, user_context, format, ...):
    # Delegate to independent PodcastService
    dialogue = await podcast_service.generate_script(
        content=content,
        topic=topic,
        user_context=user_context
    )
```

### 7. **LLM Generates Podcast Script**
**File:** [backend/app/services/podcast_service.py](backend/app/services/podcast_service.py#L40)

```python
class PodcastService:
    def __init__(self, config: Optional[PodcastServiceConfig] = None):
        self.config = config or PodcastServiceConfig()
        # TEMPERATURE = 0.9  (for natural dialogue)
        # MAX_TOKENS = 12000
    
    async def generate_script(self, content, topic, user_context):
        # Create podcast prompt
        podcast_prompt = self._create_prompt(content, topic)
        
        # Get LLM with Podcast config
        llm = model_manager.get_chat_model(
            model_id=self.config.MODEL_ID,
            temperature=self.config.TEMPERATURE  # ← TUNING POINT
        )
        
        # Invoke LLM
        response = await self._invoke_llm(llm, podcast_prompt)
        
        # Extract & return podcast dialogue
        podcast = self._extract_response(response)
        return podcast
```

**LLM Output Example:**
```
Host: Welcome to our podcast about encrypted visibility engine.
Guest: Thank you for having me. Let me explain what this technology does.
Host: Please, go ahead.
Guest: The encrypted visibility engine enables organizations to...
[continues...]
```

### 8. **Audio Generation (TTS)**
**File:** [backend/app/services/document_generator.py](backend/app/services/document_generator.py#L655)

```python
async def _generate_podcast(self, content, ...):
    dialogue = await podcast_service.generate_script(...)
    
    # Convert dialogue to audio
    audio_data = await asyncio.to_thread(
        tts_service.text_to_speech_dialogue,
        dialogue,
        audio_format=audio_format,
        use_dialogue=True  # Parses Host/Guest for two voices
    )
    
    return audio_data, filename, content_type
```

**TTS Service:** Uses OpenAI TTS with:
- Host voice: `nova` (configurable via `OPENAI_TTS_VOICE_HOST`)
- Guest voice: `onyx` (configurable via `OPENAI_TTS_VOICE_GUEST`)

### 9. **Response Returned**
**File:** [backend/app/services/mcp_service.py](backend/app/services/mcp_service.py#L150)

```python
# MCP service formats response
return {
    "status": "success",
    "audio_data": base64_encoded_audio,
    "filename": "podcast_topic_1234567890.mp3",
    "format": "mp3",
    "message": "Successfully generated podcast dialogue in MP3 format"
}
```

### 10. **Chat API Returns to User**
**File:** [backend/app/api/chat.py](backend/app/api/chat.py#L820)

```python
# Save assistant message to database
assistant_message = ChatMessage(
    session_id=session.id,
    role="assistant",
    content=f"Agent Response: {json.dumps(agent_result, indent=2)}",
    metadata={
        "agent_call": {
            "agent": "create_podcast",
            "result": agent_result
        }
    }
)

# Return to frontend
return {
    "message_id": assistant_message.id,
    "role": "assistant",
    "content": assistant_content,
    "metadata": metadata
}
```

---

## Temperature Tuning Points

### 1. **Podcast Generation**
- **Location:** [backend/app/services/podcast_service.py](backend/app/services/podcast_service.py#L17)
- **Current Default:** `TEMPERATURE = 0.9` (natural, varied dialogue)
- **Environment Variable:** `PODCAST_TEMPERATURE` (add to `.env`)
- **Affects:** Script generation randomness/creativity

### 2. **Speech Generation**
- **Location:** [backend/app/services/speech_service.py](backend/app/services/speech_service.py#L17)
- **Current Default:** `TEMPERATURE = 0.7` (clear, focused)
- **Environment Variable:** `SPEECH_TEMPERATURE` (add to `.env`)
- **Affects:** Monologue text generation

### 3. **RAG/Q&A Responses**
- **Location:** [backend/app/services/rag_service.py](backend/app/services/rag_service.py#L532)
- **Current Default:** `temperature=0` (hardcoded - deterministic)
- **Environment Variable:** `RAG_TEMPERATURE` (add to `.env` to make tunable)
- **Affects:** Chat response generation from documents

---

## MCP Involvement

### ✅ **MCP IS USED** in Podcast Flow:

1. **Intent Detection** → Detects "create podcast" keyword
2. **MCP Agent Called** → Routes to `mcp_service.call_agent("create_podcast", ...)`
3. **Agent Handler** → `_handle_local_agent()` processes the podcast generation
4. **Response Formatted** → Returns structured agent result

### ⚠️ **MCP Wrapping:**
- MCP is a **wrapper/orchestrator** around the actual Podcast Service
- The actual LLM call happens in **PodcastService**, not in MCP
- MCP handles:
  - Intent detection
  - Parameter extraction
  - Service routing
  - Response formatting

### Alternative Path (Direct API):
Users could also generate podcast **without MCP** by calling:
- `POST /api/generate/document` with `type: "podcast"`
  - This bypasses MCP agent orchestration
  - Directly calls DocumentGenerator

---

## Key Files Summary

| File | Purpose | Temperature Setting |
|------|---------|-------------------|
| [backend/app/api/chat.py](backend/app/api/chat.py) | Chat endpoint, intent detection | N/A |
| [backend/app/services/mcp_service.py](backend/app/services/mcp_service.py) | MCP agent routing | N/A |
| [backend/app/services/document_generator.py](backend/app/services/document_generator.py) | Document/audio generation orchestrator | N/A |
| [backend/app/services/podcast_service.py](backend/app/services/podcast_service.py) | Podcast script generation | `PODCAST_TEMPERATURE = 0.9` |
| [backend/app/services/speech_service.py](backend/app/services/speech_service.py) | Speech/monologue generation | `SPEECH_TEMPERATURE = 0.7` |
| [backend/app/services/rag_service.py](backend/app/services/rag_service.py) | RAG context + Q&A | `temperature=0` (hardcoded) |
| [backend/app/services/tts_service.py](backend/app/services/tts_service.py) | Text-to-speech audio | Uses OpenAI TTS voices |

---

## Sequence Diagram

```
┌─────────┐      ┌──────────┐      ┌──────────┐      ┌────────┐      ┌────────┐
│ Frontend│      │ Chat API │      │ MCP Svc  │      │ Doc Gen│      │Podcast │
└─────────┘      └──────────┘      └──────────┘      └────────┘      └────────┘
     │                 │                  │               │               │
     │ "create         │                  │               │               │
     │  podcast"       │                  │               │               │
     ├────────────────>│                  │               │               │
     │                 │ detect_intent    │               │               │
     │                 │ "create_podcast" │               │               │
     │                 │ agent=true       │               │               │
     │                 ├─────────────────>│               │               │
     │                 │                  │ _generate_ppt │               │
     │                 │                  ├──────────────>│               │
     │                 │                  │               │ generate_script
     │                 │                  │               ├──────────────>│
     │                 │                  │               │               │
     │                 │                  │               │  LLM call     │
     │                 │                  │               │  temp=0.9     │
     │                 │                  │               │<──────────────┤
     │                 │                  │               │               │
     │                 │                  │               │ "Host: ... "  │
     │                 │                  │               │ "Guest: ..."  │
     │                 │                  │               │               │
     │                 │  agent_result    │               │               │
     │                 │  (base64 audio)  │               │               │
     │<────────────────┤<─────────────────┤<──────────────┤               │
     │                 │                  │               │               │
     │ Download audio  │                  │               │               │
     │ Play podcast    │                  │               │               │
     └─────────────────┘                  └───────────────┘               └───────────┘
```

