import os
import logging
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')




def load_and_chunk_file(file_path, chunk_size=500, chunk_overlap=100):
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == ".pdf":
        loader = PyPDFLoader(file_path)
    elif ext in [".txt", ".md"]:
        loader = TextLoader(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")
    
    docs = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    chunks = splitter.split_documents(docs)
    
    logging.info(f"Loaded and chunked {len(chunks)} chunks from {file_path}")
    return chunks


def build_vector_index(chunks,session_id):
    """
    Builds the vector index, loading it from disk if it exists, 
    or creating and saving it otherwise.
    """
    INDEX_PATH = f"./data/faiss_indexes/{session_id}"
    embedder = OpenAIEmbeddings(model="text-embedding-3-small")

    # 1. Check if the index already exists locally
    if os.path.exists(INDEX_PATH):
        try:
            logging.info(f"Loading existing FAISS index from {INDEX_PATH}...")
            
            vector_store = FAISS.load_local(
                INDEX_PATH, 
                embedder, 
                allow_dangerous_deserialization=True # Required for loading components
            )
            logging.info("FAISS index loaded successfully.")
            return vector_store
        except Exception as e:
            logging.error(f"Failed to load FAISS index: {e}. Rebuilding index.")
            # Fall through to rebuild if loading fails

    # 2. If index doesn't exist, create the directory
    if not os.path.exists(INDEX_PATH):
        os.makedirs(INDEX_PATH)
        logging.info(f"Created index directory: {INDEX_PATH}")

    # 3. Create the index (the slow part, runs only once)
    logging.info("Creating new FAISS index (this may take time)...")
    vector_store = FAISS.from_documents(chunks, embedder)
    
    # 4. Save the index for future runs
    vector_store.save_local(INDEX_PATH)
    logging.info(f"New FAISS index created and saved to {INDEX_PATH}")
    
    return vector_store

def retrieve_relevant_chunks(query, vector_store, top_k=5):
    results = vector_store.similarity_search(query, k=top_k)
    return results

def construct_prompt(query, retrieved_chunks):
    context = "\n\n".join([doc.page_content for doc in retrieved_chunks])
    prompt = f"""You are a helpful assistant. Use the following context to answer the question.
If you don't find relevant information in the context, say "I don't know..

Context:
{context}

Question:
{query}
"""
    return prompt


def generate_answer(prompt, model_name="gpt-3.5-turbo", max_tokens=2048):
    llm = ChatOpenAI(model_name=model_name, max_tokens=max_tokens)
    response = llm.invoke(prompt)
    return response.content


# def evaluate_answer(answer, ground_truth):
#     return {
#         "exact_match": answer.strip().lower() == ground_truth.strip().lower(),
#         "length": len(answer),
#         "contains_keywords": all(kw in answer for kw in ground_truth.split()[:3])
#     }

