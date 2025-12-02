import re
import logging
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple
from app.services.rag_service import rag_service

logger = logging.getLogger(__name__)

class DemoVideoService:
    """Service for finding and retrieving demo videos from RAG documents"""
    
    # YouTube URL patterns
    YOUTUBE_PATTERNS = [
        r'https?://(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)',
        r'https?://(?:www\.)?youtu\.be/([a-zA-Z0-9_-]+)',
        r'https?://(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]+)',
        r'youtube\.com/watch\?v=([a-zA-Z0-9_-]+)',
        r'youtu\.be/([a-zA-Z0-9_-]+)',
    ]
    
    def __init__(self):
        """Initialize the demo video service"""
        self._embeddings = None
    
    def _get_embeddings(self):
        """Get embeddings model from RAG service"""
        if self._embeddings is None:
            self._embeddings = rag_service.embeddings
        return self._embeddings
    
    def _calculate_semantic_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate semantic similarity between two texts using embeddings
        Returns a score between 0.0 and 1.0 (higher = more similar)
        Uses cosine similarity of embeddings
        """
        try:
            embeddings = self._get_embeddings()
            if not embeddings:
                logger.warning("Embeddings not available, using fallback text matching")
                # Fallback: simple text matching
                text1_lower = text1.lower()
                text2_lower = text2.lower()
                if text1_lower in text2_lower or text2_lower in text1_lower:
                    return 0.6
                # Check for word overlap
                words1 = set(text1_lower.split())
                words2 = set(text2_lower.split())
                if words1 and words2:
                    overlap = len(words1.intersection(words2)) / len(words1.union(words2))
                    return overlap
                return 0.3
            
            # Get embeddings for both texts
            emb1 = embeddings.embed_query(text1)
            emb2 = embeddings.embed_query(text2)
            
            # Calculate cosine similarity
            emb1_array = np.array(emb1)
            emb2_array = np.array(emb2)
            
            # Normalize vectors
            norm1 = np.linalg.norm(emb1_array)
            norm2 = np.linalg.norm(emb2_array)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            # Cosine similarity (ranges from -1 to 1, typically 0 to 1 for normalized embeddings)
            similarity = np.dot(emb1_array, emb2_array) / (norm1 * norm2)
            
            # Normalize to 0-1 range (cosine similarity is typically already 0-1 for embeddings)
            # But ensure it's in [0, 1] range
            return max(0.0, min(1.0, (similarity + 1) / 2))
            
        except Exception as e:
            logger.warning(f"Error calculating semantic similarity: {e}, using fallback")
            # Fallback: simple substring check
            text1_lower = text1.lower()
            text2_lower = text2.lower()
            if text1_lower in text2_lower or text2_lower in text1_lower:
                return 0.6
            return 0.3
    
    def _extract_youtube_links(self, text: str) -> List[Dict[str, str]]:
        """
        Extract YouTube links and video IDs from text
        
        Returns list of dicts with:
        - url: Full YouTube URL
        - video_id: YouTube video ID
        - embed_url: Embeddable URL for viewing
        """
        links = []
        seen_ids = set()
        
        for pattern in self.YOUTUBE_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                video_id = match.group(1)
                
                # Skip if we've already found this video
                if video_id in seen_ids:
                    continue
                seen_ids.add(video_id)
                
                # Normalize URL format
                url = f"https://www.youtube.com/watch?v={video_id}"
                embed_url = f"https://www.youtube.com/embed/{video_id}"
                
                links.append({
                    "url": url,
                    "video_id": video_id,
                    "embed_url": embed_url
                })
        
        return links
    
    def _extract_video_title(self, content: str, video_url: str) -> Optional[str]:
        """
        Try to extract video title from content around the YouTube link
        Looks for text before the link that might be the title
        """
        # Find the position of the video URL in content
        url_pos = content.lower().find(video_url.lower())
        if url_pos == -1:
            return None
        
        # Look backwards for potential title (up to 200 chars before)
        start = max(0, url_pos - 200)
        text_before = content[start:url_pos].strip()
        
        # Try to find title patterns:
        # - Text ending with colon or dash before URL
        # - Text on previous line
        lines = text_before.split('\n')
        if lines:
            last_line = lines[-1].strip()
            # Remove common prefixes
            for prefix in ['Video:', 'Demo:', 'Link:', 'Watch:', 'View:', '-', '•']:
                if last_line.startswith(prefix):
                    last_line = last_line[len(prefix):].strip()
            if last_line and len(last_line) > 5 and len(last_line) < 150:
                return last_line
        
        # If no clear title, try to extract from surrounding context
        if text_before:
            # Look for capitalized phrases
            sentences = re.split(r'[.!?]\s+', text_before)
            if sentences:
                last_sentence = sentences[-1].strip()
                if len(last_sentence) > 10 and len(last_sentence) < 150:
                    return last_sentence
        
        return None
    
    def _extract_key_terms(self, query: str) -> List[str]:
        """
        Extract meaningful key terms from query, ignoring stop words
        Returns list of important terms for matching
        """
        # Common stop words to ignore
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
            'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this',
            'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they',
            'what', 'which', 'who', 'when', 'where', 'why', 'how', 'about', 'into',
            'through', 'during', 'before', 'after', 'above', 'below', 'up', 'down',
            'out', 'off', 'over', 'under', 'again', 'further', 'then', 'once',
            'here', 'there', 'when', 'where', 'why', 'how', 'all', 'each', 'few',
            'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only',
            'own', 'same', 'so', 'than', 'too', 'very', 's', 't', 'can', 'will',
            'just', 'don', 'should', 'now', 'video', 'demo', 'videos', 'demos',
            'show', 'shows', 'help', 'please', 'generate', 'create', 'make'
        }
        
        # Normalize query: lowercase, remove punctuation
        query_lower = re.sub(r'[^\w\s-]', ' ', query.lower())
        
        # Split into terms and filter
        terms = query_lower.split()
        key_terms = [
            term.strip('-') 
            for term in terms 
            if len(term.strip('-')) > 2 and term.strip('-') not in stop_words
        ]
        
        # Remove duplicates while preserving order
        seen = set()
        unique_terms = []
        for term in key_terms:
            if term not in seen:
                seen.add(term)
                unique_terms.append(term)
        
        return unique_terms
    
    
    def _clean_query(self, query: str) -> str:
        """
        Clean query by removing generation-related phrases and extracting the actual topic
        Examples:
        - "Please generate a L4 smart switch segmentation video" -> "L4 smart switch segmentation"
        - "please generate a demo video regarding EVE" -> "EVE"
        - "Please generate a smart switch video" -> "smart switch"
        - "give re: eve" -> "eve"
        - "give me eve" -> "eve"
        - "show me aiops" -> "aiops"
        """
        # Remove common generation phrases
        generation_phrases = [
            r'please\s+generate\s+(a\s+)?(demo\s+)?(video\s+)?(regarding\s+)?(about\s+)?',
            r'generate\s+(a\s+)?(demo\s+)?(video\s+)?(regarding\s+)?(about\s+)?',
            r'create\s+(a\s+)?(demo\s+)?(video\s+)?(regarding\s+)?(about\s+)?',
            r'make\s+(a\s+)?(demo\s+)?(video\s+)?(regarding\s+)?(about\s+)?',
            r'(demo\s+)?video\s+(about|regarding|for|on)\s+',
            r'^please\s+',
            r'\s+video\s*$',
            r'\s+demo\s+video\s*$',
        ]
        
        cleaned = query.lower().strip()
        for pattern in generation_phrases:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        # Remove common request phrases (e.g., "give re:", "give me", "show me", "find", "get")
        request_phrases = [
            r'^give\s+(re:?\s*)?(me\s+)?',
            r'^show\s+(me\s+)?',
            r'^find\s+(me\s+)?(a\s+)?(demo\s+)?(video\s+)?(for\s+)?(about\s+)?',
            r'^get\s+(me\s+)?(a\s+)?(demo\s+)?(video\s+)?(for\s+)?(about\s+)?',
            r'^i\s+want\s+(a\s+)?(demo\s+)?(video\s+)?(for\s+)?(about\s+)?',
            r'^can\s+you\s+(give|show|find|get)\s+(me\s+)?(a\s+)?(demo\s+)?(video\s+)?(for\s+)?(about\s+)?',
        ]
        
        for pattern in request_phrases:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        # Clean up extra spaces and punctuation
        cleaned = re.sub(r'[^\w\s-]', ' ', cleaned)  # Remove special chars except hyphens
        cleaned = ' '.join(cleaned.split())
        return cleaned.strip()
    
    def _extract_tags_from_content(self, content: str) -> List[str]:
        """Extract tags from TAGS: line in document content"""
        tags = []
        # Look for TAGS: line
        tag_match = re.search(r'TAGS:\s*(.+)', content, re.IGNORECASE | re.MULTILINE)
        if tag_match:
            tag_line = tag_match.group(1).strip()
            # Split by comma and clean
            tags = [tag.strip() for tag in tag_line.split(',') if tag.strip()]
        return tags
    
    def _extract_product_from_content(self, content: str, filename: str) -> Optional[str]:
        """Extract product name from document content (title line)"""
        # Look for title line format: "Category | Product Name" or "Product Name"
        lines = content.split('\n')
        for line in lines[:15]:  # Check first 15 lines (title is usually early)
            line = line.strip()
            if not line or line.startswith('TAGS:'):
                continue
            
            # Format: "Category | Product Name" (most common)
            if '|' in line and len(line) < 200:
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 2:
                    # Product name is after the |
                    product = parts[-1].strip()
                    # Remove "demo-video" suffix if present
                    product = re.sub(r'\s*demo\s*video\s*$', '', product, flags=re.IGNORECASE)
                    # Clean up extra spaces
                    product = ' '.join(product.split())
                    if product and len(product) > 3:
                        return product
            
            # Also check if line looks like a product name (no |, but has key terms)
            elif len(line) > 5 and len(line) < 150:
                # Check if it contains product indicators
                line_lower = line.lower()
                if any(indicator in line_lower for indicator in ['snortml', 'eve', 'aiops', 'rtc', 'sgt', 'mcd', 'hypershield', 'l4']):
                    # This might be a product name
                    product = line.strip()
                    product = re.sub(r'\s*demo\s*video\s*$', '', product, flags=re.IGNORECASE)
                    product = ' '.join(product.split())
                    if product and len(product) > 3:
                        return product
        
        # Fallback: extract from filename
        name = Path(filename).stem
        name = name.replace('_', ' ').replace('-', ' ')
        name = re.sub(r'\s*demo\s*video\s*$', '', name, flags=re.IGNORECASE)
        name = ' '.join(name.split())
        return name if name and len(name) > 3 else None
    
    def _matches_query_precisely(self, query: str, content: str, filename: str, metadata: Dict) -> bool:
        """
        Precise matching based on actual document structure for 100% accuracy:
        1. Check tags from TAGS: line (highest priority - most reliable)
        2. Check product name from title line
        3. Check filename (normalized)
        4. Check metadata tags
        """
        query_lower = query.lower().strip()
        # Extract meaningful terms (length > 2, or single character if it's the whole query)
        query_terms = [term for term in query_lower.split() if len(term) > 2]
        
        # If no terms found (e.g., "eve" is 3 chars, but if query is "eve" it should be included)
        # OR if query is a single word (even if short), include it
        if not query_terms:
            # Single word or very short query - use the whole query as a term
            query_terms = [query_lower] if query_lower else []
        
        # Also handle case where query is a single short word that was filtered out
        # (e.g., "eve" would be included since len > 2, but "ai" would not)
        if not query_terms and len(query_lower) >= 2:
            query_terms = [query_lower]
        
        # Extract tags - PRIORITIZE metadata tags (more reliable, stored per document)
        # Content tags might not be in every RAG chunk, but metadata tags are always available
        metadata_tags = metadata.get("tags", "")
        if metadata_tags:
            metadata_tags_list = [tag.strip().lower() for tag in str(metadata_tags).split(',') if tag.strip()]
        else:
            metadata_tags_list = []
        
        # Also try to extract from content (TAGS: line) as fallback
        content_tags = self._extract_tags_from_content(content)
        content_tags_lower = [tag.strip().lower() for tag in content_tags if tag.strip()]
        
        # Combine: metadata tags first (more reliable), then content tags
        # Remove duplicates while preserving order
        seen = set()
        all_tags = []
        for tag in metadata_tags_list + content_tags_lower:
            if tag and tag not in seen:
                seen.add(tag)
                all_tags.append(tag)
        
        logger.debug(f"  Metadata tags: {metadata_tags_list[:3]}, Content tags: {content_tags_lower[:3]}, Combined: {all_tags[:5]}")
        
        # Extract product name from title line
        product_name = self._extract_product_from_content(content, filename)
        if product_name:
            product_lower = product_name.lower()
        else:
            product_lower = ""
        
        filename_lower = filename.lower().replace('_', ' ').replace('-', ' ')
        title_lower = metadata.get("title", "").lower()
        
        logger.debug(f"  Query: '{query_lower}', Terms: {query_terms}")
        logger.debug(f"  Product: '{product_lower}', Tags: {all_tags[:5]}")
        logger.debug(f"  Filename: '{filename_lower[:50]}...'")
        
        # Special handling for common product acronyms (case-insensitive)
        # Map common queries to product names
        product_acronyms = {
            'eve': ['eve', 'encrypted visibility engine'],
            'aiops': ['aiops', 'ai ops', 'scc', 'security cloud control'],
            'rtc': ['rtc', 'rapid threat containment'],
            'sgt': ['sgt', 'security group tags'],
            'mcd': ['mcd', 'automated cloud security orchestration'],
            'snortml': ['snortml', 'snort ml', 'zero day'],
        }
        
        # Check if query matches any known acronym
        for acronym, variations in product_acronyms.items():
            if query_lower == acronym or query_lower in variations:
                # Check if any variation appears in tags, product, or filename
                for variation in variations:
                    if any(variation in tag for tag in all_tags):
                        logger.info(f"  ✅ Query '{query_lower}' matches known acronym '{acronym}' via tag variation '{variation}'")
                        return True
                    if product_lower and variation in product_lower:
                        logger.info(f"  ✅ Query '{query_lower}' matches known acronym '{acronym}' via product name")
                        return True
                    if variation in filename_lower:
                        logger.info(f"  ✅ Query '{query_lower}' matches known acronym '{acronym}' via filename")
                        return True
        
        # PRIORITY 1: Check if query matches product name exactly (most specific)
        if product_lower:
            # Exact match or query is substring of product
            if query_lower == product_lower or query_lower in product_lower or product_lower in query_lower:
                logger.info(f"  ✅ Matches product name: '{product_name}'")
                return True
            
            # For single word queries, check if it appears as a word in product name
            if len(query_terms) == 1:
                term = query_terms[0]
                product_words = product_lower.split()
                # Check if term is a word in product name (e.g., "eve" in "dc edge eve encrypted")
                if term in product_words:
                    logger.info(f"  ✅ Single term '{term}' found as word in product name: '{product_name}'")
                    return True
                # Check if term is substring of any word (e.g., "eve" in "eve" or "encrypted")
                if any(term in word for word in product_words):
                    logger.info(f"  ✅ Single term '{term}' found in product name words: '{product_name}'")
                    return True
            
            # Check if all query terms are in product name
            if all(term in product_lower for term in query_terms):
                logger.info(f"  ✅ All query terms in product name: '{product_name}'")
                return True
        
        # PRIORITY 2: Check tags (very reliable - explicitly defined in documents)
        if all_tags:
            # Check if query matches any tag exactly (case-insensitive)
            for tag in all_tags:
                # Exact match
                if query_lower == tag:
                    logger.info(f"  ✅ Matches tag exactly: '{tag}'")
                    return True
                # Query is substring of tag (e.g., "eve" in "eve, encrypted visibility engine")
                if query_lower in tag:
                    logger.info(f"  ✅ Query found in tag: '{tag}'")
                    return True
                # Tag is substring of query (e.g., "aiops" tag in "aiops scc" query)
                if tag in query_lower:
                    logger.info(f"  ✅ Tag found in query: '{tag}'")
                    return True
            
            # Check if all query terms appear in tags
            if len(query_terms) == 1:
                # Single term query - check if term appears in any tag
                term = query_terms[0]
                for tag in all_tags:
                    # Check if term is in tag (e.g., "eve" in "eve, encrypted visibility")
                    if term in tag:
                        logger.info(f"  ✅ Single term '{term}' found in tag: '{tag}'")
                        return True
                    # Check if tag word matches term (e.g., tag "eve" matches query "eve")
                    tag_words = tag.split()
                    if term in tag_words or any(term in word for word in tag_words):
                        logger.info(f"  ✅ Single term '{term}' matches tag word: '{tag}'")
                        return True
            else:
                # Multiple terms - check if all terms are covered by tags
                matching_tags = []
                for term in query_terms:
                    for tag in all_tags:
                        if term in tag:
                            matching_tags.append(tag)
                            break
                
                if len(matching_tags) >= len(query_terms):
                    logger.info(f"  ✅ All query terms match tags: {matching_tags[:3]}")
                    return True
        
        # PRIORITY 3: Check filename (normalized - remove underscores, dashes)
        if query_terms:
            # Normalize filename: replace underscores and dashes with spaces, then split
            filename_normalized = filename_lower.replace('_', ' ').replace('-', ' ')
            filename_words = set(filename_normalized.split())
            
            # For single term queries, check if term is in filename
            if len(query_terms) == 1:
                term = query_terms[0]
                # Check if term is a word in filename (e.g., "eve" in "dc edge eve encrypted")
                if term in filename_words:
                    logger.info(f"  ✅ Single term '{term}' found as word in filename")
                    return True
                # Check if term is substring of any filename word (e.g., "eve" in "eve" or "encrypted")
                if any(term in word for word in filename_words):
                    logger.info(f"  ✅ Single term '{term}' found in filename words")
                    return True
                # Check if term appears anywhere in filename string
                if term in filename_normalized:
                    logger.info(f"  ✅ Single term '{term}' found in filename string")
                    return True
            else:
                # Multiple terms - require ALL terms to match
                matching_terms = sum(1 for term in query_terms if any(term in word for word in filename_words) or term in filename_normalized)
                if matching_terms == len(query_terms):
                    logger.info(f"  ✅ All query terms match filename")
                    return True
        
        # PRIORITY 4: Check title
        if query_terms and title_lower:
            title_words = set(title_lower.split())
            if len(query_terms) == 1:
                if query_terms[0] in title_words or any(query_terms[0] in word for word in title_words):
                    logger.info(f"  ✅ Single term matches title")
                    return True
            else:
                matching_terms = sum(1 for term in query_terms if any(term in word for word in title_words))
                if matching_terms == len(query_terms):
                    logger.info(f"  ✅ All query terms match title")
                    return True
        
        # No precise match found
        logger.warning(f"  ❌ No precise match - query: '{query_lower}'")
        return False
    
    def _calculate_relevance_score(
        self, 
        query: str, 
        content: str, 
        filename: str, 
        metadata: Dict,
        rag_score: float
    ) -> float:
        """
        Calculate relevance score for suggestions (partial matches)
        Returns score 0.0-1.0 (higher = more relevant)
        """
        query_lower = query.lower().strip()
        query_terms = [term for term in query_lower.split() if len(term) > 2]
        
        if not query_terms:
            query_terms = [query_lower]
        
        score = 0.0
        
        # Extract tags - prioritize metadata (more reliable)
        metadata_tags = metadata.get("tags", "")
        if metadata_tags:
            metadata_tags_list = [tag.strip().lower() for tag in str(metadata_tags).split(',') if tag.strip()]
        else:
            metadata_tags_list = []
        
        content_tags = self._extract_tags_from_content(content)
        content_tags_lower = [tag.strip().lower() for tag in content_tags if tag.strip()]
        
        # Combine tags (metadata first)
        seen = set()
        all_tags = []
        for tag in metadata_tags_list + content_tags_lower:
            if tag and tag not in seen:
                seen.add(tag)
                all_tags.append(tag)
        
        product_name = self._extract_product_from_content(content, filename)
        product_lower = product_name.lower() if product_name else ""
        filename_lower = filename.lower().replace('_', ' ').replace('-', ' ')
        title_lower = metadata.get("title", "").lower()
        
        # Check partial matches (weighted scoring)
        
        # Tag matches (high weight - 40%)
        if all_tags:
            matching_terms = 0
            for term in query_terms:
                # Check if term appears in any tag
                if any(term in tag or tag in term or term in tag.split() for tag in all_tags):
                    matching_terms += 1
            
            if matching_terms > 0:
                tag_ratio = matching_terms / len(query_terms)
                tag_score = tag_ratio * 0.4
                score += tag_score
                logger.debug(f"    Tag match: {matching_terms}/{len(query_terms)} terms = {tag_score:.3f}")
        
        # Product name matches (high weight - 30%)
        if product_lower:
            matching_terms = sum(1 for term in query_terms if term in product_lower or any(term in word for word in product_lower.split()))
            if matching_terms > 0:
                product_ratio = matching_terms / len(query_terms)
                product_score = product_ratio * 0.3
                score += product_score
                logger.debug(f"    Product match: {matching_terms}/{len(query_terms)} terms = {product_score:.3f}")
        
        # Filename matches (medium weight - 20%)
        filename_words = set(filename_lower.split())
        matching_terms = sum(1 for term in query_terms if any(term in word for word in filename_words) or term in filename_lower)
        if matching_terms > 0:
            filename_ratio = matching_terms / len(query_terms)
            filename_score = filename_ratio * 0.2
            score += filename_score
            logger.debug(f"    Filename match: {matching_terms}/{len(query_terms)} terms = {filename_score:.3f}")
        
        # RAG score (low weight - 10% - already considered in search)
        # Normalize RAG score (typically 0-1, but can be negative for distance)
        normalized_rag = max(0.0, min(1.0, (rag_score + 1) / 2)) if rag_score < 0 else min(1.0, rag_score)
        rag_contribution = normalized_rag * 0.1
        score += rag_contribution
        logger.debug(f"    RAG score: {rag_score:.3f} (normalized: {normalized_rag:.3f}) = {rag_contribution:.3f}")
        
        final_score = min(score, 1.0)
        logger.debug(f"    Total relevance score: {final_score:.3f}")
        
        return final_score
    
    def find_demo_videos(
        self, 
        query: str, 
        user_role: str = "user",
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Search for demo videos matching the query in RAG documents
        Uses precise matching based on actual document structure:
        - Tags from TAGS: line
        - Product names from title
        - Filename matching
        - Metadata tags
        
        Args:
            query: Search query (e.g., "SnortML", "EVE", "Cloud Edge", "RTC")
            user_role: User role for RAG access control
            limit: Maximum number of videos to return (default: 10)
        
        Returns:
            Dict with:
            - status: "success" or "error"
            - videos: List of video dicts with url, embed_url, video_id, title, description
            - message: Status message
        """
        try:
            # Clean the query first to extract the actual topic
            cleaned_query = self._clean_query(query)
            logger.info(f"Query: '{query}' -> Cleaned: '{cleaned_query}'")
            
            # Use cleaned query for RAG search (more focused)
            search_query = cleaned_query if cleaned_query else query
            
            # Search RAG for relevant documents
            search_results = rag_service.search(
                query=search_query,
                user_role=user_role,
                limit=limit * 2  # Get more results to filter through
            )
            
            logger.info(f"RAG search returned {len(search_results)} results")
            
            if not search_results:
                return {
                    "status": "success",
                    "videos": [],
                    "message": f"No documents found matching '{cleaned_query or query}'. Try different keywords."
                }
            
            # Sort by RAG score (highest first)
            sorted_results = sorted(search_results, key=lambda x: x.get("score", 0), reverse=True)
            
            # PRECISE MATCHING: Use actual document structure for 100% accuracy
            videos = []
            suggestions = []  # Near matches to suggest if no precise match
            seen_video_ids = set()
            
            logger.info(f"Processing {len(sorted_results)} RAG results for precise matching")
            
            for result in sorted_results:
                original_content = result.get("content", "")
                metadata = result.get("metadata", {})
                rag_score = result.get("score", 0.0)
                filename = metadata.get("filename", "Unknown")
                
                logger.info(f"Evaluating: {filename} (RAG score: {rag_score:.3f})")
                
                # Extract YouTube links from this result
                youtube_links = self._extract_youtube_links(original_content)
                
                if not youtube_links:
                    logger.debug(f"  No videos found in this document")
                    continue
                
                # PRECISE MATCHING: Check if this document matches the query
                query_for_matching = cleaned_query if cleaned_query else query
                is_precise_match = self._matches_query_precisely(
                    query_for_matching, 
                    original_content, 
                    filename, 
                    metadata
                )
                
                if not is_precise_match:
                    # Calculate relevance score for suggestions (partial match)
                    relevance_score = self._calculate_relevance_score(
                        query_for_matching,
                        original_content,
                        filename,
                        metadata,
                        rag_score
                    )
                    
                    logger.info(f"  📊 Relevance score: {relevance_score:.3f} (threshold: 0.2)")
                    
                    # If relevance is reasonable, add as suggestion
                    # Lowered threshold to 0.2 to catch more relevant suggestions
                    if relevance_score > 0.2:  # Threshold for suggestions (lowered from 0.3)
                        logger.info(f"  💡 SUGGESTION - Relevance: {relevance_score:.3f} > 0.2")
                        # Store as suggestion (will be added to videos if no precise matches)
                        suggestions.append({
                            "result": result,
                            "youtube_links": youtube_links,
                            "relevance_score": relevance_score,
                            "rag_score": rag_score,
                            "filename": filename
                        })
                    else:
                        logger.warning(f"  ❌ REJECTED - Relevance too low: {relevance_score:.3f} <= 0.2")
                    continue
                
                logger.info(f"  ✅ ACCEPTED - Precise match found")
                
                # Process each video in this matching result
                for link_info in youtube_links:
                    video_id = link_info["video_id"]
                    
                    # Skip duplicates
                    if video_id in seen_video_ids:
                        logger.debug(f"  Skipping duplicate video: {video_id}")
                        continue
                    seen_video_ids.add(video_id)
                    
                    # Extract title from document (prefer title line, then filename)
                    title = self._extract_product_from_content(original_content, filename)
                    if not title:
                        title = self._extract_video_title(original_content, link_info["url"])
                    if not title:
                        # Use filename as fallback
                        title = filename.rsplit('.', 1)[0].replace('_', ' ')
                    
                    # Get description from content snippet around the video
                    url_pos = original_content.lower().find(link_info["url"].lower())
                    if url_pos > 0:
                        start = max(0, url_pos - 200)
                        end = min(len(original_content), url_pos + 200)
                        description = original_content[start:end].strip()
                    else:
                        description = original_content[:300].strip()
                    
                    if len(description) > 300:
                        description = description[:300] + "..."
                    
                    video_info = {
                        "video_id": video_id,
                        "url": link_info["url"],
                        "embed_url": link_info["embed_url"],
                        "title": title,
                        "description": description,
                        "source_document": filename,
                        "relevance_score": rag_score
                    }
                    
                    videos.append(video_info)
                    logger.info(f"  ✅ Added video: {title} (video_id: {video_id})")
                    
                    # Stop if we have enough videos
                    if len(videos) >= limit:
                        break
                
                # Stop if we have enough videos
                if len(videos) >= limit:
                    break
            
            # If no precise matches, use suggestions (if available)
            if not videos and suggestions:
                logger.info(f"No precise matches found, but {len(suggestions)} suggestion(s) available")
                logger.info(f"Suggestions found for query '{query}' (cleaned: '{cleaned_query}'):")
                for i, sug in enumerate(suggestions[:5], 1):
                    logger.info(f"  {i}. {sug.get('filename', 'Unknown')} (relevance: {sug['relevance_score']:.3f}, RAG: {sug['rag_score']:.3f})")
                
                # Sort suggestions by relevance score (highest first), then by RAG score
                suggestions.sort(key=lambda x: (x['relevance_score'], x['rag_score']), reverse=True)
                
                # Check if cleaned query matches any suggestion's filename/product name
                # If so, boost those suggestions even if relevance is low
                cleaned_query_lower = cleaned_query.lower() if cleaned_query else query.lower()
                cleaned_query_terms = [t for t in cleaned_query_lower.split() if len(t) > 2] or [cleaned_query_lower]
                
                for sug in suggestions:
                    filename_lower = sug.get('filename', '').lower()
                    # If query terms match filename, boost relevance
                    if any(term in filename_lower for term in cleaned_query_terms):
                        if sug['relevance_score'] < 0.2:
                            logger.info(f"Boosting suggestion '{sug.get('filename')}' - query terms match filename")
                            sug['relevance_score'] = max(0.2, sug['relevance_score'] + 0.1)
                
                # Re-sort after boosting
                suggestions.sort(key=lambda x: (x['relevance_score'], x['rag_score']), reverse=True)
                
                # Show top suggestions (at least top 3 if available, or all if less than 3)
                # Even if relevance is below threshold, show if query terms match filename
                max_suggestions = min(limit, max(3, len(suggestions)))
                top_suggestions = suggestions[:max_suggestions]
                
                for suggestion in top_suggestions:
                    result = suggestion["result"]
                    youtube_links = suggestion["youtube_links"]
                    relevance_score = suggestion["relevance_score"]
                    rag_score = suggestion["rag_score"]
                    
                    original_content = result.get("content", "")
                    metadata = result.get("metadata", {})
                    filename = metadata.get("filename", "Unknown")
                    
                    for link_info in youtube_links:
                        video_id = link_info["video_id"]
                        
                        if video_id in seen_video_ids:
                            continue
                        seen_video_ids.add(video_id)
                        
                        # Extract title
                        title = self._extract_product_from_content(original_content, filename)
                        if not title:
                            title = self._extract_video_title(original_content, link_info["url"])
                        if not title:
                            title = filename.rsplit('.', 1)[0].replace('_', ' ')
                        
                        # Get description
                        url_pos = original_content.lower().find(link_info["url"].lower())
                        if url_pos > 0:
                            start = max(0, url_pos - 200)
                            end = min(len(original_content), url_pos + 200)
                            description = original_content[start:end].strip()
                        else:
                            description = original_content[:300].strip()
                        
                        if len(description) > 300:
                            description = description[:300] + "..."
                        
                        video_info = {
                            "video_id": video_id,
                            "url": link_info["url"],
                            "embed_url": link_info["embed_url"],
                            "title": title,
                            "description": description,
                            "source_document": filename,
                            "relevance_score": relevance_score,
                            "is_suggestion": True  # Mark as suggestion
                        }
                        
                        videos.append(video_info)
                        logger.info(f"  💡 Added suggestion: {title} (relevance: {relevance_score:.3f})")
                        
                        if len(videos) >= limit:
                            break
                    
                    if len(videos) >= limit:
                        break
                
                # Sort by relevance score
                videos.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
                
                logger.info(f"Returning {len(videos)} suggested video(s) for query: '{query}'")
                for i, video in enumerate(videos, 1):
                    logger.info(f"  {i}. {video.get('title')} (relevance: {video.get('relevance_score', 0):.3f})")
                
                return {
                    "status": "success",
                    "videos": videos,
                    "message": f"Perhaps you are referring to these related demo videos:",
                    "is_suggestion": True
                }
            
            if not videos:
                return {
                    "status": "success",
                    "videos": [],
                    "message": f"No demo videos found for '{cleaned_query or query}'."
                }
            
            # Sort by relevance score (highest first)
            videos.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
            
            logger.info(f"Returning {len(videos)} precisely matched video(s) for query: '{query}'")
            for i, video in enumerate(videos, 1):
                logger.info(f"  {i}. {video.get('title')} (RAG score: {video.get('relevance_score', 0):.3f})")
            
            return {
                "status": "success",
                "videos": videos,
                "message": f"Found {len(videos)} demo video(s) matching '{query}'"
            }
            
        except Exception as e:
            logger.error(f"Error searching for demo videos: {e}", exc_info=True)
            return {
                "status": "error",
                "videos": [],
                "message": f"Error searching for demo videos: {str(e)}"
            }

# Global instance
demo_video_service = DemoVideoService()

