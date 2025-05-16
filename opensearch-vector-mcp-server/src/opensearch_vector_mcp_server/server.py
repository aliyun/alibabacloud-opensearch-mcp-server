import json
import os
from operator import attrgetter

from alibabacloud_searchplat20240529.models import GetTextEmbeddingRequest, GetTextSparseEmbeddingRequest
from dotenv import load_dotenv

from alibabacloud_ha3engine_vector.models import QueryRequest, MultiQueryRequest, SparseData, TextQuery, SearchRequest
from alibabacloud_ha3engine_vector.models import FetchRequest
from alibabacloud_ha3engine_vector.models import Config
from alibabacloud_ha3engine_vector.client import Client

from alibabacloud_tea_openapi.models import Config as AIsearchConfig
from alibabacloud_searchplat20240529.client import Client as AIsearchClient

from mcp.server.fastmcp import FastMCP

from typing import Dict, List, Any, Optional, Union
from pydantic import Field

load_dotenv()


def get_vector_config():
    """Get vector configuration from environment variables."""
    vector_config = {
        "endpoint": os.getenv("OPENSEARCH_VECTOR_ENDPOINT", "http://localhost:8000"),
        "user_name": os.getenv("OPENSEARCH_VECTOR_USERNAME", ""),
        "user_password": os.getenv("OPENSEARCH_VECTOR_PASSWORD", ""),
        "instance_id": os.getenv("OPENSEARCH_VECTOR_INSTANCE_ID", ""),
        # "table_name": os.getenv("OPENSEARCH_VECTOR_VECTOR_NAME", ""),
        "index_name": os.getenv("OPENSEARCH_VECTOR_INDEX_NAME", "embedding"),
        "application_name": f"opensearch-vector-mcp-server"
    }
    if not all([vector_config["endpoint"], vector_config["user_name"], vector_config["user_password"],
                vector_config["instance_id"]]):
        raise ValueError("Missing required opensearch vector configuration")
    return vector_config


def get_vector_client():
    vector_config = get_vector_config()
    config = Config(
        # API域名，可在实例详情页>API入口 查看
        endpoint=vector_config["endpoint"],
        # 用户名，可在实例详情页>API入口 查看
        access_user_name=vector_config["user_name"],
        # 密码，可在实例详情页>API入口 修改
        access_pass_word=vector_config["user_password"]
    )
    return Client(config)


config = get_vector_config()
client = get_vector_client()


def get_aisearch_client():
    if not all([os.getenv("AISEARCH_API_KEY"), os.getenv("AISEARCH_ENDPOINT")]):
        return None
    config = AIsearchConfig(
        bearer_token=os.getenv("AISEARCH_API_KEY"),
        endpoint=os.getenv("AISEARCH_ENDPOINT"),
        protocol="http"
    )
    return AIsearchClient(config=config)


aisearch_client = get_aisearch_client()

mcp = FastMCP("opensearch-vector-mcp-server")


