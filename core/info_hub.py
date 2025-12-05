import hashlib
import bisect
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import List, Dict, Set, Optional

_info_hub = {}

def get_info_hub(group_id:str):
    global _info_hub
    if group_id not in _info_hub:
        _info_hub[group_id] = InformationHub(group_id)
    return _info_hub[group_id]

@dataclass
class Information:
    title: str
    content: str
    id: int = 0
    deleted: bool = False


class InformationHub:
    def __init__(self, group_id:str):
        self.documents = []  # documents[doc_id-1] gives the document
        self.next_id = 1
        self.group_id = group_id
        self.group_prefix = abs(hash(group_id)) % 1000
        self.deleted_ids = set()  # Track IDs available for reuse

        # Inverted indexes for fast searching
        self.title_index = defaultdict(list)  # word -> list of (doc_id, position)
        self.content_index = defaultdict(list)  # word -> list of (doc_id, position)

        # For tracking document words
        self.doc_title_words = defaultdict(set)  # doc_id -> set of words in title
        self.doc_content_words = defaultdict(set)  # doc_id -> set of words in content

    def _tokenize(self, text: str) -> List[str]:
        """Convert text to lowercase tokens - O(k)"""
        words = re.findall(r'\b\w+\b', text.lower())
        return words

    def _allocate_id(self) -> int:
        """Allocate a document ID, ensuring it is unique within the group"""
        if self.deleted_ids:
            return self.deleted_ids.pop()
        else:
            id_val = self.next_id
            self.next_id += 1
            if id_val > 999:
                raise OverflowError("Quá nhiều tài liệu trong nhóm.")
            return self.group_prefix * 1000 + id_val

    def add_document(self, title: str, content: str) -> int:
        """Add a document and return its ID - O(k log n) where k is number of words"""
        doc_id = self._allocate_id()

        # Ensure documents list is large enough
        while len(self.documents) < doc_id:
            self.documents.append(None)

        doc = Information(title, content, doc_id)
        self.documents[doc_id - 1] = doc

        # Index title words
        title_words = self._tokenize(title)
        for pos, word in enumerate(title_words):
            bisect.insort(self.title_index[word], (doc_id, pos))
            self.doc_title_words[doc_id].add(word)

        # Index content words
        content_words = self._tokenize(content)
        for pos, word in enumerate(content_words):
            bisect.insort(self.content_index[word], (doc_id, pos))
            self.doc_content_words[doc_id].add(word)

        return doc_id

    def delete_document(self, doc_id: int) -> bool:
        """Delete a document by ID - O(k log n) where k is number of words"""
        if doc_id < 1 or doc_id > len(self.documents) or self.documents[doc_id - 1] is None:
            return False

        doc = self.documents[doc_id - 1]
        if doc.deleted:
            return False

        # Mark as deleted
        doc.deleted = True

        # Remove from indexes - O(k log n) operation
        for word in self.doc_title_words[doc_id]:
            # Binary search to find and remove entries for this doc_id
            entries = self.title_index[word]
            # Find all positions to remove
            to_remove = []
            left = bisect.bisect_left(entries, (doc_id, 0))
            right = bisect.bisect_right(entries, (doc_id, float('inf')))
            to_remove.extend(range(left, right))

            # Remove from end to avoid index shifting issues
            for i in reversed(to_remove):
                del entries[i]

            # Clean up empty word entries
            if not entries:
                del self.title_index[word]

        for word in self.doc_content_words[doc_id]:
            # Same process for content index
            entries = self.content_index[word]
            to_remove = []
            left = bisect.bisect_left(entries, (doc_id, 0))
            right = bisect.bisect_right(entries, (doc_id, float('inf')))
            to_remove.extend(range(left, right))

            for i in reversed(to_remove):
                del entries[i]

            if not entries:
                del self.content_index[word]

        # Clear word sets
        del self.doc_title_words[doc_id]
        del self.doc_content_words[doc_id]

        # Add to reusable IDs
        self.deleted_ids.add(doc_id)

        return True

    def _filter_deleted(self, doc_ids: Set[int]) -> List[int]:
        """Filter out deleted documents - O(m) where m is number of doc_ids"""
        return [doc_id for doc_id in doc_ids
                if doc_id <= len(self.documents) and
                self.documents[doc_id - 1] is not None and
                not self.documents[doc_id - 1].deleted]

    def search(self, keyword: str) -> List[Information]:
        """Search by keyword - O(log n) for lookup + O(m) for filtering"""

        # ⚠️ BƯỚC QUAN TRỌNG: Tokenize keyword trước khi tìm kiếm
        keywords = self._tokenize(keyword)
        if not keywords:
            return []

        search_term = keywords[0]  # Chỉ lấy từ đầu tiên cho tìm kiếm đơn giản

        title_matches = set()
        if search_term in self.title_index:
            title_matches.update(doc_id for doc_id, _ in self.title_index[search_term])

        content_matches = set()
        if search_term in self.content_index:
            content_matches.update(doc_id for doc_id, _ in self.content_index[search_term])

        content_only_matches = content_matches - title_matches

        # Filter out deleted documents
        title_matches = self._filter_deleted(title_matches)
        content_only_matches = self._filter_deleted(content_only_matches)

        # Build results
        results = []
        # Ưu tiên kết quả khớp tiêu đề
        for doc_id in title_matches:
            results.append(self.documents[doc_id - 1])
        for doc_id in content_only_matches:
            results.append(self.documents[doc_id - 1])

        return results

    """def search_multiple(self, keywords: List[str]) -> List[Information]:
        #Search for multiple keywords with AND logic - O(m * log n)
        if not keywords:
            return []

        candidate_docs = set(range(1, self.next_id))

        for keyword in keywords:
            keyword = keyword.lower()
            matching_docs = set()

            if keyword in self.title_index:
                matching_docs.update(doc_id for doc_id, _ in self.title_index[keyword])
            if keyword in self.content_index:
                matching_docs.update(doc_id for doc_id, _ in self.content_index[keyword])

            candidate_docs &= matching_docs
            if not candidate_docs:
                break

        # Filter deleted and score
        candidate_docs = self._filter_deleted(candidate_docs)
        scored_docs = []

        for doc_id in candidate_docs:
            title_match_count = sum(1 for kw in keywords
                                    if kw in self.doc_title_words.get(doc_id, set()))
            content_match_count = sum(1 for kw in keywords
                                      if kw in self.doc_content_words.get(doc_id, set()))
            score = title_match_count * 100 + content_match_count
            scored_docs.append((score, doc_id))

        scored_docs.sort(reverse=True)
        return [self.documents[doc_id - 1] for _, doc_id in scored_docs]"""

    def update_document(self, doc_id: int, title: str = None, content: str = None) -> bool:
        """Update a document - O(k log n)"""
        if doc_id < 1 or doc_id > len(self.documents) or self.documents[doc_id - 1] is None:
            return False

        doc = self.documents[doc_id - 1]
        if doc.deleted:
            return False

        # Delete old indexes
        for word in self.doc_title_words[doc_id]:
            entries = self.title_index[word]
            to_remove = []
            left = bisect.bisect_left(entries, (doc_id, 0))
            right = bisect.bisect_right(entries, (doc_id, float('inf')))
            to_remove.extend(range(left, right))
            for i in reversed(to_remove):
                del entries[i]
            if not entries:
                del self.title_index[word]

        for word in self.doc_content_words[doc_id]:
            entries = self.content_index[word]
            to_remove = []
            left = bisect.bisect_left(entries, (doc_id, 0))
            right = bisect.bisect_right(entries, (doc_id, float('inf')))
            to_remove.extend(range(left, right))
            for i in reversed(to_remove):
                del entries[i]
            if not entries:
                del self.content_index[word]

        # Clear old word sets
        self.doc_title_words[doc_id] = set()
        self.doc_content_words[doc_id] = set()

        # Update document
        if title is not None:
            doc.title = title
        if content is not None:
            doc.content = content

        # Re-index
        title_words = self._tokenize(doc.title)
        for pos, word in enumerate(title_words):
            bisect.insort(self.title_index[word], (doc_id, pos))
            self.doc_title_words[doc_id].add(word)

        content_words = self._tokenize(doc.content)
        for pos, word in enumerate(content_words):
            bisect.insort(self.content_index[word], (doc_id, pos))
            self.doc_content_words[doc_id].add(word)

        return True

    def get_document(self, doc_id: int) -> Optional[Information]:
        """Get document by ID - O(1)"""
        if (doc_id < 1 or doc_id > len(self.documents) or
                self.documents[doc_id - 1] is None or
                self.documents[doc_id - 1].deleted):
            return None
        return self.documents[doc_id - 1]

    def get_stats(self) -> Dict:
        """Get statistics about the hub"""
        active_docs = [doc for doc in self.documents if doc is not None and not doc.deleted]
        return {
            "total_documents": len(active_docs),
            "deleted_documents": len(self.deleted_ids),
            "unique_title_words": len(self.title_index),
            "unique_content_words": len(self.content_index)
        }
