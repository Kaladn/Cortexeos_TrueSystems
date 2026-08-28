"""
Chat Logger Implementation (Append-Only XMLL)
==============================================

This module implements the Chat Logger for the Chat Citations system.

RULES:
- Append-only: Never edit, never delete
- Immutable: Once written, never changes
- One message = one line = one XML element
- Integrity: SHA-256 hash on every message
- Write authority: ChatLogger ONLY

Author: Manus AI
Date: January 2026
Status: IMPLEMENTATION PSEUDOCODE
"""

import hashlib
import os
from datetime import datetime
from typing import Literal, Optional
from xml.etree import ElementTree as ET
import xml.sax.saxutils as saxutils


# ============================================================================
# EXCEPTIONS
# ============================================================================

class ImmutabilityViolationError(Exception):
    """
    Raised when an attempt is made to modify an immutable chat log.
    This is a HARD FAILURE. System should exit.
    """
    pass


class IntegrityViolationError(Exception):
    """
    Raised when a message's integrity hash doesn't match.
    This indicates tampering or corruption.
    """
    pass


# ============================================================================
# INTEGRITY HASH CALCULATION
# ============================================================================

def calculate_integrity_hash(
    conversation_id: str,
    message_id: str,
    timestamp_utc: str,
    role: str,
    content: str
) -> str:
    """
    Calculate SHA-256 hash for integrity verification.
    
    The hash is calculated over a canonical representation of all fields
    in a fixed order.
    
    Args:
        conversation_id: Unique conversation identifier
        message_id: Unique message identifier within conversation
        timestamp_utc: ISO-8601 UTC timestamp
        role: One of 'user', 'assistant', 'system'
        content: The actual message text
    
    Returns:
        Hexadecimal SHA-256 hash string
    """
    canonical = (
        f"conversation_id={conversation_id}|"
        f"message_id={message_id}|"
        f"timestamp_utc={timestamp_utc}|"
        f"role={role}|"
        f"content={content}"
    )
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


def verify_integrity(
    conversation_id: str,
    message_id: str,
    timestamp_utc: str,
    role: str,
    content: str,
    stored_hash: str
) -> bool:
    """
    Verify that a message hasn't been tampered with.
    
    Args:
        conversation_id: Unique conversation identifier
        message_id: Unique message identifier
        timestamp_utc: ISO-8601 UTC timestamp
        role: Message role
        content: Message content
        stored_hash: The hash stored with the message
    
    Returns:
        True if integrity check passes
    
    Raises:
        IntegrityViolationError: If hash doesn't match
    """
    calculated_hash = calculate_integrity_hash(
        conversation_id, message_id, timestamp_utc, role, content
    )
    
    if stored_hash != calculated_hash:
        raise IntegrityViolationError(
            f"Message {message_id} failed integrity check. "
            f"Expected: {stored_hash}, Got: {calculated_hash}. "
            "This message has been corrupted or tampered with."
        )
    
    return True


# ============================================================================
# MESSAGE ID GENERATION
# ============================================================================

def generate_message_id(conversation_id: str, storage_dir: str = "chat_logs") -> str:
    """
    Generate monotonic sequential message IDs.
    
    Format: m_000001, m_000002, etc.
    
    Args:
        conversation_id: Conversation identifier
        storage_dir: Directory where chat logs are stored
    
    Returns:
        Next sequential message ID
    """
    file_path = os.path.join(storage_dir, f"conversation_{conversation_id}.xmll")
    
    # If file doesn't exist, this is the first message
    if not os.path.exists(file_path):
        return "m_000001"
    
    # Count existing lines
    with open(file_path, 'r', encoding='utf-8') as f:
        line_count = sum(1 for _ in f)
    
    next_id = line_count + 1
    return f"m_{next_id:06d}"


# ============================================================================
# MESSAGE EXISTENCE CHECK
# ============================================================================

def message_exists(
    conversation_id: str,
    message_id: str,
    storage_dir: str = "chat_logs"
) -> bool:
    """
    Check if a message ID already exists in a conversation.
    
    Args:
        conversation_id: Conversation identifier
        message_id: Message identifier to check
        storage_dir: Directory where chat logs are stored
    
    Returns:
        True if message exists, False otherwise
    """
    file_path = os.path.join(storage_dir, f"conversation_{conversation_id}.xmll")
    
    if not os.path.exists(file_path):
        return False
    
    # Scan file for message_id
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if f'message_id="{message_id}"' in line:
                return True
    
    return False


# ============================================================================
# XML LINE BUILDER
# ============================================================================

