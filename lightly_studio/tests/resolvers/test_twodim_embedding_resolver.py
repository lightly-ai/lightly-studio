from lightly_studio.resolvers.twodim_embedding_resolver import _calculate_2d_embeddings


def test__calculate_2d_embeddings__1_sample() -> None:
    embedding_values = [[0.1, 0.2, 0.3]]
    projected = _calculate_2d_embeddings(embedding_values)
    assert projected == [(0.0, 0.0)]


def test__calculate_2d_embeddings__2_samples() -> None:
    embedding_values = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    projected = _calculate_2d_embeddings(embedding_values)
    assert projected == [(0.0, 0.0), (1.0, 1.0)]