@mcp.tool(
    name="simple_search",
    description="Perform a similarity search based on either a text query or a vector. If the input is text, it will be converted into a vector using the specified embedding model."
)
async def simple_search(
        table_name: str = Field(..., description="The name of the target table in OpenSearch Vector."),
        query: Union[str, List[float]] = Field(..., description="Search query, can be either a text string or a list of floats representing a vector."),
        embedding_model: str = Field(default="ops-text-embedding-002", description="Embedding model for text queries. Supported: `ops-text-embedding-001`、`ops-text-embedding-zh-001`、`ops-text-embedding-en-001`、`ops-text-embedding-002`"),
        namespace: Optional[str] = Field(default=None, description="Namespace for filtering results."),
        filter: Optional[str] = Field(default=None, description="Additional filtering criteria."),
        need_sparse_vector: bool = Field(default=False, description="Whether to include sparse vector data in the search.")
):
    """
    :param table_name: str
    :param query: Union[str, List[float]]
    :param embedding_model: str
    :param namespace: Optional[str]
    :param filter: Optional[str]
    :param need_sparse_vector: bool
    :return: SearchResult
    """
    try:
        if isinstance(query, str):
            if aisearch_client is None:
                raise ValueError("AiSearch client is not configured.")
            dense_request = GetTextEmbeddingRequest(
                input=[query],
                input_type="query",
            )

            SUPPORTED_EMBEDDING_MODELS = {
                "ops-text-embedding-001",
                "ops-text-embedding-zh-001",
                "ops-text-embedding-en-001",
                "ops-text-embedding-002"
            }
            if embedding_model not in SUPPORTED_EMBEDDING_MODELS:
                raise ValueError(f"Invalid embedding_model: {embedding_model}. "
                                 f"Supported models are: {', '.join(SUPPORTED_EMBEDDING_MODELS)}")

            response = aisearch_client.get_text_embedding("default", embedding_model, dense_request)
            vector = response.body.result.embeddings[0].embedding
            if need_sparse_vector is False:
                request = QueryRequest(table_name=table_name,
                                       vector=vector,
                                       include_vector=True,
                                       namespace=namespace,
                                       filter=filter,
                                       top_k=10,
                                       order="DESC",
                                       output_fields=["content"])
            else:
                sparse_request = GetTextSparseEmbeddingRequest(
                    input=[query],
                    input_type="query",
                )
                sparse_response = aisearch_client.get_text_sparse_embedding("default", "ops-text-sparse-embedding-001",
                                                                            sparse_request)
                sparse_embeddings = sparse_response.body.result.sparse_embeddings[0].embedding
                sorted_sparse_embedding_result = sorted(sparse_embeddings, key=attrgetter("token_id"))
                sparse_ids = [sparse_embedding.token_id for sparse_embedding in sorted_sparse_embedding_result]
                sparse_values = [sparse_embedding.weight for sparse_embedding in sorted_sparse_embedding_result]

                index_name = config["index_name"]
                sparse_data = SparseData(indices=sparse_ids, values=sparse_values)
                request = QueryRequest(table_name=table_name,
                                       index_name=index_name,
                                       vector=vector,
                                       sparse_data=sparse_data,
                                       include_vector=True,
                                       top_k=10,
                                       order="DESC",
                                       output_fields=["content"])
        elif isinstance(query, list):
            request = QueryRequest(table_name=table_name,
                                   vector=query,
                                   include_vector=True,
                                   namespace=namespace,
                                   filter=filter,
                                   top_k=10,
                                   order="DESC",
                                   output_fields=["content"])
        else:
            raise ValueError("query must be a string or a list of floats")
        response = client.query(request)
        json_body = json.loads(response.body)
        if len(json_body.get("errorMsg", '')) > 0:
            raise Exception(f"{json_body['errorMsg']}")
        search_result = []
        for item in json_body["result"]:
            search_result.append({
                "score": item["score"],
                "doc": item["fields"]["content"].encode('utf-8').decode('utf-8'),
            })
        return json.dumps(search_result, ensure_ascii=False)
    except Exception as e:
        raise Exception(f"{str(e)}") from e


@mcp.tool(
    name="query_by_ids",
    description="Perform a simple search based on key ids."
)
async def query_by_ids(
        table_name: str = Field(..., description="The name of the target table in OpenSearch Vector."),
        ids: List[str] = Field(..., description="List of ids to query")
):
    """
    :param table_name: str
    :param ids: List[str]
    :return: SearchResult
    """
    try:
        request = FetchRequest(table_name=table_name,
                               ids=ids)
        result = client.fetch(request)
        json_body = json.loads(result.body)
        if len(json_body.get("errorMsg", '')) > 0:
            raise Exception(f"{json_body['errorMsg']}")
        return json_body
    except Exception as e:
        raise Exception(f"{str(e)}") from e


