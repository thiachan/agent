import os

# Disable ChromaDB telemetry warnings BEFORE any chromadb imports
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_CLIENT_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY"] = "False"

from typing import List, Dict, Optional
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain.prompts import PromptTemplate
from app.core.config import settings
from app.services.model_manager import model_manager

import chromadb

# Suppress ChromaDB telemetry logger errors
import logging
chromadb_telemetry_logger = logging.getLogger("chromadb.telemetry.product.posthog")
chromadb_telemetry_logger.setLevel(logging.CRITICAL)
chromadb_telemetry_logger.disabled = True
chromadb_logger = logging.getLogger("chromadb.telemetry")
chromadb_logger.setLevel(logging.CRITICAL)
chromadb_logger.disabled = True
try:
    from openai import AuthenticationError
except ImportError:
    AuthenticationError = Exception  # Fallback if openai not available

# Import LLM types for isinstance checks
try:
    from langchain_openai import ChatOpenAI, AzureChatOpenAI
except ImportError:
    ChatOpenAI = None
    AzureChatOpenAI = None

try:
    from langchain_aws import ChatBedrock, BedrockLLM
except ImportError:
    ChatBedrock = None
    BedrockLLM = None

class RAGService:
    def __init__(self):
        self.embeddings = None
        self.vector_store = None
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        self._initialize_embeddings()
        self._initialize_vector_store()
    
    def _initialize_embeddings(self):
        """Initialize embeddings model - Only OpenAI embeddings"""
        try:
            self.embeddings = model_manager.get_embedding_model()
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Could not initialize OpenAI embedding model: {e}")
            raise ValueError("No embedding models available. Please configure OPENAI_API_KEY for embeddings.")
    
    def _initialize_vector_store(self):
        """Initialize or load the ChromaDB vector store"""
        if not self.embeddings:
            raise ValueError("Embeddings not initialized")
        os.makedirs(settings.VECTOR_DB_PATH, exist_ok=True)
        
        self.vector_store = Chroma(
            persist_directory=settings.VECTOR_DB_PATH,
            embedding_function=self.embeddings
        )
    
    def add_document(self, text: str, metadata: Dict) -> List[str]:
        """Add a document to the vector store and return chunk IDs"""
        import logging
        logger = logging.getLogger(__name__)
        
        # Ensure embeddings and vector store are initialized
        if not self.embeddings:
            self._initialize_embeddings()
        if not self.vector_store:
            self._initialize_vector_store()
        
        try:
            logger.info(f"Splitting text into chunks for document {metadata.get('document_id')}")
            texts = self.text_splitter.split_text(text)
            logger.info(f"Split into {len(texts)} chunks")
            
            if not texts:
                logger.warning("No text chunks created, using empty text")
                texts = [" "]
            
            metadatas = [metadata for _ in texts]
            ids = [f"{metadata['document_id']}_{i}" for i in range(len(texts))]
            
            logger.info(f"Adding {len(texts)} chunks to vector store...")
            self.vector_store.add_texts(
                texts=texts,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(f"Successfully added {len(ids)} chunks to vector store")
            return ids
        except Exception as e:
            logger.error(f"Error adding document to vector store: {e}", exc_info=True)
            raise
    
    def delete_document(self, document_id: int):
        """Delete all chunks for a document"""
        # Get all IDs for this document
        collection = self.vector_store._collection
        results = collection.get(where={"document_id": document_id})
        if results and results.get("ids"):
            collection.delete(ids=results["ids"])
    
    def search(self, query: str, user_role: str, limit: int = 10, previously_used_docs: Optional[set] = None) -> List[Dict]:
        """Search for relevant documents based on query and user permissions"""
        import logging
        logger = logging.getLogger(__name__)
        
        # Normalize query: handle variations like "zero trust" vs "zero-trust" vs "Zero Trust"
        normalized_query = query.lower()
        # Replace hyphens with spaces for better matching
        normalized_query = normalized_query.replace("-", " ")
        # Also try with hyphens
        hyphenated_query = query.lower().replace(" ", "-")
        
        # Expand search to get more results, then filter
        # Use a larger k value to ensure we get enough results after filtering
        search_k = limit * 4  # Search for 4x the limit to account for filtering
        
        # Try multiple search strategies for better retrieval
        all_results = []
        
        # Strategy 1: Direct similarity search with original query
        try:
            results = self.vector_store.similarity_search_with_score(query, k=search_k)
            all_results.extend([(doc, score) for doc, score in results])
        except Exception as e:
            logger.warning(f"Similarity search failed: {e}")
        
        # Strategy 2: Search with normalized query (spaces instead of hyphens)
        if normalized_query != query.lower():
            try:
                results = self.vector_store.similarity_search_with_score(normalized_query, k=search_k)
                all_results.extend([(doc, score * 0.95) for doc, score in results])  # Slightly lower weight
            except Exception as e:
                logger.debug(f"Normalized query search failed: {e}")
        
        # Strategy 3: Search with hyphenated query
        if hyphenated_query != query.lower():
            try:
                results = self.vector_store.similarity_search_with_score(hyphenated_query, k=search_k)
                all_results.extend([(doc, score * 0.95) for doc, score in results])  # Slightly lower weight
            except Exception as e:
                logger.debug(f"Hyphenated query search failed: {e}")
        
        # Strategy 4: Extract key terms and search individually
        query_terms = normalized_query.split()
        # Filter out common words and keep important terms
        stop_words = {"what", "are", "the", "for", "is", "a", "an", "and", "or", "but", "in", "on", "at", "to", "of", "with"}
        important_terms = [term for term in query_terms if len(term) > 3 and term not in stop_words]
        
        if important_terms:
            for term in important_terms[:3]:  # Try top 3 important terms
                try:
                    term_results = self.vector_store.similarity_search_with_score(term, k=search_k // 2)
                    all_results.extend([(doc, score * 0.7) for doc, score in term_results])  # Lower weight for term-only searches
                except Exception as e:
                    logger.debug(f"Term search for '{term}' failed: {e}")
        
        # Strategy 5: Search by filename if query mentions document names
        # Check if query contains common document name patterns
        try:
            collection = self.vector_store._collection
            all_docs = collection.get()  # Get all documents metadata
            if all_docs and "metadatas" in all_docs:
                for metadata in all_docs["metadatas"]:
                    filename = metadata.get("filename", "").lower()
                    # If query mentions part of filename, include those documents
                    if filename and any(term in filename for term in important_terms if len(term) > 4):
                        # Get chunks for this document
                        doc_id = metadata.get("document_id")
                        if doc_id:
                            doc_results = collection.get(where={"document_id": doc_id})
                            if doc_results and "ids" in doc_results:
                                # Add these chunks with a moderate score
                                for i, chunk_id in enumerate(doc_results["ids"][:5]):  # Limit to 5 chunks per doc
                                    try:
                                        chunk_data = collection.get(ids=[chunk_id])
                                        if chunk_data and "documents" in chunk_data and chunk_data["documents"]:
                                            # Create a document-like object
                                            from langchain.schema import Document
                                            doc = Document(
                                                page_content=chunk_data["documents"][0],
                                                metadata=metadata
                                            )
                                            all_results.append((doc, 0.5))  # Moderate score for filename match
                                    except Exception as e:
                                        logger.debug(f"Error getting chunk {chunk_id}: {e}")
        except Exception as e:
            logger.debug(f"Filename-based search failed: {e}")
        
        # Remove duplicates and apply document-level relevance boosting
        seen_ids = set()
        unique_results = []
        
        # Extract key terms from query for document matching
        query_lower = normalized_query.lower()
        query_terms = set([term for term in query_lower.split() if len(term) > 3])
        
        for doc, score in all_results:
            doc_id = doc.metadata.get('document_id')
            chunk_id = f"{doc_id}_{doc.page_content[:50]}"  # Use content hash for uniqueness
            if chunk_id not in seen_ids:
                seen_ids.add(chunk_id)
                
                # DOCUMENT-LEVEL RELEVANCE BOOSTING
                # If query terms match document filename/title/tags, boost this chunk's relevance
                filename = doc.metadata.get('filename', '').lower()
                title = doc.metadata.get('title', '').lower()
                tags = doc.metadata.get('tags', '').lower()
                
                # Check if query terms appear in document name
                filename_match_score = 0.0
                if filename:
                    # Count how many query terms appear in filename
                    matching_terms = sum(1 for term in query_terms if term in filename)
                    if matching_terms > 0:
                        # Strong boost: reduce score (lower = better) by up to 0.4 for strong matches
                        # This ensures documents with matching names rank much higher
                        match_ratio = matching_terms / max(len(query_terms), 1)
                        if match_ratio >= 0.5:  # 50%+ of terms match
                            filename_match_score = -0.4  # Strong boost
                        else:
                            filename_match_score = -0.25 * match_ratio  # Moderate boost
                    
                    # Also check for phrase matches (e.g., "ai protection" in "ai model protection")
                    query_phrase = ' '.join(sorted(query_terms))  # Normalize phrase
                    filename_words = set(filename.split())
                    if len(query_terms) >= 2 and all(term in filename_words for term in query_terms):
                        # All query terms are in filename - very strong boost
                        filename_match_score = -0.5
                
                title_match_score = 0.0
                if title:
                    matching_terms = sum(1 for term in query_terms if term in title)
                    if matching_terms > 0:
                        match_ratio = matching_terms / max(len(query_terms), 1)
                        if match_ratio >= 0.5:
                            title_match_score = -0.35  # Strong boost
                        else:
                            title_match_score = -0.2 * match_ratio
                    
                    # Phrase match in title
                    title_words = set(title.split())
                    if len(query_terms) >= 2 and all(term in title_words for term in query_terms):
                        title_match_score = -0.45
                
                # TAG MATCHING - Boost documents with matching tags
                tag_match_score = 0.0
                if tags:
                    # Split tags (comma-separated)
                    tag_list = [tag.strip().lower() for tag in tags.split(',')]
                    matching_tags = sum(1 for term in query_terms if any(term in tag for tag in tag_list))
                    if matching_tags > 0:
                        # Tags are important metadata - give good boost
                        match_ratio = matching_tags / max(len(query_terms), 1)
                        if match_ratio >= 0.5:
                            tag_match_score = -0.3  # Strong boost for tag matches
                        else:
                            tag_match_score = -0.15 * match_ratio
                
                # Apply boosting (subtract from score since lower = better)
                boosted_score = score + filename_match_score + title_match_score + tag_match_score
                
                unique_results.append((doc, boosted_score, score))  # Keep original score for logging
        
        # Sort by boosted score (lower distance = better match)
        unique_results.sort(key=lambda x: x[1])
        
        # Filter by permissions first
        permission_filtered = []
        for doc, boosted_score, original_score in unique_results:
            metadata = doc.metadata
            has_access = (
                metadata.get("is_public", False) or
                user_role in (metadata.get("allowed_roles", "") or "").split(",") or
                metadata.get("owner_id")  # Owner always has access (will be checked at API level)
            )
            if has_access:
                permission_filtered.append({
                    "content": doc.page_content,
                    "score": boosted_score,  # Use boosted score for ranking
                    "original_score": original_score,  # Keep original for logging
                    "metadata": metadata
                })
        
        # PRIORITIZE BOOSTED DOCUMENTS: Documents with matching names should come first
        # Also prioritize documents used in previous conversation messages
        # Group by document and identify boosted documents
        document_chunks = {}  # {document_id: [chunks]}
        boosted_documents = set()  # Track which documents got boosted
        conversation_relevant_docs = set()  # Documents used in previous messages
        
        if previously_used_docs:
            conversation_relevant_docs = previously_used_docs
            logger.info(f"Prioritizing {len(conversation_relevant_docs)} documents from previous conversation context")
        
        for result in permission_filtered:
            doc_id = result["metadata"].get("document_id")
            if doc_id not in document_chunks:
                document_chunks[doc_id] = []
            document_chunks[doc_id].append(result)
            
            # Check if this document was boosted (original_score > score means boost was applied)
            original = result.get("original_score", result["score"])
            if original - result["score"] > 0.01:  # Boost was applied
                boosted_documents.add(doc_id)
            
            # Apply additional boost for documents used in previous conversation
            if doc_id in conversation_relevant_docs:
                # Boost chunks from previously used documents
                result["score"] = result["score"] - 0.3  # Strong boost for conversation continuity
                boosted_documents.add(doc_id)  # Treat as boosted
                logger.debug(f"Boosting document {doc_id} (used in previous conversation)")
        
        filtered_results = []
        
        # FIRST PRIORITY: Take top chunks from boosted documents (documents with matching names)
        boosted_chunks = []
        for doc_id in boosted_documents:
            chunks = document_chunks[doc_id]
            chunks.sort(key=lambda x: x["score"])  # Sort by boosted score
            boosted_chunks.extend(chunks)
        
        # Sort all boosted chunks by score and add them first
        boosted_chunks.sort(key=lambda x: x["score"])
        for chunk in boosted_chunks:
            if len(filtered_results) < limit:
                filtered_results.append(chunk)
        
        # SECOND PRIORITY: Diversify across remaining documents (non-boosted)
        non_boosted_docs = [doc_id for doc_id in document_chunks.keys() if doc_id not in boosted_documents]
        if non_boosted_docs and len(filtered_results) < limit:
            chunks_per_doc = max(1, (limit - len(filtered_results)) // max(len(non_boosted_docs), 1))
            
            for doc_id in non_boosted_docs:
                chunks = document_chunks[doc_id]
                chunks.sort(key=lambda x: x["score"])
                for chunk in chunks[:chunks_per_doc]:
                    if len(filtered_results) < limit:
                        filtered_results.append(chunk)
        
        # THIRD PRIORITY: Fill remaining slots with best chunks across all documents
        if len(filtered_results) < limit:
            remaining_chunks = []
            added_content = {r["content"][:50] for r in filtered_results}
            
            for doc_id, chunks in document_chunks.items():
                for chunk in chunks:
                    if chunk["content"][:50] not in added_content:
                        remaining_chunks.append(chunk)
            
            remaining_chunks.sort(key=lambda x: x["score"])
            for chunk in remaining_chunks:
                if len(filtered_results) < limit:
                    filtered_results.append(chunk)
        
        # Final sort by score to ensure best matches are first
        filtered_results.sort(key=lambda x: x["score"])
        
        # Log what we found for debugging
        if filtered_results:
            logger.info(f"Found {len(filtered_results)} relevant chunks from {len(document_chunks)} documents for query: '{query}'")
            for i, result in enumerate(filtered_results[:5]):  # Log top 5
                doc_name = result["metadata"].get("filename", result["metadata"].get("title", "Unknown"))
                original = result.get("original_score", result["score"])
                boosted = result["score"]
                boost_applied = original - boosted
                if boost_applied > 0.01:
                    logger.info(f"  {i+1}. {doc_name} (boosted score: {boosted:.4f}, original: {original:.4f}, boost: -{boost_applied:.4f})")
                else:
                    logger.info(f"  {i+1}. {doc_name} (score: {boosted:.4f})")
        else:
            logger.warning(f"No documents found for query: '{query}' (searched {len(unique_results)} total chunks)")
        
        return filtered_results
    
    def query(self, question: str, user_role: str, model_id: Optional[str] = None, conversation_history: Optional[List[Dict[str, str]]] = None, content_type: Optional[str] = None) -> Dict:
        """Query the RAG system with a question and optional conversation history
        
        Args:
            question: The user's question
            user_role: User role for access control
            model_id: Optional model ID to use
            conversation_history: Optional conversation history for context
            content_type: Optional content type (doc, ppt, mp4, podcast, speech) to streamline retrieval
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # If content_type is provided, enhance the query to focus on relevant content
        enhanced_question = question
        if content_type:
            # Add context hints based on content type to improve RAG retrieval
            content_type_hints = {
                "doc": "document report information",
                "ppt": "presentation slides content",
                "mp4": "demo video tutorial",
                "podcast": "dialogue conversation interview",
                "speech": "monologue speech talking points"
            }
            if content_type in content_type_hints:
                enhanced_question = f"{question} {content_type_hints[content_type]}"
        
        # Detect if this is a command/action request (like "save as doc", "create podcast", etc.)
        # If so, extract the topic from conversation history instead of using the literal query
        question_lower = enhanced_question.lower().strip()
        is_action_request = any(phrase in question_lower for phrase in [
            "save as", "save it as", "create", "generate", "make", "convert to",
            "export as", "download as", "turn into"
        ])
        
        # Extract previously used documents from conversation history
        # This helps maintain context - if we discussed "zone segmentation" before,
        # we should prioritize those documents for follow-up questions
        previously_used_docs = set()
        topic_keywords = []
        
        if conversation_history and len(conversation_history) > 0:
            # Look through previous assistant messages to find which documents were cited
            for msg in reversed(conversation_history[-10:]):  # Check last 10 messages
                if msg.get("role") == "assistant":
                    # Check if metadata contains sources
                    if isinstance(msg, dict) and "metadata" in msg:
                        sources = msg.get("metadata", {}).get("sources", [])
                        for source in sources:
                            doc_id = source.get("metadata", {}).get("document_id")
                            filename = source.get("metadata", {}).get("filename", "")
                            if doc_id:
                                previously_used_docs.add(doc_id)
                            if filename:
                                # Extract keywords from filename for topic matching
                                filename_lower = filename.lower()
                                # Extract meaningful words (not common words)
                                words = [w for w in filename_lower.replace(".", " ").replace("-", " ").split() 
                                        if len(w) > 3 and w not in ["study", "guide", "demo", "script", "deck", "document"]]
                                topic_keywords.extend(words)
            
            # Also extract topic from previous user questions
            for msg in reversed(conversation_history[-10:]):
                if msg.get("role") == "user":
                    content = msg.get("content", "").strip()
                    # Skip short responses
                    if len(content) > 20 and not content.lower() in ["yes", "no", "ok", "thanks", "thank you"]:
                        # Extract key terms from the question
                        words = [w for w in content.lower().split() if len(w) > 3]
                        topic_keywords.extend(words)
                        break  # Use the most recent substantial question
        
        # Build enhanced search query
        search_query = question
        if is_action_request and conversation_history and len(conversation_history) > 0:
            # Extract the topic from previous user questions
            topic_query = None
            for msg in reversed(conversation_history):
                if msg.get("role") == "user":
                    content = msg.get("content", "").strip()
                    if len(content) > 20 and not content.lower() in ["yes", "no", "ok", "thanks", "thank you"]:
                        topic_query = content
                        break
            
            if topic_query:
                logger.info(f"Action request detected: '{question}'. Using topic from conversation history: '{topic_query[:100]}...'")
                search_query = topic_query
            else:
                logger.info(f"Action request detected but no topic found in conversation history. Using original query.")
        elif topic_keywords:
            # For follow-up questions, enhance the query with topic keywords
            # This helps maintain context across the conversation
            unique_keywords = list(set(topic_keywords))[:5]  # Top 5 unique keywords
            if unique_keywords:
                enhanced_query = f"{question} {' '.join(unique_keywords)}"
                logger.info(f"Enhancing search query with topic keywords from conversation: {unique_keywords}")
                search_query = enhanced_query
        
        # Get relevant context - use the search query (which may be enhanced with topic keywords)
        context_docs = self.search(search_query, user_role, limit=10, previously_used_docs=previously_used_docs)
        
        # Log the search results for debugging
        if context_docs:
            if search_query != question:
                logger.info(f"Retrieved {len(context_docs)} document chunks for action request: '{question}' (searched using topic: '{search_query[:100]}...')")
            else:
                logger.info(f"Retrieved {len(context_docs)} document chunks for question: '{question}'")
            for i, doc in enumerate(context_docs[:5]):  # Log top 5
                doc_name = doc["metadata"].get("filename", doc["metadata"].get("title", "Unknown"))
                logger.info(f"  Chunk {i+1}: From '{doc_name}' (similarity score: {doc['score']:.4f})")
        else:
            logger.warning(f"No context found for question: '{question}' (searched using: '{search_query}')")
        
        context = "\n\n".join([doc["content"] for doc in context_docs])
        
        # Get the LLM model
        try:
            llm = model_manager.get_chat_model(model_id=model_id, temperature=0)
        except ValueError as e:
            # No models configured - return a helpful message
            logger.warning(f"No chat models available: {e}")
            if context_docs:
                # Return context-based answer even without LLM
                return {
                    "answer": f"Based on the available documents, here's what I found:\n\n{context[:500]}...\n\nNote: AI chat models are not configured. Please set OPENAI_API_KEY or AWS Bedrock credentials to enable full AI responses.",
                    "sources": [
                        {
                            "content": doc["content"][:200],
                            "metadata": doc["metadata"]
                        }
                        for doc in context_docs[:3]
                    ]
                }
            else:
                return {
                    "answer": "I couldn't find any relevant information in the uploaded documents. Also, AI chat models are not configured. Please set OPENAI_API_KEY or AWS Bedrock credentials to enable AI-powered responses.",
                    "sources": []
                }
        
        # Use the search method which already filters by permissions
        # Then create a simple prompt-based answer
        if not context_docs:
            # STRICT: No RAG context = No answer (don't use training data)
            return {
                "answer": "I cannot find this information in the uploaded documents. The RAG system (Retrieval-Augmented Generation) is my only source of truth, and I do not have access to this information in the uploaded documents. Please upload relevant documents or rephrase your question.",
                "sources": []
            }
        
        # Build conversation history context if available
        history_context = ""
        if conversation_history and len(conversation_history) > 0:
            history_context = "\n\nIMPORTANT - Previous Conversation Context:\n"
            # Include more messages and more content for better context
            for msg in conversation_history[-10:]:  # Last 10 messages (5 exchanges)
                role_label = "User" if msg.get("role") == "user" else "Assistant"
                content = msg.get('content', '')
                # Include more content (up to 1000 chars) to preserve full context
                if len(content) > 1000:
                    content = content[:1000] + "..."
                history_context += f"{role_label}: {content}\n"
            history_context += "\nNOTE: When the user refers to 'it', 'this', 'that', or uses pronouns, refer to the previous conversation to understand what they're referring to. For example, if they previously asked about a topic and now say 'save it as doc', 'it' refers to the previous answer about that topic.\n"
        
        # Create prompt with context and conversation history
        # PROACTIVE RAG PROMPT: Extract and present information directly
        prompt_template = """You are an AI assistant for GSSE AI Center. Your role is to be extremely helpful by extracting, synthesizing, and presenting information directly from the uploaded documents.

CRITICAL INSTRUCTIONS:
1. **USE CONVERSATION HISTORY**: If the user refers to "it", "this", "that", or uses pronouns, look at the previous conversation to understand what they're referring to. For example:
   - If they previously asked "What is Cloud Edge?" and now say "save it as doc", "it" refers to the previous answer about Cloud Edge
   - If they say "create a podcast about this", "this" refers to the topic discussed in previous messages
   - Always check the conversation history to resolve references and pronouns

2. **EXTRACT AND PRESENT DIRECTLY**: Your primary goal is to extract key information from the documents and present it directly to the user. Do NOT just tell them to "refer to this document" - actually provide the information they need.

3. **BE COMPREHENSIVE**: Dig deep into the context provided. Extract all relevant information, key points, features, benefits, and details. Synthesize information from multiple document sections when relevant.

4. **BE HELPFUL AND PROACTIVE**: 
   - If the user asks about a topic, provide a complete, detailed answer based on the documents
   - Include all relevant details, not just a summary
   - Extract specific examples, numbers, features, and technical details
   - If creating content (like speeches, summaries, presentations), include ALL key points from the documents
   - If the user asks to "save as doc", "save as PDF", "save it as doc", "save it as PDF", or similar:
     * First, identify what "it" or "this" refers to by checking the conversation history
     * Acknowledge that you understand they want to save the previous answer/content
     * Provide the content in a format ready for document generation
     * Mention that they can use the document generation feature to create the file

5. **SYNTHESIZE INFORMATION**: Combine information from multiple document sections to provide comprehensive answers. Don't just cite sources - actually extract and present the information.

6. **USE ONLY DOCUMENT CONTEXT**: Base your answer ONLY on the information provided in the "Context from documents" section below. Do not use general knowledge or training data.

7. **CITE SOURCES AT THE END**: After providing a comprehensive answer, you may include a brief note about which documents the information came from, but do NOT use citations as a way to avoid providing information.

8. **IF INFORMATION IS MISSING**: Only if the context truly doesn't contain relevant information, then state that. But first, make sure you've thoroughly searched the context for any related information.

{history_context}

Context from documents (extract and synthesize information from this):
{context}

Current Question: {question}

IMPORTANT: Before answering, check if the question contains pronouns or references like "it", "this", "that". If so, refer to the conversation history above to understand what the user is referring to. Then provide a comprehensive, detailed answer by extracting and presenting all relevant information directly from the documents above. Be thorough and helpful:"""
        
        prompt = PromptTemplate(
            template=prompt_template,
            input_variables=["context", "question", "history_context"]
        )
        
        # Format the prompt
        formatted_prompt = prompt.format(
            context=context, 
            question=question,
            history_context=history_context
        )
        
        # Generate answer using LLM
        try:
            from langchain_aws import ChatBedrock, BedrockLLM
            from langchain_openai import AzureChatOpenAI, ChatOpenAI
            import logging
            logger = logging.getLogger(__name__)
            
            # Check model type and invoke appropriately
            if isinstance(llm, AzureChatOpenAI):
                # AzureChatOpenAI (Cisco) - use messages format
                from langchain.schema import HumanMessage
                messages = [HumanMessage(content=formatted_prompt)]
                logger.info(f"Invoking AzureChatOpenAI (Cisco) with {len(messages)} message(s)")
                try:
                    # Add user parameter with appkey if configured
                    from app.core.config import settings
                    invoke_kwargs = {}
                    if settings.CISCO_APPKEY:
                        import json
                        user_data = {"appkey": settings.CISCO_APPKEY}
                        invoke_kwargs["user"] = json.dumps(user_data)
                    
                    response = llm.invoke(messages, **invoke_kwargs)
                except Exception as auth_error:
                    # Check if it's an authentication error (token expired)
                    error_str = str(auth_error)
                    is_auth_error = (
                        isinstance(auth_error, AuthenticationError) or
                        "401" in error_str or
                        "expired" in error_str.lower() or
                        "authentication" in error_str.lower() or
                        "Token has expired" in error_str
                    )
                    if is_auth_error:
                        logger.warning("Cisco token expired during request, refreshing and retrying...")
                        # Refresh token and retry once
                        model_manager._initialize_cisco()  # Force refresh
                        # Recreate the LLM with new token
                        token = model_manager._get_cisco_token()
                        if token:
                            # Recreate the LLM instance with fresh token
                            deployment_name = settings.CISCO_DEPLOYMENT
                            if not deployment_name:
                                endpoint_parts = settings.CISCO_ENDPOINT.split("/")
                                for i, part in enumerate(endpoint_parts):
                                    if part == "deployments" and i + 1 < len(endpoint_parts):
                                        deployment_name = endpoint_parts[i + 1]
                                        break
                            if not deployment_name:
                                deployment_name = "gpt-4.1"
                            
                            llm = AzureChatOpenAI(
                                azure_endpoint="https://chat-ai.cisco.com",
                                azure_deployment=deployment_name,
                                openai_api_key=token,
                                openai_api_version="2024-08-01-preview",
                                temperature=0
                            )
                            # Retry the request
                            try:
                                response = llm.invoke(messages, **invoke_kwargs)
                            except Exception as retry_error:
                                logger.error(f"Azure/Cisco API error on retry: {retry_error}", exc_info=True)
                                raise
                        else:
                            raise ValueError("Failed to refresh Cisco token after expiration")
                    else:
                        logger.error(f"Azure/Cisco API error: {auth_error}", exc_info=True)
                        raise
            elif isinstance(llm, BedrockLLM):
                # BedrockLLM (for models that don't support chat) - use string prompt
                import time
                logger.info("Invoking BedrockLLM with string prompt")
                
                # Retry logic for Bedrock with exponential backoff
                max_retries = 5
                base_delay = 2  # Start with 2 seconds
                
                for attempt in range(max_retries):
                    try:
                        response = llm.invoke(formatted_prompt)
                        break  # Success, exit retry loop
                    except Exception as bedrock_error:
                        error_str = str(bedrock_error)
                        
                        # Check if it's a throttling error
                        is_throttling = (
                            "ThrottlingException" in error_str or 
                            "Too many requests" in error_str or
                            "throttl" in error_str.lower()
                        )
                        
                        if is_throttling and attempt < max_retries - 1:
                            # Calculate exponential backoff delay
                            delay = base_delay * (2 ** attempt) + (attempt * 0.5)  # Exponential backoff with jitter
                            logger.warning(
                                f"Bedrock throttling detected (attempt {attempt + 1}/{max_retries}). "
                                f"Retrying in {delay:.1f} seconds..."
                            )
                            time.sleep(delay)
                            continue
                        
                        # Handle throttling after max retries
                        if is_throttling:
                            error_msg = (
                                f"AWS Bedrock rate limit exceeded. Please wait a moment and try again.\n\n"
                                f"The system attempted {max_retries} times with exponential backoff.\n"
                                f"Please wait 30-60 seconds before trying again."
                            )
                            logger.error(error_msg)
                            raise ValueError(error_msg)
                        
                        raise
            elif isinstance(llm, ChatBedrock):
                # ChatBedrock - use messages format
                from langchain.schema import HumanMessage
                import time
                messages = [HumanMessage(content=formatted_prompt)]
                logger.info(f"Invoking ChatBedrock with {len(messages)} message(s)")
                
                # Retry logic for Bedrock with exponential backoff
                max_retries = 5
                base_delay = 2  # Start with 2 seconds
                
                for attempt in range(max_retries):
                    try:
                        response = llm.invoke(messages)
                        break  # Success, exit retry loop
                    except Exception as bedrock_error:
                        error_str = str(bedrock_error)
                        
                        # Check if it's a throttling error
                        is_throttling = (
                            "ThrottlingException" in error_str or 
                            "Too many requests" in error_str or
                            "throttl" in error_str.lower()
                        )
                        
                        if is_throttling and attempt < max_retries - 1:
                            # Calculate exponential backoff delay
                            delay = base_delay * (2 ** attempt) + (attempt * 0.5)  # Exponential backoff with jitter
                            logger.warning(
                                f"Bedrock throttling detected (attempt {attempt + 1}/{max_retries}). "
                                f"Retrying in {delay:.1f} seconds..."
                            )
                            time.sleep(delay)
                            continue
                        
                        # Log the actual error from Bedrock
                        logger.error(f"Bedrock API error: {bedrock_error}", exc_info=True)
                        
                        # Check if it's a response parsing error (NoneType subscriptable)
                        if "'NoneType' object is not subscriptable" in error_str or "outputs" in error_str.lower():
                            error_msg = (
                                f"Bedrock model returned an invalid response. This usually means:\n"
                                f"1. The model ID format is incorrect (try using just 'model:version' instead of full ARN)\n"
                                f"2. The model is not available in your AWS account or region\n"
                                f"3. AWS credentials don't have Bedrock access permissions\n"
                                f"4. The model request format is incompatible\n\n"
                                f"Original error: {bedrock_error}\n\n"
                                f"Try using a simple model ID format like 'mistral.mistral-large-2407-v1:0' "
                                f"instead of an ARN, or verify the model is available in region {settings.AWS_REGION}."
                            )
                            logger.error(error_msg)
                            raise ValueError(error_msg)
                        
                        # Handle throttling after max retries
                        if is_throttling:
                            error_msg = (
                                f"AWS Bedrock rate limit exceeded. Please wait a moment and try again.\n\n"
                                f"The system attempted {max_retries} times with exponential backoff.\n"
                                f"This usually happens when:\n"
                                f"1. Too many requests are being made in a short time\n"
                                f"2. Your AWS account has rate limits on Bedrock usage\n"
                                f"3. Multiple users are using the system simultaneously\n\n"
                                f"Please wait 30-60 seconds before trying again."
                            )
                            logger.error(error_msg)
                            raise ValueError(error_msg)
                        
                        raise
            elif isinstance(llm, ChatOpenAI):
                # Regular ChatOpenAI - use messages format
                from langchain.schema import HumanMessage
                messages = [HumanMessage(content=formatted_prompt)]
                logger.info(f"Invoking ChatOpenAI with {len(messages)} message(s)")
                response = llm.invoke(messages)
            else:
                # Other models can take string directly
                response = llm.invoke(formatted_prompt)
            
            # Handle different response types
            if response is None:
                raise ValueError("LLM returned None response")
            
            # Try to get content from response
            if hasattr(response, 'content'):
                answer = response.content
            elif isinstance(response, str):
                answer = response
            elif hasattr(response, 'text'):
                answer = response.text
            elif isinstance(response, dict):
                # Some models return dict with 'text' or 'content' key
                answer = response.get('text') or response.get('content') or str(response)
            else:
                # Fallback: convert to string
                answer = str(response)
                
            if not answer or not answer.strip():
                raise ValueError("LLM returned empty response")
            
            # Post-processing: Validate that answer references RAG context
            # If the answer seems to be generic knowledge without referencing the context,
            # add a reminder that RAG is the source
            answer_lower = answer.lower()
            context_lower = context.lower()
            
            # Check if answer might be using general knowledge instead of RAG
            # If context is provided but answer doesn't seem to reference it, add a note
            if context and len(context) > 100:
                # Simple heuristic: if answer doesn't contain any words from context (beyond common words)
                # it might be using general knowledge
                context_words = set(context_lower.split())
                answer_words = set(answer_lower.split())
                common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they'}
                context_unique_words = context_words - common_words
                answer_unique_words = answer_words - common_words
                
                # If there's minimal overlap, the answer might not be based on context
                overlap = len(context_unique_words & answer_unique_words)
                if len(context_unique_words) > 0 and overlap < 2 and len(answer_unique_words) > 5:
                    # Answer might be using general knowledge - add a reminder
                    logger.warning(f"Answer may not be based on RAG context. Overlap: {overlap}/{len(context_unique_words)} unique words")
                    # Don't modify the answer, but log it for monitoring
                
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error invoking LLM: {e}, LLM type: {type(llm).__name__}, Error details: {str(e)}", exc_info=True)
            # Return a helpful error message instead of crashing
            return {
                "answer": f"I encountered an error while generating a response: {str(e)}. Please check your model configuration and AWS Bedrock credentials.",
                "sources": [
                    {
                        "content": doc["content"][:200],
                        "metadata": doc["metadata"]
                    }
                    for doc in context_docs[:3]
                ]
            }
        
        return {
            "answer": answer,
            "sources": [
                {
                    "content": doc["content"][:200],
                    "metadata": doc["metadata"]
                }
                for doc in context_docs[:5]
            ]
        }

# Global instance
rag_service = RAGService()

