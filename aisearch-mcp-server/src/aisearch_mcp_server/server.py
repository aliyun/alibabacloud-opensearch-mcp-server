import base64
import os
import time

from dotenv import load_dotenv
from typing import Dict, List, Any, Optional
from pydantic import Field


from alibabacloud_searchplat20240529.models import CreateDocumentAnalyzeTaskRequestDocument, \
    CreateDocumentAnalyzeTaskRequestOutput, CreateDocumentAnalyzeTaskRequest, CreateDocumentAnalyzeTaskResponse, \
    GetDocumentAnalyzeTaskStatusRequest, GetDocumentAnalyzeTaskStatusResponse, CreateImageAnalyzeTaskRequestDocument, \
    CreateImageAnalyzeTaskRequest, CreateImageAnalyzeTaskResponse, GetImageAnalyzeTaskStatusRequest, \
    GetImageAnalyzeTaskStatusResponse, GetDocumentSplitRequest, GetDocumentSplitRequestDocument, \
    GetDocumentSplitRequestStrategy, GetTextEmbeddingRequest, GetTextSparseEmbeddingRequest, GetDocumentRankRequest, \
    GetWebSearchRequest, GetQueryAnalysisRequestFunctions, GetQueryAnalysisRequest

from mcp.server.fastmcp import FastMCP
from alibabacloud_tea_openapi.models import Config
from alibabacloud_searchplat20240529.client import Client

from aisearch_mcp_server.util import *
from aisearch_mcp_server.prompt import *

load_dotenv()


def get_aisearch_client():
    if not all([os.getenv("AISEARCH_API_KEY"), os.getenv("AISEARCH_ENDPOINT")]):
        raise ValueError("Missing required aisearch configuration")
    config = Config(
        bearer_token=os.getenv("AISEARCH_API_KEY"),
        endpoint=os.getenv("AISEARCH_ENDPOINT"),
        protocol="http"
    )
    return Client(config=config)


client = get_aisearch_client()
mcp = FastMCP("aisearch_mcp_server")


@mcp.tool(
    name="document_analyze",
    description=DOCUMENT_ANALYZE_DESC
)
async def document_analyze(
        file_path: str = Field(..., description="用户需要提供待处理文件的地址或路径"),
        file_type: str = Field(..., description="待处理文件类型，支持以下格式：`pdf`, `doc`, `docx`, `html`, `txt`"),
        mode: str = Field(..., description="文件来源模式，支持以下选项：`url`, `local`")
):
    if mode == Mode.URL.value:
        document = CreateDocumentAnalyzeTaskRequestDocument(
            url=file_path,
            file_type=file_type
        )
    elif mode == Mode.LOCAL.value:
        document = CreateDocumentAnalyzeTaskRequestDocument(
            content=base64.b64encode(open(file_path, 'rb').read()).decode(),
            file_name=os.path.basename(file_path)
        )
    else:
        raise ValueError("Invalid mode")

    output = CreateDocumentAnalyzeTaskRequestOutput(image_storage="url")
    request = CreateDocumentAnalyzeTaskRequest(document=document, output=output)
    response: CreateDocumentAnalyzeTaskResponse = client.create_document_analyze_task(
        "default", "ops-document-analyze-001", request)
    task_id = response.body.result.task_id
    request = GetDocumentAnalyzeTaskStatusRequest(task_id=task_id)
    while True:
        response: GetDocumentAnalyzeTaskStatusResponse = client.get_document_analyze_task_status(
            "default", "ops-document-analyze-001", request)
        status = response.body.result.status
        if status == "PENDING":
            time.sleep(5)
        elif status == "SUCCESS":
            data = response.body.result.data
            # usage = response.body.usage
            return data.content
        else:
            raise RuntimeError(f"{response.body.result.error}")


@mcp.tool(
    name="image_analyze",
    description=IMAGE_ANALYZE_DESC
)
async def image_analyze(
        file_path: str = Field(..., description="待处理图片的地址或路径"),
        mode: str = Field(..., description="文件来源模式，支持以下选项：`url`, `local`")
):
    if mode == Mode.URL.value:
        document = CreateImageAnalyzeTaskRequestDocument(
            url=file_path
        )
    elif mode == Mode.LOCAL.value:
        document = CreateImageAnalyzeTaskRequestDocument(
            content=base64.b64encode(open(file_path, 'rb').read()).decode(),
            file_name=os.path.basename(file_path)
        )
    else:
        raise ValueError("Invalid mode")

    request = CreateImageAnalyzeTaskRequest(document=document)
    response: CreateImageAnalyzeTaskResponse = client.create_image_analyze_task(
        "default", "ops-image-analyze-vlm-001", request)
    task_id = response.body.result.task_id
    request = GetImageAnalyzeTaskStatusRequest(task_id=task_id)
    while True:
        response: GetImageAnalyzeTaskStatusResponse = client.get_image_analyze_task_status(
            "default", "ops-image-analyze-vlm-001", request)
        status = response.body.result.status
        if status == "PENDING":
            time.sleep(5)
        elif status == "SUCCESS":
            data = response.body.result.data
            # usage = response.body.usage
            return data.content
        else:
            raise RuntimeError(f"{response.body.result.error}")


