"""
SQLAlchemy ORM models for the Customer Support Agent.

WHY THIS FILE EXISTS:
---------------------
Instead of writing raw SQL like:
    INSERT INTO tickets (id, subject, status) VALUES ('abc', 'Help', 'new')

We define Python classes that MAP to database tables:
    ticket = Ticket(subject="Help", status="new")
    session.add(ticket)

This is called an ORM (Object-Relational Mapping):
    Python Object  ←→  Database Row
    Python Class   ←→  Database Table
    Python Attribute ←→  Database Column

Benefits:
1. Write Python instead of SQL (fewer bugs, IDE autocomplete)
2. Database-agnostic (works with PostgreSQL, SQLite, MySQL)
3. Automatic type conversion (Python uuid ↔ PostgreSQL UUID)
4. Relationships between tables are Python attributes

HOW THE TABLES RELATE:
----------------------
    Customer ──creates──→ Ticket ──has──→ Message
                            │
                            ├──assigned_to──→ Agent
                            ├──has──→ AgentAction (audit trail)
                            └──tagged_with──→ Tag

    KnowledgeArticle ──has──→ KBEmbedding (vector chunks for RAG)
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# =============================================================================
# Base Class — all models inherit from this
# =============================================================================

class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy models.
    
    Every model that inherits from Base automatically gets:
    - Table creation support (Base.metadata.create_all)
    - Alembic migration detection (compares models vs database)
    
    DeclarativeBase is SQLAlchemy 2.0's modern base class.
    The old way was: Base = declarative_base()  ← deprecated
    """
    pass


# =============================================================================
# CUSTOMERS — people who submit support tickets
# =============================================================================

class Customer(Base):
    """
    A customer who interacts with the support system.
    
    One customer can create many tickets (one-to-many relationship).
    
    Database table: customers
    """
    __tablename__ = "customers"
    
    # --- Primary Key ---
    # UUID is better than auto-increment integers because:
    # 1. Can be generated client-side (no DB round-trip)
    # 2. No sequential IDs to guess (security)
    # 3. Merging databases is easy (no ID collisions)
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    
    # --- Fields ---
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # JSONB = flexible schema-less data. Perfect for varying metadata:
    # {"company": "Acme", "plan": "pro", "phone": "+91-xxx"}
    metadata_: Mapped[dict] = mapped_column(
        "metadata",           # Column name in DB (metadata_ avoids Python keyword clash)
        JSONB,
        default=dict,
        server_default="{}",
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    
    # --- Relationships ---
    # This doesn't create a column! It tells SQLAlchemy:
    # "customer.tickets gives me all tickets for this customer"
    tickets: Mapped[list["Ticket"]] = relationship(
        back_populates="customer",
        lazy="selectin",     # Eager load tickets when accessing customer.tickets
    )
    
    def __repr__(self) -> str:
        return f"<Customer {self.email}>"


# =============================================================================
# AGENTS — AI agents and human support staff
# =============================================================================

class Agent(Base):
    """
    A support agent — either AI or human.
    
    The is_ai flag distinguishes between:
    - AI agents (automated ticket handling)
    - Human agents (escalation targets)
    
    Database table: agents
    """
    __tablename__ = "agents"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    role: Mapped[str] = mapped_column(String(100), nullable=False, default="support")
    
    # What this agent specializes in:
    # {"categories": ["billing", "technical"], "languages": ["en", "hi"]}
    skills: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    
    is_ai: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # --- Relationships ---
    assigned_tickets: Mapped[list["Ticket"]] = relationship(
        back_populates="assigned_agent",
    )
    actions: Mapped[list["AgentAction"]] = relationship(
        back_populates="agent",
    )
    
    def __repr__(self) -> str:
        agent_type = "AI" if self.is_ai else "Human"
        return f"<Agent {self.name} ({agent_type})>"


# =============================================================================
# TICKETS — the core entity of the support system
# =============================================================================

class Ticket(Base):
    """
    A support ticket created by a customer.
    
    This is the CENTRAL table — almost everything relates to it.
    
    Lifecycle: new → open → (pending_customer|pending_agent|escalated) → resolved → closed
    
    Database table: tickets
    """
    __tablename__ = "tickets"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    
    # --- Foreign Keys ---
    # Links this ticket to a customer (REQUIRED — every ticket has a customer)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id"),
        nullable=False,
    )
    
    # Links to the assigned agent (OPTIONAL — may not be assigned yet)
    assigned_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id"),
        nullable=True,
    )
    
    # --- Ticket Fields ---
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="new")
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # AI context: stores classification results, KB search results, etc.
    # {"intent": "password_reset", "sentiment": "frustrated", "confidence": 0.92}
    ai_context: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    
    # --- Timestamps ---
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),  # Auto-update on changes
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # --- Constraints ---
    # CHECK constraints ensure only valid values can be stored
    __table_args__ = (
        CheckConstraint(
            "status IN ('new', 'open', 'pending_customer', 'pending_agent', 'escalated', 'resolved', 'closed')",
            name="valid_status",
        ),
        CheckConstraint(
            "priority IN ('low', 'medium', 'high', 'urgent')",
            name="valid_priority",
        ),
        # Indexes speed up common queries
        Index("idx_tickets_status", "status"),
        Index("idx_tickets_customer", "customer_id"),
        Index("idx_tickets_created", "created_at"),
    )
    
    # --- Relationships ---
    customer: Mapped["Customer"] = relationship(back_populates="tickets")
    assigned_agent: Mapped["Agent | None"] = relationship(back_populates="assigned_tickets")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="ticket",
        order_by="Message.created_at",   # Messages ordered by time
    )
    actions: Mapped[list["AgentAction"]] = relationship(
        back_populates="ticket",
        order_by="AgentAction.created_at",
    )
    tags: Mapped[list["Tag"]] = relationship(
        secondary="ticket_tags",         # Many-to-many through junction table
        back_populates="tickets",
    )
    
    def __repr__(self) -> str:
        return f"<Ticket {self.id} [{self.status}] {self.subject[:50]}>"


