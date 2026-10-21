from SemanticRetriever import *
import documents

def retrieve_for(q: str, result_count: int = 5) -> str:
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

   
    # 3. Index the documents (chunks the text and computes embeddings)
    print("Indexing documents...", flush=True)
    num_chunks = retriever.index(pdf_data)
    print(f"Successfully indexed {num_chunks} text passages.")

    # 4. Search for a query
    query = q
    results = retriever.retrieve(prompt=query, top_k=result_count)

    res = []

    # 5. Process the results
    for i, result in enumerate(results, 1):
        res_item = ""
        res_item += f"\n--- Result {i} (Similarity Score: {result['score']:.4f}) ---\n"
        res_item += f"File: {result['filename']}\n"
        res_item += f"Page: {result['page_number']}\n"
        res_item += f"Content: {result['content']}\n"

        res.append(res_item)
    return res



def retrieve_dict_for(q: str, result_count: int = 5) -> str:
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

   
    # 3. Index the documents (chunks the text and computes embeddings)
    print("Indexing documents...", flush=True)
    num_chunks = retriever.index(pdf_data)
    print(f"Successfully indexed {num_chunks} text passages.")

    # 4. Search for a query
    query = q
    results = retriever.retrieve(prompt=query, top_k=result_count)

    res = []

    # 5. Process the results
    for i, result in enumerate(results, 1):
        res.append({
                            "pdf_id": "0",
                            "chunk_id": f"0_{result['page_number']}_semantic",
                            "page": result['page_number'],
                            "text": result['content'],
                            "ad": result["filename"],
                            "sayfa": result['page_number'],
                            "metin": result['content']
                        })
        
        
        
    return res

