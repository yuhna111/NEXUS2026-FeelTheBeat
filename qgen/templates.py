"""Question templates for VN-Admin2025-QA (Week 3, TV1).

Groups: A direct lookup · B obsolete-district trap · C multi-hop spatial · D before/after.
Generated questions are paraphrased by an LLM, then 100% manually checked.
"""
from __future__ import annotations

TEMPLATES: dict[str, list[str]] = {
    "A_direct": [
        "Tỉnh {new_province} mới được hợp nhất từ những tỉnh nào?",
        "Trung tâm hành chính của tỉnh {new_province} hiện nay đặt ở đâu?",
    ],
    "B_obsolete_trap": [
        "Chủ tịch UBND huyện {old_district} hiện nay đóng trụ sở ở đâu?",
        "Huyện {old_district} hiện có bao nhiêu xã?",
    ],
    "C_multihop_spatial": [
        "Tỉnh mới chứa {old_unit} cũ giáp với những tỉnh/thành nào?",
    ],
    "D_before_after": [
        "Trước và sau 01/07/2025, trung tâm hành chính của tỉnh {old_province} thay đổi thế nào?",
    ],
}

# Group B: 20% negative controls — valid questions about units that still exist.
NEGATIVE_CONTROL_RATIO = 0.2