# =============================================================================
# MESSAGES — conversation within a ticket
# =============================================================================

class Message(Base):
    """
    A single message in a ticket's conversation thread.
    
    sender_type indicates who sent it:
    - "customer" — the customer wrote this
    - "ai_agent" — our AI agent generated this
    - "human_agent" — a human support agent wrote this
    - "system" — automated system message (e.g., "ticket escalated")
    
    Database table: messages
    """
    __tablename__ = "messages"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tickets.id"),
        nullable=False,
    )
    
    # Who sent this message
    sender_type: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # The actual message text
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Extra data: {"channel": "web", "attachments": [...], "confidence": 0.95}
    metadata_: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
        server_default="{}",
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    
    __table_args__ = (
        CheckConstraint(
            "sender_type IN ('customer', 'ai_agent', 'human_agent', 'system')",
            name="valid_sender_type",
        ),
        Index("idx_messages_ticket", "ticket_id"),
    )
    
    # --- Relationships ---
    ticket: Mapped["Ticket"] = relationship(back_populates="messages")
    
    def __repr__(self) -> str:
        return f"<Message {self.sender_type}: {self.content[:40]}...>"


# =============================================================================
# AGENT_ACTIONS — audit trail for every action the AI takes
# =============================================================================

class AgentAction(Base):
    """
    Records every action taken by an agent on a ticket.
    
    This is the AUDIT TRAIL — crucial for transparency and debugging.
    
    Examples:
        action_type="classify_ticket"
        action_data={"intent": "billing", "category": "refund"}
        reasoning={"thought": "Customer mentions charge and refund...", "confidence": 0.9}
        outcome="success"
    
    Database table: agent_actions
    """
    __tablename__ = "agent_actions"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tickets.id"),
        nullable=False,
    )
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id"),
        nullable=True,
    )
    
    # What action was taken: classify, search_kb, generate_response, escalate, etc.
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Action input/output data
    action_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")
    
    # LLM's chain-of-thought reasoning (for transparency/debugging)
    reasoning: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    
    # Result: success, failure, escalated, timeout
    outcome: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    
    __table_args__ = (
        Index("idx_actions_ticket", "ticket_id"),
        Index("idx_actions_type", "action_type"),
    )
    
    # --- Relationships ---
    ticket: Mapped["Ticket"] = relationship(back_populates="actions")
    agent: Mapped["Agent"] = relationship(back_populates="actions")
    
    def __repr__(self) -> str:
        return f"<AgentAction {self.action_type} → {self.outcome}>"


