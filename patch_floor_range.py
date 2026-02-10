"""Patch script to add floor range input to the planning form."""
import pathlib

BASE = pathlib.Path(__file__).parent


def patch_html():
    """Add floor range inputs to index.html plan form."""
    p = BASE / "frontend" / "index.html"
    lines = p.read_text("utf-8").split("\n")

    # Already patched?
    for l in lines:
        if "floor-start" in l:
            print("HTML: already patched, skipping")
            return

    insert_block = [
        '              <label style="margin-top: 15px;">작업 층수 범위</label>',
        '              <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 10px;">',
        '                <input id="floor-start" type="number" min="1" placeholder="시작층" style="width: 100px; padding: 8px; border: 1px solid #ddd; border-radius: 6px;" />',
        '                <span style="font-weight: 600;">층 ~</span>',
        '                <input id="floor-end" type="number" min="1" placeholder="끝층" style="width: 100px; padding: 8px; border: 1px solid #ddd; border-radius: 6px;" />',
        '                <span style="font-weight: 600;">층</span>',
        '              </div>',
        '',
    ]

    for i, l in enumerate(lines):
        if "우선 작업 구역" in l:
            lines = lines[:i] + insert_block + lines[i:]
            break

    p.write_text("\n".join(lines), "utf-8")
    print("HTML: patched OK")


def patch_main_py():
    """Add floor_start/floor_end to DailyInput and _build_rag_context."""
    p = BASE / "backend" / "main.py"
    src = p.read_text("utf-8")

    # 1. DailyInput model - add floor fields
    if "floor_start" not in src:
        old = "    priority_areas: List[str] = Field(default_factory=list)"
        new = (
            "    priority_areas: List[str] = Field(default_factory=list)\n"
            "    floor_start: Optional[int] = None\n"
            "    floor_end: Optional[int] = None"
        )
        src = src.replace(old, new, 1)

        # Make sure Optional is imported
        if "Optional" not in src.split("from typing import")[0] + src.split("from typing import")[1].split("\n")[0] if "from typing import" in src else "":
            pass  # We'll check below

        # Ensure Optional is in the typing import
        if "from typing import" in src and "Optional" not in src.split("\n")[0:30].__repr__():
            # Find the typing import line
            lines = src.split("\n")
            for i, l in enumerate(lines):
                if "from typing import" in l and "Optional" not in l:
                    lines[i] = l.rstrip().rstrip(")") + ", Optional)"
                    if not l.strip().endswith(")"):
                        lines[i] = l.rstrip() + ", Optional"
                    break
            src = "\n".join(lines)

    # 2. _build_rag_context - add floor_range
    if "floor_range_rag" not in src:
        old_ctx = '        "waterproof_sequences_rag": {"retrieved_docs": sequence_docs},'
        new_ctx = (
            '        "waterproof_sequences_rag": {"retrieved_docs": sequence_docs},\n'
            '        "floor_range_rag": {"start": payload.floor_start, "end": payload.floor_end},'
        )
        src = src.replace(old_ctx, new_ctx, 1)

    p.write_text(src, "utf-8")
    print("main.py: patched OK")


def patch_app_js():
    """Add floor_start/floor_end to the plan generation payload."""
    p = BASE / "frontend" / "app.js"
    src = p.read_text("utf-8")

    if "floor_start" not in src:
        old = '      priority_areas: parseCSV(document.getElementById("areas").value),'
        new = (
            '      priority_areas: parseCSV(document.getElementById("areas").value),\n'
            '      floor_start: parseInt(document.getElementById("floor-start").value) || null,\n'
            '      floor_end: parseInt(document.getElementById("floor-end").value) || null,'
        )
        src = src.replace(old, new, 1)

    p.write_text(src, "utf-8")
    print("app.js: patched OK")


def patch_ai_agent():
    """Add floor range info to the AI system prompt."""
    p = BASE / "backend" / "ai_agent.py"
    src = p.read_text("utf-8")

    if "floor_range_rag" not in src:
        old_prompt = "- waterproof_sequences_rag: 방수 작업 순서(RAG)"
        new_prompt = (
            "- waterproof_sequences_rag: 방수 작업 순서(RAG)\n"
            "- floor_range_rag: 오늘 작업할 층수 범위 (start~end층). 아랫층부터 윗층 순서대로 작업 배정해라."
        )
        src = src.replace(old_prompt, new_prompt, 1)

        # Add rule about floor range
        old_rule = "6. **overview 및 guidelines**: 오늘의 전체적인 작업 전략과 안전/품질 주의사항을 구체적으로 작성해라."
        new_rule = (
            "6. **overview 및 guidelines**: 오늘의 전체적인 작업 전략과 안전/품질 주의사항을 구체적으로 작성해라.\n"
            "7. **층수 순서 준수**: floor_range_rag에 start/end가 있으면 해당 층 범위 내에서만 작업을 배정하고, **아랫층(start)부터 윗층(end) 순서**로 작업해라. 예: 2층→3층→4층"
        )
        src = src.replace(old_rule, new_rule, 1)

    p.write_text(src, "utf-8")
    print("ai_agent.py: patched OK")


if __name__ == "__main__":
    patch_html()
    patch_main_py()
    patch_app_js()
    patch_ai_agent()
    print("\nAll patches applied!")
