I have a plenty of doucment in pptx, excel, docs and markdown. They are all business documents, to let AI ultilize this data source, I need an fast way to query the data. So Im thinking about modern RAG technique where we extract, indexing, chunking and ingest data into vector database, so the the AI can retrieve relevant data with exactly files' location, page, sections, et cetera...   

## Features

- Important extra metadata to store into vector DB like: file path, file name, location of chunk (page, line number, section, slide, sheet,...) - so the AI can know where to find the data and also the data surrounding that data chunk.
- I think we Only need embedding model input as environment (with OpenAI compatible)
- Expose a MCP server, so the AI can communicate to extract the data from vector DB
- About the extracting tools, it nust support different kind of document (pptx, excel, docx, pdf, markdown, text), 
- About the retrieval phase, It combine both keyword search and semantic search, so please choose a best and light-weight approach. The nmaximum of final output document to AI should be 3 documents. 
- I prefer to have hierarachical chunking technique because our approach here is to find the most relevant files for AI to refer to (not extracting text for LLM model to generate answer like chatbot). what lib do you suggest?
- About vector database, I prefer a lightweight one and can be run locally (docker,..). What is your suggestion?
- I plan to upload the source as a GIt repository, so I need a ready-to-run package, so other can run all thing in one shot (docker, python,...)
- 


## UI web page
- I need an UI page with basic operations:
    - Manage projects, each project has its separated storing area in vector database
    - In each project users can add and remove files (to load and remove chunks from vector DB)
    - a Button 'MCP Server' to show a popup message with mcp server information and ready-to-use json string, so user can copy and add to their mcp server config of other agent coding tools.
    - A search bar where user can input query with approiated length limit, then return a list of relevant document.

