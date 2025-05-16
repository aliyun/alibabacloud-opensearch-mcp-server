from enum import Enum


class Mode(Enum):
    LOCAL = "local"
    URL = "url"


class FileType(Enum):
    PDF = "pdf"
    DOC = "doc"
    DOCX = "docx"
    TXT = "txt"
    HTML = "html"


class DocumentSplitType(Enum):
    TEXT = "text"
    MARKDOWN = "markdown"
    HTML = "html"


class InputType(Enum):
    QUERY = "query"
    DOCUMENT = "document"


class TextEmbeddingModel(Enum):
    OPS_TEXT_EMBEDDING_001 = "ops-text-embedding-001"
    OPS_TEXT_EMBEDDING_ZH_001 = "ops-text-embedding-zh-001"
    OPS_TEXT_EMBEDDING_EN_001 = "ops-text-embedding-en-001"
    OPS_TEXT_EMBEDDING_002 = "ops-text-embedding-002"
