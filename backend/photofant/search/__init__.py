"""Search-domain logic that sits above the vector index (ADR-024).

The HTTP layer lives in `photofant/api/search.py`; the nearest-neighbour index in
`photofant/db/vector_index.py`. This package holds the pieces in between — currently
the DINOv2 visual re-ranking of image→image candidates (P37).
"""
