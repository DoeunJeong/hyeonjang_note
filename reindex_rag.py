import os
import sys
import traceback
from pathlib import Path

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load .env manually
from dotenv import load_dotenv
load_dotenv()

try:
    from backend.rag_store import index_waterproof_sequence_doc
    
    # 직접 파일 경로 지정 (절대 경로)
    base_dir = Path(__file__).resolve().parent
    doc_path = base_dir / "data" / "rag_docs" / "waterproof_sequences.md"
    
    print(f"Indexing file: {doc_path}")
    print(f"File exists? {doc_path.exists()}")
    
    result = index_waterproof_sequence_doc(str(doc_path))
    print(f"Index result: {result}")

except Exception:
    traceback.print_exc()
