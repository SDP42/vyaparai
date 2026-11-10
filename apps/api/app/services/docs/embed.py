"""Sentence embeddings from a pretrained multilingual model, run locally on CPU with ONNX.

Default: paraphrase-multilingual-MiniLM-L12-v2 (Apache-2.0, 50+ languages including Hindi, 384
dimensions, about 220 MB, downloaded once). The choice was made by measurement; see
docs/DOCUMENTS.md. The model is loaded once per process.
"""

import threading
from typing import Any

import numpy as np

from app.core.errors import AppError

DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
_lock = threading.Lock()
_models: dict[str, Any] = {}


class EmbeddingUnavailableError(AppError):
    status_code = 503
    code = "embeddings_unavailable"


def _load(name: str) -> Any:
    with _lock:
        if name not in _models:
            try:
                from fastembed import TextEmbedding

                _models[name] = TextEmbedding(model_name=name)
            except Exception as exc:  # download blocked, disk full, package missing
                raise EmbeddingUnavailableError(
                    "The search model is not available on this server yet."
                ) from exc
        return _models[name]


def embed(texts: list[str], model: str = DEFAULT_MODEL, batch: int = 32) -> np.ndarray:
    """Unit-length float32 vectors, one row per text."""
    if not texts:
        return np.zeros((0, 0), dtype=np.float32)
    m = _load(model)
    vecs = np.array(list(m.embed(texts, batch_size=batch)), dtype=np.float32)
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    return vecs / np.maximum(norms, 1e-9)
