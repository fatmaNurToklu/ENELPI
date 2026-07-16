import chromadb
from chromadb.utils.embedding_functions import OllamaEmbeddingFunction
from mevzuat_db import mevzuat_listesi

# ChromaDB bağlantısı
client = chromadb.PersistentClient(path="./chroma_veri")

# Embedding fonksiyonu (nomic-embed-text)
embedding_fn = OllamaEmbeddingFunction(
    url="http://localhost:11434/api/embeddings",
    model_name="nomic-embed-text"
)

# Koleksiyon oluştur (varsa sil, yeniden yükle)
try:
    client.delete_collection("mevzuat")
except:
    pass

koleksiyon = client.create_collection(
    name="mevzuat",
    embedding_function=embedding_fn
)

koleksiyon.add(
    ids=[m["id"] for m in mevzuat_listesi],
    documents=[m["metin"] for m in mevzuat_listesi],
    metadatas=[{
        "kanun": m["kanun"],
        "madde": m["madde"],
        "evrak_turleri": ",".join(m["evrak_turleri"])
    } for m in mevzuat_listesi]
)

print(f"{len(mevzuat_listesi)} mevzuat ChromaDB'ye yüklendi.")