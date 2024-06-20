#TODO: add documentation

"""
You need to install some 3-rd party dependencies, in order to use it, you should have installed first. To do it
run `python -m pip install alex-ber-utils[np]` in order to use it.

For production purposes, you should install another dependency such as langchain_openai in order to use,
for example OpenAIEmbeddings. Run 'python -m pip install langchain-openai'`.

This module contains SimpleEmbeddings for some simple-minding in-memory calculation of embedding.
It is provided mainly for education purposes and for tests. It is not intended to be used in production.

See URL for documentation.
"""

import logging
from typing import List, Tuple, Dict, Protocol

logger = logging.getLogger(__name__)


#for example
#from langchain_openai import OpenAIEmbeddings
class Embeddings(Protocol):
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        ...

class SimpleEmbeddings:
    def __init__(self, dims: int = 1536):
        self.dims = dims

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        embeddings = []
        for text in texts:
            embedding_vector = [0] * self.dims
            #This effectively counts the occurrences of each character in the text, mapped to a fixed-size vector.
            for char in text:
                index = hash(char) % self.dims
                embedding_vector[index] += 1
            embeddings.append(embedding_vector)
        return embeddings

try:
    import numpy as np
except ImportError:
    import warnings

    warning = (
        "You appear to be missing some optional dependencies;"
        "please 'python -m pip install alex-ber-utils[numpy]'."
    )
    warnings.warn(warning, ImportWarning)
    raise


def _calc_embedding_as_matrix(embeddings: Embeddings, text: str) -> np.ndarray:
    v = embeddings.embed_documents([text])[0]
    return np.array(v).reshape(1, -1)

def find_most_similar_with_scores(embeddings: Embeddings, input_text: str, *args: List[str],
                                  ord_norm: int = 2, verbose=True) -> List[Tuple[Tuple[int, str], float]]:
    logger.info("find_most_similar_with_scores()")
    if not args:
        return [(input_text, 1.0)]

    input_v: np.ndarray = _calc_embedding_as_matrix(embeddings, input_text)

    example_embeddings_d: Dict[Tuple[int, str], np.ndarray] = {
        (i, example): _calc_embedding_as_matrix(embeddings, example) for i, example in enumerate(args)
    }

    # Stack all example embeddings into a single matrix
    example_matrix = np.vstack([v for v in example_embeddings_d.values()])

    # Calculate norms based on the specified ord
    input_norm = np.linalg.norm(input_v, axis=1, keepdims=True, ord=ord_norm)
    example_norms = np.linalg.norm(example_matrix, axis=1, keepdims=True, ord=ord_norm)

    # Calculate cosine similarities in one go
    similarities_matrix = np.dot(input_v, example_matrix.T) / np.outer(input_norm, example_norms)

    # Handle numerical issues
    similarities_matrix[np.isnan(similarities_matrix) | np.isinf(similarities_matrix)] = 0.0

    # Extract scores and sort
    similarities_d = {
        key: similarities_matrix[0, idx] for idx, key in enumerate(example_embeddings_d.keys())
    }
    sorted_similarities_d = sorted(similarities_d.items(), key=lambda item: item[1], reverse=True)

    if verbose:
        logger.info(f'Target is {input_text}')
        for (i, example), score in sorted_similarities_d:
            logger.info(f"{i} {example}: has cosine similarity {score:.4f}")

    return sorted_similarities_d

def find_most_similar(embeddings: Embeddings, input_text: str, /, *args: List[str],
                      ord_norm: int = 2, verbose=True) -> Tuple[int, str]:
    logger.info("find_most_similar()")
    sorted_similarities_d = find_most_similar_with_scores(embeddings, input_text, *args,
                                                          ord_norm=ord_norm, verbose=verbose)
    return sorted_similarities_d[0][0]
