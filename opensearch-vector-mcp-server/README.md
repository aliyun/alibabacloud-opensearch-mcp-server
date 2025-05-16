# OpenSearch-Vector-MCP-Server
OpenSearch-Vector-MCP-Server serves as a universal interface between AI Agents and OpenSearch Vector.

## Configuration
### Mode 1: Using Local File
#### Download
Download from GitHub
```shell
git clone https://github.com/aliyun/alibabacloud-opensearch-mcp-server.git
```
#### MCP Integration
Add the following configuration to the MCP client configuration file:
```json
{
	"mcpServers": {
		"opensearch-vector-mcp-server": {
			"command": "uv",
			"args": [
				"--directory",
				"/path/to/opensearch-vector-mcp-server",
				"run",
				"opensearch-vector-mcp-server"
			],
			"env": {
				"OPENSEARCH_VECTOR_ENDPOINT": "http://ha-cn-***.public.ha.aliyuncs.com",
				"OPENSEARCH_VECTOR_USERNAME": "<username>",
				"OPENSEARCH_VECTOR_PASSWORD": "<password>",
				"OPENSEARCH_VECTOR_INSTANCE_ID": "ha-cn-***",
				"OPENSEARCH_VECTOR_INDEX_NAME": "<Optional: index in vector table>",
				"AISEARCH_API_KEY": "<Optional: AISEARCH_API_KEY for embedding>",
				"AISEARCH_ENDPOINT": "<Optional: AISEARCH_ENDPOINT for embedding>"
			}
		}
	}
}
```
## Components
### Tools
* `simple_search`: Perform a simple search based on either a text query or a vector.
* `query_by_ids`: Perform a simple search based on key ids.
* `inference_query`: Perform a simple search based on text after configuring EmbeddingModel in OpenSearch Console.
* `multi_query`: Perform a multi search based on vectors.
* `mix_query_with_sparse_vector`: Perform a complex search based on a single dense vector and a sparse vector.
* `mix_query_with_text`: Perform a complex search based on a single dense vector and a text.
