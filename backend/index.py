import os
import chromadb
from sentence_transformers import SentenceTransformer
from intent import process_query

print("Loading embedding model...")
embedder = SentenceTransformer('all-MiniLM-L6-v2')

print("Setting up ChromaDB...")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
client = chromadb.PersistentClient(path=os.path.join(BASE_DIR, "vectordb"))

try:
    client.delete_collection("medirisk")
    print("Existing collection deleted!")
except:
    pass

collection = client.create_collection("medirisk")
print("Collection created!")

def parse_chunks(filepath):
    chunks = []
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    raw_chunks = content.split('[CHUNK_START]')
    for raw in raw_chunks:
        if '[CHUNK_END]' not in raw:
            continue
        chunk_text = raw.split('[CHUNK_END]')[0].strip()
        lines = chunk_text.split('\n')
        metadata = {}
        text_lines = []

        for line in lines:
            if line.startswith('TOPIC:'):
                metadata['topic'] = line.replace('TOPIC:', '').strip()
            elif line.startswith('DISEASE:'):
                metadata['disease'] = line.replace('DISEASE:', '').strip()
            elif line.startswith('SOURCE:'):
                metadata['source'] = line.replace('SOURCE:', '').strip()
            elif line.startswith('KEYWORDS:'):
                metadata['keywords'] = line.replace('KEYWORDS:', '').strip()
            elif line.strip():
                text_lines.append(line.strip())

        chunk_content = ' '.join(text_lines)
        if chunk_content and metadata:
            chunks.append({'text': chunk_content, 'metadata': metadata})

    return chunks


def build_embedding_text(chunk):
    metadata = chunk["metadata"]
    topic = metadata.get("topic", "")
    disease = metadata.get("disease", "")
    keywords = metadata.get("keywords", "")
    text = chunk["text"]

    return (
        f"Topic: {topic}. "
        f"Disease: {disease}. "
        f"Keywords: {keywords}. "
        f"Content: {text}"
    )

# All 8 knowledge files
knowledge_files = [
    os.path.join(BASE_DIR, 'knowledge', 'diabetes.txt'),
    os.path.join(BASE_DIR, 'knowledge', 'diabetes_types.txt'),
    os.path.join(BASE_DIR, 'knowledge', 'heart_disease.txt'),
    os.path.join(BASE_DIR, 'knowledge', 'general_health.txt'),
    os.path.join(BASE_DIR, 'knowledge', 'foods.txt'),
    os.path.join(BASE_DIR, 'knowledge', 'indian_diet.txt'),
    os.path.join(BASE_DIR, 'knowledge', 'south_indian_diabetes_diet.txt'),
    os.path.join(BASE_DIR, 'knowledge', 'heart_diet_indian.txt'),
]

all_chunks = []
for filepath in knowledge_files:
    chunks = parse_chunks(filepath)
    all_chunks.extend(chunks)
    print(f"Loaded {len(chunks)} chunks from {os.path.basename(filepath)}")

print(f"\nTotal chunks: {len(all_chunks)}")

print("\nGenerating embeddings and storing in ChromaDB...")
for i, chunk in enumerate(all_chunks):
    embedding_text = build_embedding_text(chunk)
    embedding = embedder.encode(embedding_text).tolist()
    collection.add(
        ids=[f"chunk_{i:03d}"],
        embeddings=[embedding],
        documents=[chunk['text']],
        metadatas=[chunk['metadata']]
    )

print(f"\nSuccessfully stored {len(all_chunks)} chunks!")
print(f"Total in DB: {collection.count()}")

# Test
test_queries = ["weekly plan for diabetes", "heart diet indian", "foods avoid diabetes"]
for q in test_queries:
    expanded_query = process_query(q)["expanded"]
    emb = embedder.encode(expanded_query).tolist()
    res = collection.query(query_embeddings=[emb], n_results=2)
    print(f"\nQuery: '{q}'")
    for i, doc in enumerate(res['documents'][0]):
        print(f"  {i+1}. {res['metadatas'][0][i]['topic']}: {doc[:80]}...")