@mcp.tool(
    name="document_split",
    description=DOCUMENT_SPLIT_DESC
)
async def document_split(
        content: str = Field(..., description="待切分的原始文档内容"),
        content_type: str = Field(default="text", description="文档内容类型，支持：`text`、`html`、`markdown`"),
        need_sentence: bool = Field(default=False, description="是否需要按句子粒度切分"),
        max_chunk_size: int = Field(default=300, description="单个切片最大长度")
):
    try:
        request = GetDocumentSplitRequest(
            document=GetDocumentSplitRequestDocument(
                content=content,
                content_type=content_type
            ),
            strategy=GetDocumentSplitRequestStrategy(
                need_sentence=need_sentence,
                max_chunk_size=max_chunk_size
            )
        )
        response = client.get_document_split("default", "ops-document-split-001", request)
        doc_list = []
        for chunk in response.body.result.chunks:
            doc_list.append({"id": chunk.meta.get("id"), "content": chunk.content})
        for rich_text in response.body.result.rich_texts:
            if rich_text.meta.get("type") != "image":
                doc_list.append({"id": rich_text.meta.get("id"), "content": rich_text.content})
        return doc_list
    except Exception as e:
        raise RuntimeError(f"{e}")


@mcp.tool(
    name="text_embedding",
    description=TEXT_EMBEDDING_DESC
)
async def text_embedding(
        text_list: List[str] = Field(..., description="待向量化的文本列表，每次最多支持 32 条，最少 1 条。若超过上限需分批调用。"),
        input_type: str = Field(default="query", description="输入文本类型，可选值：`query`或`document`"),
        embedding_model: str = Field(default="ops-text-embedding-002",
                                     description="文本向量化模型，可选值：`ops-text-embedding-001`、`ops-text-embedding-zh-001`、`ops-text-embedding-en-001`、`ops-text-embedding-002`")
):
    try:
        SUPPORTED_EMBEDDING_MODELS = {
            "ops-text-embedding-001",
            "ops-text-embedding-zh-001",
            "ops-text-embedding-en-001",
            "ops-text-embedding-002"
        }
        if embedding_model not in SUPPORTED_EMBEDDING_MODELS:
            raise ValueError(f"Invalid embedding_model: {embedding_model}. "
                             f"Supported models are: {', '.join(SUPPORTED_EMBEDDING_MODELS)}")

        request = GetTextEmbeddingRequest(
            input=text_list,
            input_type=input_type,
        )
        response = client.get_text_embedding("default", embedding_model, request)
        return response.body.result.embeddings
    except Exception as e:
        raise RuntimeError(f"{e}")


@mcp.tool(
    name="text_sparse_embedding",
    description=TEXT_SPARSE_EMBEDDING_DESC
)
async def text_sparse_embedding(
        text_list: List[str] = Field(..., description="待稀疏向量化的文本列表，每次最多支持 32 条，最少 1 条。若超过上限需分批调用。"),
        input_type: str = Field(default="query", description="输入文本类型，可选值：`query`或`document`"),
):
    try:
        request = GetTextSparseEmbeddingRequest(
            input=text_list,
            input_type=input_type,
        )
        response = client.get_text_sparse_embedding("default", "ops-text-sparse-embedding-001", request)
        return response.body.result.sparse_embeddings
    except Exception as e:
        raise RuntimeError(f"{e}")


@mcp.tool(
    name="rerank",
    description=RERANK_DESC
)
async def rerank(
        query: str = Field(..., description="用户输入的查询语句或问题"),
        docs: List[str] = Field(..., description="待排序的文档列表，将根据与查询的相关性重新排序"),
        top_k: int = Field(default=5, description="返回的相关性最高的文档数量")
):
    try:
        request = GetDocumentRankRequest(
            query=query,
            docs=docs
        )
        response = client.get_document_rank("default", "ops-bge-reranker-larger", request)
        scores = response.body.result.scores
        rerank_results = [(docs[item.index], item.score) for item in scores[:top_k]]
        return rerank_results
    except Exception as e:
        raise RuntimeError(f"{e}")


@mcp.tool(
    name="web_search",
    description=WEB_SEARCH_DESC
)
async def web_search(
        query: str = Field(..., description="用户输入的查询语句或问题")
):
    try:
        request = GetWebSearchRequest(
            query=query
        )
        response = client.get_web_search("default", "ops-web-search-001", request)
        return response.body.result.search_result
    except Exception as e:
        raise RuntimeError(f"{e}")


@mcp.tool(
    name="query_analyze",
    description=QUERY_ANALYZE_DESC
)
async def query_analyze(
        query: str = Field(..., description="用户输入的查询语句或问题")
):
    try:
        functions = [
            GetQueryAnalysisRequestFunctions(name="intent", parameters={"enable": True}),
            GetQueryAnalysisRequestFunctions(name="similar_query", parameters={"enable": True}),
            GetQueryAnalysisRequestFunctions(name="nl2sql",
                                             parameters={"enable": False, "config_name": "[object Object]"}),
        ]
        request = GetQueryAnalysisRequest(
            query=query,
            functions=functions
        )
        response = client.get_query_analysis("default", "ops-query-analyze-001", request)
        result = {
            "original_query": response.body.result.query,
            "intent": response.body.result.intent,
            "similar_query": response.body.result.queries,
        }
        return result
    except Exception as e:
        raise RuntimeError(f"{e}")

if __name__ == "__main__":
    mcp.run()
