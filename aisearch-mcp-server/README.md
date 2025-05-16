# AISearch-MCP-Server
AISearch-MCP-Server serves as a universal interface between AI Agents and OpenSearch AI Search Platform.

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
		"aisearch-mcp-server": {
			"command": "uv",
			"args": [
				"--directory",
				"/path/to/aisearch-mcp-server",
				"run",
				"aisearch-mcp-server"
			],
			"env": {
				"AISEARCH_API_KEY": "<AISEARCH_API_KEY>",
				"AISEARCH_ENDPOINT": "<AISEARCH_ENDPOINT>"
			}
		}
	}
}
```
## Components
### Tools
* `document_analyze`: 
  * Provide a general-purpose document parsing service. You can use this service to extract logical structures, such as titles and paragraphs, from non-structured documents, such as text, tables, and images, to generate structured data. 
* `image_analyze`: 
  * Parse the content of images based on multimodal large language models (LLMs). You can also use the service to parse the text in images and use the parsed text for image retrieval and conversational search.
* `document_split`: 
  * Provide a general-purpose text splitting service. You can use this service to split structured data in the HTML, MARKDOWN, and TXT formats based on paragraphs, semantics, and specific rules. You can also extract code, images, and tables from rich text. 
* `text_embedding`: 
  * ops-text-embedding-001 provides a text vectorization service that supports more than 40 languages. The input text can be up to 300 tokens in length, and the dimension of the generated vectors is 1,536. 
  * ops-text-embedding-002 provides a text vectorization service that supports more than 100 languages. The input text can be up to 8,192 tokens in length, and the dimension of the generated vectors is 1,024. 
  * ops-text-embedding-zh-001 provides a text vectorization service for Chinese text. The input text can be up to 1,024 tokens in length, and the dimension of the generated vectors is 768. 
  * ops-text-embedding-en-001 provides a text vectorization service for English text. The input text can be up to 512 tokens in length, and the dimension of the generated vectors is 768. 
* `text_sparse_embedding`:
  * Convert text data into sparse vectors that occupy less storage space. You can use sparse vectors to express keywords and the information about frequently used terms. You can perform a hybrid search by using sparse and dense vectors to improve the retrieval performance. 
* `rerank`: 
  * Provide a general-purpose document scoring service. This service scores documents based on the relevance between queries and document content, sorts documents in descending order based on scores, and then returns the scores. The service supports Chinese and English. The input text can be up to 512 tokens in length, which includes the length of queries and documents. 
* `web_search`: 
  * Provide internet search service. When the private knowledge base cannot provide corresponding answers, expand the search to obtain more internet information, supplement the private knowledge base, and combine it with large language models to provide richer answers.
* `query_analyze`: 
  * Provide the content analysis service for queries based on LLMs and the Natural Language Processing (NLP) capabilities to understand the intent of users, extend similar questions, and convert questions in natural languages into SQL statements. This improves the performance of conversational search in retrieval-augmented generation (RAG) scenarios. 