def build_message_xml(
    conversation_id: str,
    message_id: str,
    timestamp_utc: str,
    role: str,
    content: str,
    integrity_hash: str
) -> str:
    """
    Build a single-line XML element for a chat message.
    
    Args:
        conversation_id: Conversation identifier
        message_id: Message identifier
        timestamp_utc: ISO-8601 UTC timestamp
        role: Message role
        content: Message content
        integrity_hash: SHA-256 integrity hash
    
    Returns:
        Single-line XML string
    """
    # Wrap content in CDATA to handle special characters
    content_cdata = f"<![CDATA[{content}]]>"
    
    # Build XML line (single line, no newlines)
    xml_line = (
        f'<chat_message '
        f'conversation_id="{conversation_id}" '
        f'message_id="{message_id}" '
        f'timestamp_utc="{timestamp_utc}" '
        f'role="{role}" '
        f'integrity_sha256="{integrity_hash}">'
        f'<content>{content_cdata}</content>'
        f'</chat_message>'
    )
    
    return xml_line


# ============================================================================
# APPEND-ONLY FILE OPERATIONS
# ============================================================================

def append_message_to_file(
    conversation_id: str,
    message_xml: str,
    storage_dir: str = "chat_logs"
) -> None:
    """
    Append a single message to the conversation log file.
    
    CRITICAL: This function ONLY appends. It never overwrites.
    
    Args:
        conversation_id: Conversation identifier
        message_xml: Complete XML line to append
        storage_dir: Directory where chat logs are stored
    """
    # Ensure storage directory exists
    os.makedirs(storage_dir, exist_ok=True)
    
    file_path = os.path.join(storage_dir, f"conversation_{conversation_id}.xmll")
    
    # CRITICAL: Append mode only ('a')
    # Never use 'w' (overwrite) or 'r+' (read-write)
    with open(file_path, 'a', encoding='utf-8') as f:
        f.write(message_xml + '\n')


# ============================================================================
# CHAT LOGGER (WRITE AUTHORITY)
# ============================================================================

class ChatLogger:
    """
    The ONLY component allowed to write to chat logs.
    
    This is the write authority for the Chat Citations system.
    No other component, no LLM, no user interface can write directly.
    
    Responsibilities:
    - Log every message immediately
    - Generate message IDs
    - Calculate integrity hashes
    - Enforce immutability
    - Append-only file operations
    """
    
    def __init__(self, storage_dir: str = "chat_logs"):
        """
        Initialize the Chat Logger.
        
        Args:
            storage_dir: Directory where chat logs will be stored
        """
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
    
    def log_message(
        self,
        conversation_id: str,
        role: Literal["user", "assistant", "system"],
        content: str,
        message_id: Optional[str] = None
    ) -> str:
        """
        Log a single message to the conversation.
        
        This is the core write operation. All other log_* methods call this.
        
        Args:
            conversation_id: Conversation identifier
            role: Message role (user, assistant, or system)
            content: Message content
            message_id: Optional explicit message ID (auto-generated if None)
        
        Returns:
            The message_id that was logged
        
        Raises:
            ImmutabilityViolationError: If message_id already exists
        """
        # Generate message ID if not provided
        if message_id is None:
            message_id = generate_message_id(conversation_id, self.storage_dir)
        
        # Check for immutability violation
        if message_exists(conversation_id, message_id, self.storage_dir):
            raise ImmutabilityViolationError(
                f"Message {message_id} already exists in conversation {conversation_id}. "
                "Chat logs are immutable. This is a system integrity failure."
            )
        
        # Generate UTC timestamp
        timestamp_utc = datetime.utcnow().isoformat() + 'Z'
        
        # Calculate integrity hash
        integrity_hash = calculate_integrity_hash(
            conversation_id, message_id, timestamp_utc, role, content
        )
        
        # Build XML line
        message_xml = build_message_xml(
            conversation_id, message_id, timestamp_utc, role, content, integrity_hash
        )
        
        # Append to file (WRITE OPERATION)
        append_message_to_file(conversation_id, message_xml, self.storage_dir)
        
        return message_id
    
    def log_user_message(self, conversation_id: str, content: str) -> str:
        """
        Log a user message.
        
        Args:
            conversation_id: Conversation identifier
            content: User's message content
        
        Returns:
            The message_id that was logged
        """
        return self.log_message(conversation_id, "user", content)
    
    def log_assistant_message(self, conversation_id: str, content: str) -> str:
        """
        Log an assistant message.
        
        Args:
            conversation_id: Conversation identifier
            content: Assistant's message content
        
        Returns:
            The message_id that was logged
        """
        return self.log_message(conversation_id, "assistant", content)
    
    def log_system_message(self, conversation_id: str, content: str) -> str:
        """
        Log a system message.
        
        Args:
            conversation_id: Conversation identifier
            content: System message content
        
        Returns:
            The message_id that was logged
        """
        return self.log_message(conversation_id, "system", content)


