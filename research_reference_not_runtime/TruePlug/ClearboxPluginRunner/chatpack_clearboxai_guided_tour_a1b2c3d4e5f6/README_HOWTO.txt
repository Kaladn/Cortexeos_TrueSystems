HOW TO COMPLETE AND INSTALL THIS CHAT PACK
==========================================

Pack ID: chatpack_clearboxai_guided_tour_a1b2c3d4e5f6

STEP 1 — Fill in the 4 files
─────────────────────────────
  metadata.json   — Pack title, tags, difficulty, short description
  instructor.txt  — The AI persona + rules (system prompt)
  lesson.txt      — The lesson content split into sections
  questions.json  — Comprehension questions (one per section)

  Each file has inline instructions at the top. Follow them, then delete the
  instruction comments before installing.

STEP 2 — Install the pack
──────────────────────────
  Copy this entire folder to:

    C:\Users\Lee\AppData\Local\ForestAI\chat_packs\packs\

  Full path after copy:
    C:\Users\Lee\AppData\Local\ForestAI\chat_packs\packs\
        chatpack_clearboxai_guided_tour_a1b2c3d4e5f6\
            metadata.json
            instructor.txt
            lesson.txt
            questions.json

  Alternatively, if you want it bundled with the source:
    E:\ForestAI-ROCm-7.1\plugins\chat_packs\packs\

STEP 3 — Activate in the bridge
─────────────────────────────────
  Restart the bridge server (or use the Settings → Restart Bridge button).
  The Chat Packs engine scans the packs folder at startup.

  Open the Chat Packs panel in the UI — your new pack should appear in the list.

REQUIRED FILES (all 4 must be present or the pack is skipped):
  metadata.json
  instructor.txt
  lesson.txt
  questions.json
