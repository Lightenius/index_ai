from SemanticRetriever import *
import documents

# 1. Initialize the retriever
# Note: "BAAI/bge-m3" is a strong multilingual model, but you can 
# swap it with "all-MiniLM-L6-v2" for faster CPU performance.
retriever = SemanticRetriever(
    model_name="BAAI/bge-m3", 
    chunk_size=400,
    overlap=60,
    device=None # automatically uses CUDA if available, otherwise CPU
)

# 2. Get your PDF data using the function created earlier
pdf_data = documents.get_pdf_dicts()

# (Mock data representing the output of pdf_iceriklerini_listele)


# 3. Index the documents (chunks the text and computes embeddings)
print("Indexing documents...")
num_chunks = retriever.index(pdf_data)
print(f"Successfully indexed {num_chunks} text passages.")

# 4. Search for a query
query = input("Query to test: ")
results = retriever.retrieve(prompt=query, top_k=2)

# 5. Process the results
for i, result in enumerate(results, 1):
    print(f"\n--- Result {i} (Similarity Score: {result['score']:.4f}) ---")
    print(f"File: {result['filename']}")
    print(f"Page: {result['page_number']}")
    print(f"Content: {result['content']}")