# ============================================================================
# CHAT LOG READER (READ-ONLY ACCESS)
# ============================================================================

class ChatLogReader:
    """
    Read-only interface for accessing chat logs.
    
    This is what LLMs (like Qwen) use to read conversation history.
    
    CRITICAL: This class has ZERO write methods.
    It can only read and verify.
    """
    
    def __init__(self, storage_dir: str = "chat_logs"):
        """
        Initialize the Chat Log Reader.
        
        Args:
            storage_dir: Directory where chat logs are stored
        """
        self.storage_dir = storage_dir
    
    def parse_message_line(self, line: str) -> dict:
        """
        Parse a single XMLL line into a message dictionary.
        
        Args:
            line: Single line from XMLL file
        
        Returns:
            Dictionary with message fields
        """
        # Parse XML
        root = ET.fromstring(line.strip())
        
        # Extract attributes
        conversation_id = root.get('conversation_id')
        message_id = root.get('message_id')
        timestamp_utc = root.get('timestamp_utc')
        role = root.get('role')
        integrity_hash = root.get('integrity_sha256')
        
        # Extract content (handle CDATA)
        content_elem = root.find('content')
        content = content_elem.text if content_elem is not None else ""
        
        # Verify integrity
        verify_integrity(
            conversation_id, message_id, timestamp_utc, role, content, integrity_hash
        )
        
        return {
            'conversation_id': conversation_id,
            'message_id': message_id,
            'timestamp_utc': timestamp_utc,
            'role': role,
            'content': content,
            'integrity_sha256': integrity_hash
        }
    
    def get_conversation(self, conversation_id: str) -> list[dict]:
        """
        Retrieve all messages from a conversation.
        
        Args:
            conversation_id: Conversation identifier
        
        Returns:
            List of message dictionaries
        
        Raises:
            FileNotFoundError: If conversation doesn't exist
            IntegrityViolationError: If any message fails integrity check
        """
        file_path = os.path.join(self.storage_dir, f"conversation_{conversation_id}.xmll")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Conversation {conversation_id} not found")
        
        messages = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():  # Skip empty lines
                    message = self.parse_message_line(line)
                    messages.append(message)
        
        return messages
    
    def get_recent_messages(self, conversation_id: str, count: int) -> list[dict]:
        """
        Get the N most recent messages from a conversation.
        
        Args:
            conversation_id: Conversation identifier
            count: Number of recent messages to retrieve
        
        Returns:
            List of message dictionaries (most recent last)
        """
        all_messages = self.get_conversation(conversation_id)
        return all_messages[-count:] if len(all_messages) > count else all_messages
    
    def search_content(self, conversation_id: str, keyword: str) -> list[dict]:
        """
        Search for messages containing a keyword.
        
        Args:
            conversation_id: Conversation identifier
            keyword: Keyword to search for (case-insensitive)
        
        Returns:
            List of matching message dictionaries
        """
        all_messages = self.get_conversation(conversation_id)
        keyword_lower = keyword.lower()
        
        return [
            msg for msg in all_messages
            if keyword_lower in msg['content'].lower()
        ]
    
    def list_conversations(self) -> list[str]:
        """
        List all available conversation IDs.
        
        Returns:
            List of conversation IDs
        """
        if not os.path.exists(self.storage_dir):
            return []
        
        conversation_ids = []
        
        for filename in os.listdir(self.storage_dir):
            if filename.startswith("conversation_") and filename.endswith(".xmll"):
                # Extract conversation_id from filename
                conv_id = filename[len("conversation_"):-len(".xmll")]
                conversation_ids.append(conv_id)
        
        return sorted(conversation_ids)


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    # Initialize logger and reader
    logger = ChatLogger(storage_dir="chat_logs")
    reader = ChatLogReader(storage_dir="chat_logs")
    
    # Example conversation
    conv_id = "c_0001"
    
    # Log some messages
    logger.log_user_message(conv_id, "Hey bro. Append this correctly.")
    logger.log_assistant_message(conv_id, "Got it. Append-only, role-separated, no enrichment.")
    logger.log_user_message(conv_id, "Perfect. This is the brain.")
    
    # Read the conversation back
    messages = reader.get_conversation(conv_id)
    
    for msg in messages:
        print(f"[{msg['role']}] {msg['content']}")
    
    # Verify integrity (automatic in parse_message_line)
    print("\n✅ All messages verified. Integrity intact.")
    
    # Try to write duplicate (should fail)
    try:
        logger.log_message(conv_id, "user", "Duplicate test", message_id="m_000001")
    except ImmutabilityViolationError as e:
        print(f"\n❌ Immutability enforced: {e}")
