"""
This module is usable to calculate cosine similarity for small number of vectors.

See here https://alex-ber.medium.com/in-memory-similarity-search-998582fbb802 for documentation.

You need to install some 3rd-party dependencies. In order to use it, you should have them installed first.
To do it, run `python -m pip install alex-ber-utils[np]`.

For production purposes, you should install another dependency such as langchain_openai to use, for example, OpenAIEmbeddings.
Run `python -m pip install langchain-openai`.

This module contains SimpleEmbeddings for some simple-minded in-memory calculation of embeddings.
It is provided mainly for educational purposes and for tests. It is not intended to be used in production.

"""

import logging
from typing import List, Tuple, Dict, Protocol

logger = logging.getLogger(__name__)


# For example
# from langchain_openai import OpenAIEmbeddings

class Embeddings(Protocol):
    """
    Protocol for embedding classes.
    """

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a list of documents (texts) into a list of vectors.

        Args:
            texts (List[str]): List of documents to embed.

        Returns:
            List[List[float]]: List of embedding vectors.
        """
        ...


class SimpleEmbeddings:
    """
    Simple in-memory implementation of embeddings for educational and testing purposes.
    """

    def __init__(self, dims: int = 1536):
        """
        Initialize the SimpleEmbeddings with a specified dimension size.

        Args:
            dims (int): Dimension size of the embedding vectors. Default is 1536.
        """
        self.dims = dims

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a list of documents (texts) into a list of vectors.

        Args:
            texts (List[str]): List of documents to embed.

        Returns:
            List[List[float]]: List of embedding vectors.
        """
        embeddings = []
        for text in texts:
            embedding_vector = [0] * self.dims
            # This effectively counts the occurrences of each character in the text, mapped to a fixed-size vector.
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
        "You appear to be missing some optional dependencies; "
        "please run 'python -m pip install alex-ber-utils[numpy]'."
    )
    warnings.warn(warning, ImportWarning)
    raise


def _calc_embedding_as_matrix(embeddings: Embeddings, text: str) -> np.ndarray:
    """
    Calculate the embedding of a single text as a matrix.

    Args:
        embeddings (Embeddings): Embedding class instance.
        text (str): Text to embed.

    Returns:
        np.ndarray: Embedding vector as a matrix.
    """
    v = embeddings.embed_documents([text])[0]
    return np.array(v).reshape(1, -1)


def find_most_similar_with_scores(
        embeddings: Embeddings,
        input_text: str,
        /,
        *args: List[str],
        verbose=True
) -> List[Tuple[Tuple[int, str], float]]:
    """
    Find the most similar texts to the input text with their similarity scores.

    Args:
        embeddings (Embeddings): Embedding class instance.
        input_text (str): Input text to compare.
        *args (List[str]): List of texts to compare against.
        verbose (bool): If True, logs additional information. Default is True.

    Returns:
        List[Tuple[Tuple[int, str], float]]: A list of tuples where each tuple contains:
            - A sub-tuple (index, text): index is the position of the text in the input list,
              and text is the corresponding text.
            - A float representing the similarity score.

        If no comparison texts are provided (*args is empty),
        the function returns [((some negative index, input_text), 0.0)].
    """
    logger.info("find_most_similar_with_scores()")
    if not args:
        # List[Tuple[Tuple[int, str], float]]
        # (i, example), score (-1, input_text), 0.0
        return [((-1, input_text), 0.0)]

    input_v: np.ndarray = _calc_embedding_as_matrix(embeddings, input_text)
    example_embeddings_d: Dict[Tuple[int, str], np.ndarray] = {
        (i, example): _calc_embedding_as_matrix(embeddings, example)
        for i, example in enumerate(args)
    }

    # Stack all example embeddings into a single matrix
    example_matrix = np.vstack([v for v in example_embeddings_d.values()])

    # Calculate norms based on the specified ord
    input_norm = np.linalg.norm(input_v, axis=1, keepdims=True)
    example_norms = np.linalg.norm(example_matrix, axis=1, keepdims=True)

    # Calculate cosine similarities in one go
    similarities_matrix = np.dot(input_v, example_matrix.T) / np.outer(input_norm, example_norms)

    # Handle numerical issues
    similarities_matrix[np.isnan(similarities_matrix) | np.isinf(similarities_matrix)] = 0.0

    # Extract scores and sort
    similarities_d: Dict[Tuple[int, str], float] = {key: similarities_matrix[0, idx] for idx, key in enumerate(example_embeddings_d.keys())}
    sorted_similarities_l: List[Tuple[Tuple[int, str], float]] = sorted(similarities_d.items(), key=lambda item: item[1], reverse=True)

    if verbose:
        logger.info(f'Target is {input_text}')
        for (i, example), score in sorted_similarities_l:
            logger.info(f"{i} {example}: has cosine similarity {score:.4f}")

    return sorted_similarities_l


def find_most_similar(
        embeddings: Embeddings,
        input_text: str,
        /,
        *args: List[str],
        verbose=True
) -> Tuple[int, str]:
    """
    Find the most similar text to the input text.

    Args:
        embeddings (Embeddings): Embedding class instance.
        input_text (str): Input text to compare.
        *args (List[str]): List of texts to compare against.
        verbose (bool): If True, logs additional information. Default is True.

    Returns:
        Tuple[int, str]: A tuple containing the index and the most similar text.

    If no comparison texts are provided (*args is empty), the function returns (some negative index, input_text).
    """
    logger.info("find_most_similar()")
    sorted_similarities_l: List[Tuple[Tuple[int, str], float]] = \
        find_most_similar_with_scores(embeddings, input_text,*args, verbose=verbose)
    return sorted_similarities_l[0][0]