from app.retrieval import aggregate_by_file


def pt(file_id: str, score: float, text: str = "x") -> dict:
    return {
        "score": score,
        "payload": {
            "id": f"c-{file_id}-{score}",
            "file_id": file_id,
            "file_name": f"{file_id}.md",
            "file_path": f"{file_id}.md",
            "file_type": "md",
            "section_path": ["S"],
            "page": None,
            "slide": None,
            "sheet": None,
            "row_range": None,
            "line_start": 1,
            "line_end": 2,
            "text": text,
        },
    }


def test_strong_single_chunk_beats_many_weak():
    points = [pt("strong", 0.9)] + [pt("weak", 0.3) for _ in range(5)]
    out = aggregate_by_file(points, 3)
    assert out[0]["file_id"] == "strong"


def test_multi_hit_bonus_breaks_ties():
    points = [pt("a", 0.5), pt("b", 0.5), pt("b", 0.4)]
    out = aggregate_by_file(points, 3)
    assert out[0]["file_id"] == "b"


def test_top_k_limit_and_match_shape():
    points = [pt(f"f{i}", 0.5 - i * 0.01) for i in range(6)]
    out = aggregate_by_file(points, 3)
    assert len(out) == 3
    m = out[0]["matches"][0]
    assert {"chunk_id", "score", "location", "snippet"} <= set(m)
    assert m["location"]["section"] == "S"