# =============================================================================
# TAGS — categorization labels for tickets
# =============================================================================

class Tag(Base):
    """
    A label/tag that can be applied to tickets.
    
    Tags enable filtering and categorization:
    - "billing", "technical", "urgent", "vip-customer"
    
    Uses a many-to-many relationship through the ticket_tags junction table.
    
    Database table: tags
    """
    __tablename__ = "tags"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    __table_args__ = (
        UniqueConstraint("name", "category", name="unique_tag_name_category"),
    )
    
    # --- Relationships ---
    tickets: Mapped[list["Ticket"]] = relationship(
        secondary="ticket_tags",
        back_populates="tags",
    )
    
    def __repr__(self) -> str:
        return f"<Tag {self.name}>"


# =============================================================================
# TICKET_TAGS — junction table for many-to-many (Ticket ↔ Tag)
# =============================================================================

# This is a "junction table" (also called association/bridge table).
# It exists because one ticket can have many tags, and one tag can be
# on many tickets. Neither side "owns" the relationship.
#
# We use SQLAlchemy's Table construct (not a class) because this table
# has no extra columns — just two foreign keys.

from sqlalchemy import Table

ticket_tags = Table(
    "ticket_tags",
    Base.metadata,
    Column("ticket_id", UUID(as_uuid=True), ForeignKey("tickets.id"), primary_key=True),
    Column("tag_id", UUID(as_uuid=True), ForeignKey("tags.id"), primary_key=True),
)


# =============================================================================
# KNOWLEDGE_ARTICLES — KB articles for RAG search
# =============================================================================

class KnowledgeArticle(Base):
    """
    A knowledge base article used for RAG (Retrieval Augmented Generation).
    
    When a customer asks "How do I reset my password?", the AI searches
    these articles to find the relevant guide, then uses it to craft
    an accurate response.
    
    Database table: knowledge_articles
    """
    __tablename__ = "knowledge_articles"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    # Flexible metadata: {"author": "...", "version": 2, "tags": [...]}
    metadata_: Mapped[dict] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
        server_default="{}",
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    
    # --- Relationships ---
    embeddings: Mapped[list["KBEmbedding"]] = relationship(
        back_populates="article",
        cascade="all, delete-orphan",   # Delete embeddings when article is deleted
    )
    
    def __repr__(self) -> str:
        return f"<KnowledgeArticle {self.title[:50]}>"


# =============================================================================
# KB_EMBEDDINGS — vector chunks for similarity search
# =============================================================================

class KBEmbedding(Base):
    """
    A vector embedding chunk from a knowledge article.
    
    Long articles are split into chunks, each chunk is converted to a
    vector (list of numbers) using sentence-transformers. These vectors
    are stored here and searched using pgvector for similarity.
    
    HOW RAG WORKS:
        1. Article "Password Reset Guide" is split into 5 chunks
        2. Each chunk → sentence-transformers → 384-dim vector
        3. Vectors stored in this table
        4. When customer asks about passwords:
           - Their question → vector
           - pgvector finds most similar chunk vectors
           - Original text from those chunks fed to LLM as context
    
    Database table: kb_embeddings
    """
    __tablename__ = "kb_embeddings"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    
    article_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_articles.id"),
        nullable=False,
    )
    
    # The original text of this chunk
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Position of this chunk within the article (0, 1, 2, ...)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # The vector embedding — stored as a pgvector 'vector' type
    # We'll handle the actual vector column via Alembic migration
    # since it requires the pgvector extension
    # embedding: mapped_column(Vector(384))  ← Added in migration
    
    __table_args__ = (
        Index("idx_embeddings_article", "article_id"),
    )
    
    # --- Relationships ---
    article: Mapped["KnowledgeArticle"] = relationship(back_populates="embeddings")
    
    def __repr__(self) -> str:
        return f"<KBEmbedding article={self.article_id} chunk={self.chunk_index}>"