@mcp.tool(
    name="inference_query",
    description="Perform a simple search based on text after configuring EmbeddingModel in OpenSearch Console."
)
async def inference_query(
        table_name: str = Field(..., description="The name of the target table in OpenSearch Vector."),
        content: str = Field(..., description="The text to query"),
        namespace: Optional[str] = Field(default=None, description="The namespace of the target table in OpenSearch Vector.")
):
    """
    :param table_name: str
    :param content: str
    :param namespace: Optional[str]
    :return: SearchResult
    """
    try:
        request = QueryRequest(table_name=table_name,
                               content=content,
                               modal="text",
                               namespace=namespace,
                               search_params="{\\\"qc.searcher.scan_ratio\\\":0.01}",
                               top_k=10,
                               order="DESC",
                               output_fields=["content"])
        result = client.inference_query(request)
        json_body = json.loads(result.body)
        if len(json_body.get("errorMsg", '')) > 0:
            raise Exception(f"{json_body['errorMsg']}")
        return json_body
    except Exception as e:
        raise Exception(f"{str(e)}") from e


@mcp.tool(
    name="multi_query",
    description="Perform a multi search based on vectors."
)
async def multi_query(
        table_name: str = Field(..., description="The name of the target table in OpenSearch Vector."),
        vector_list: List[List[float]] = Field(..., description="A list of dense vectors to be used for the multi-vector similarity search.")
):
    """
    :param table_name: str
    :param vector_list: List[List[float]]
    :return: SearchResult
    """
    try:
        query_list = []
        for vector in vector_list:
            request = QueryRequest(table_name=table_name,
                                   vector=vector,
                                   include_vector=True,
                                   top_k=10)
            query_list.append(request)
        multi_query_request = MultiQueryRequest(table_name="test",
                                                queries=query_list,
                                                top_k=10)
        result = client.multi_query(multi_query_request)
        json_body = json.loads(result.body)
        if len(json_body.get("errorMsg", '')) > 0:
            raise Exception(f"{json_body['errorMsg']}")
        return json_body
    except Exception as e:
        raise Exception(f"{str(e)}") from e


@mcp.tool(
    name="mix_query_with_sparse_vector",
    description="Perform a complex search based on a single dense vector and a sparse vector."
)
async def mix_query_with_sparse_vector(
        table_name: str = Field(..., description="The name of the target table in OpenSearch Vector."),
        vector: List[float] = Field(..., description="A dense vector used as the primary query vector for similarity search."),
        sparse_ids: List[int] = Field(..., description="A list of token IDs representing the indices of the sparse vector."),
        sparse_values: List[float] = Field(..., description="A list of corresponding weights for each token ID in sparse_ids, forming the sparse vector.")
):
    """
    :param table_name: str
    :param vector: List[float]
    :param sparse_ids: List[int]
    :param sparse_values: List[float]
    :return: SearchResult
    """
    try:
        index_name = config["index_name"]
        sparse_data = SparseData(indices=sparse_ids, values=sparse_values)
        request = QueryRequest(table_name=table_name,
                               index_name=index_name,
                               vector=vector,
                               sparse_data=sparse_data,
                               include_vector=True,
                               top_k=10)
        result = client.query(request)
        json_body = json.loads(result.body)
        if len(json_body.get("errorMsg", '')) > 0:
            raise Exception(f"{json_body['errorMsg']}")
        return json_body
    except Exception as e:
        raise Exception(f"{str(e)}") from e


@mcp.tool(
    name="mix_query_with_text",
    description="Perform a complex search based on a single dense vector and a text."
)
async def mix_query_with_text(
        table_name: str = Field(..., description="The name of the target table in OpenSearch Vector."),
        vector: List[float] = Field(..., description="A dense vector for similarity search."),
        content: str = Field(..., description="A text query for similarity search.")
):
    """
    :param table_name: str
    :param vector: List[float]
    :param content: str
    :return: SearchResult
    """
    try:
        index_name = config["index_name"]
        knn = QueryRequest(index_name=index_name,
                           vector=vector,
                           include_vector=True,
                           top_k=10)
        text = TextQuery(query_string=f"content:'{content}'")
        request = SearchRequest(table_name=table_name,
                                size=10,
                                knn=knn,
                                text=text)
        result = client.search(request)
        json_body = json.loads(result.body)
        if len(json_body.get("errorMsg", '')) > 0:
            raise Exception(f"{json_body['errorMsg']}")
        return json_body
    except Exception as e:
        raise Exception(f"{str(e)}") from e


if __name__ == "__main__":
    mcp.run()
