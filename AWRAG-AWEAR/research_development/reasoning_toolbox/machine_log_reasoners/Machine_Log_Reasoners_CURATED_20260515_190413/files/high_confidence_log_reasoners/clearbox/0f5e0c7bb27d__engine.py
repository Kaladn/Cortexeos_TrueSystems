"""ChatPackEngine -- pack loading, section parsing, session state, message building."""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

_REQUIRED_FILES = {"metadata.json", "instructor.txt", "lesson.txt", "questions.json"}
_SECTION_PRIMARY = re.compile(r"^#\s+Section\s+\d+:\s*(.+)$", re.MULTILINE)
_SECTION_FALLBACK = re.compile(r"^#\s+(.+)$", re.MULTILINE)


class ChatPackEngine:
    """Singleton engine for Chat Packs -- pack loading, session management, message building."""

    def __init__(self):
        from chat_packs.config import load_config

        self._config = load_config()
        try:
            from security.data_paths import CHAT_PACKS_PACKS_DIR, CHAT_PACKS_SESSIONS_DIR
            self._packs_dir = CHAT_PACKS_PACKS_DIR
            self._sessions_dir = CHAT_PACKS_SESSIONS_DIR
        except ImportError:
            self._packs_dir = Path("chat_packs/packs")
            self._sessions_dir = Path("chat_packs/sessions")

        self._packs: Dict[str, Dict] = {}
        self._scan_packs()
        logger.info("ChatPackEngine: %d packs loaded from %s", len(self._packs), self._packs_dir)

    # ── Pack scanning ────────────────────────────────────────

    def _scan_packs(self) -> None:
        """Scan packs directory, load metadata for each valid pack."""
        self._packs.clear()
        if not self._packs_dir.exists():
            return
        for entry in self._packs_dir.iterdir():
            if not entry.is_dir():
                continue
            meta_path = entry / "metadata.json"
            if not meta_path.exists():
                continue
            try:
                with open(meta_path, "r", encoding="utf-8-sig") as f:
                    meta = json.load(f)
                pack_id = meta.get("pack_id", "")
                if not pack_id:
                    continue

                # Parse sections and questions for counts
                lesson_path = entry / "lesson.txt"
                lesson_text = ""
                if lesson_path.exists():
                    lesson_text = lesson_path.read_text(encoding="utf-8-sig")
                sections = self.parse_sections(lesson_text)

                questions_path = entry / "questions.json"
                questions = []
                if questions_path.exists():
                    try:
                        questions = json.loads(questions_path.read_text(encoding="utf-8-sig"))
                    except json.JSONDecodeError:
                        pass

                readme_path = entry / "README.txt"
                readme = ""
                if readme_path.exists():
                    readme = readme_path.read_text(encoding="utf-8-sig")

                self._packs[pack_id] = {
                    "pack_id": pack_id,
                    "title": meta.get("title", entry.name),
                    "version": meta.get("version", "0.1"),
                    "mode": meta.get("mode", "stepwise"),
                    "tags": meta.get("tags", []),
                    "difficulty": meta.get("difficulty", ""),
                    "folder": str(entry),
                    "sections": sections,
                    "questions": questions if isinstance(questions, list) else [],
                    "readme": readme,
                    "has_assets": (entry / "assets").is_dir() and any((entry / "assets").iterdir()),
                }
            except Exception as e:
                logger.warning("Failed to load pack from %s: %s", entry, e)

    # ── Pack access (metadata only, no full content in list) ─

    def list_packs(self) -> List[Dict]:
        """Return metadata for all installed packs (no content)."""
        result = []
        for p in self._packs.values():
            result.append({
                "pack_id": p["pack_id"],
                "title": p["title"],
                "version": p["version"],
                "mode": p["mode"],
                "tags": p["tags"],
                "difficulty": p["difficulty"],
                "total_sections": len(p["sections"]),
                "total_questions": len(p["questions"]),
                "has_assets": p["has_assets"],
                "readme": p["readme"],
            })
        return result

    def get_pack(self, pack_id: str) -> Optional[Dict]:
        """Return pack metadata + section titles (no full content)."""
        p = self._packs.get(pack_id)
        if not p:
            return None
        return {
            "pack_id": p["pack_id"],
            "title": p["title"],
            "version": p["version"],
            "mode": p["mode"],
            "tags": p["tags"],
            "difficulty": p["difficulty"],
            "total_sections": len(p["sections"]),
            "total_questions": len(p["questions"]),
            "has_assets": p["has_assets"],
            "readme": p["readme"],
            "section_titles": [s["title"] for s in p["sections"]],
            "question_count": len(p["questions"]),
        }

    # ── Section parsing ──────────────────────────────────────

    def parse_sections(self, lesson_text: str) -> List[Dict[str, str]]:
        """Parse lesson.txt into [{title, content}].

        Two-tier: primary = '# Section N: Title', fallback = any '# Title'.
        """
        if not lesson_text.strip():
            return []

        max_sections = self._config.get("max_sections", 50)

        # Try primary pattern first
        matches = list(_SECTION_PRIMARY.finditer(lesson_text))
        if not matches:
            matches = list(_SECTION_FALLBACK.finditer(lesson_text))

        if not matches:
            # No headers at all -- treat entire text as one section
            return [{"title": "Lesson", "content": lesson_text.strip()}]

        sections = []
        for i, m in enumerate(matches[:max_sections]):
            title = m.group(1).strip()
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(lesson_text)
            content = lesson_text[start:end].strip()
            sections.append({"title": title, "content": content})

        return sections

    def parse_questions(self, questions_raw: list) -> List[Dict]:
        """Validate and normalize questions list."""
        result = []
        max_q = self._config.get("max_questions", 20)
        for q in questions_raw[:max_q]:
            if not isinstance(q, dict):
                continue
            result.append({
                "id": q.get("id", len(result) + 1),
                "type": q.get("type", "concept"),
                "question": q.get("question", ""),
                "answer_keywords": q.get("answer_keywords", []),
            })
        return result

    # ── Install ──────────────────────────────────────────────

    def _validate_install(self, source_path: str) -> Optional[str]:
        """Validate install source. Returns error message or None."""
        src = Path(source_path).resolve()

        # Path must exist and be a directory
        if not src.exists() or not src.is_dir():
            return f"Source not found or not a directory: {src}"

        # Check allowed roots
        allowed_roots = self._config.get("allowed_install_roots", [])
        if allowed_roots:
            ok = False
            for root in allowed_roots:
                try:
                    src.relative_to(Path(root).resolve())
                    ok = True
                    break
                except ValueError:
                    continue
            if not ok:
                return f"Source path not under any allowed root. Allowed: {allowed_roots}"

        # Required files
        for req_file in _REQUIRED_FILES:
            if not (src / req_file).exists():
                return f"Missing required file: {req_file}"

        # Reject symlinks/junctions
        for item in src.rglob("*"):
            if item.is_symlink():
                return f"Symlink detected (rejected): {item}"

        # Size guard
        max_mb = self._config.get("max_install_size_mb", 10)
        total_bytes = sum(f.stat().st_size for f in src.rglob("*") if f.is_file())
        if total_bytes > max_mb * 1024 * 1024:
            return f"Pack exceeds {max_mb}MB size limit ({total_bytes // (1024*1024)}MB)"

        return None

    def install_pack(self, source_path: str) -> Dict:
        """Validate and copy pack folder into packs directory."""
        error = self._validate_install(source_path)
        if error:
            return {"pack_id": "", "installed": False, "error": {"message": error}}

        src = Path(source_path).resolve()

        # Read metadata to get pack_id
        with open(src / "metadata.json", "r", encoding="utf-8-sig") as f:
            meta = json.load(f)
        pack_id = meta.get("pack_id", "")
        if not pack_id:
            pack_id = f"chatpack_{src.name}_{uuid4().hex[:12]}"

        # Determine destination
        dest = self._packs_dir / src.name
        if dest.exists():
            # Overwrite existing
            shutil.rmtree(dest)

        shutil.copytree(str(src), str(dest), symlinks=False)
        logger.info("Installed pack '%s' → %s", pack_id, dest)

        # Rescan
        self._scan_packs()

        return {"pack_id": pack_id, "installed": True}

    # ── Session management ───────────────────────────────────

    def start_session(self, pack_id: str, model: str = "") -> Optional[Dict]:
        """Create a new session for a pack. Returns session dict or None."""
        pack = self._packs.get(pack_id)
        if not pack:
            return None

        session_id = uuid4().hex[:12]
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        session = {
            "session_id": session_id,
            "pack_id": pack_id,
            "model": model or self._config.get("default_model", "gpt_oss:20b"),
            "phase": "lesson",
            "section_index": 0,
            "question_index": 0,
            "total_sections": len(pack["sections"]),
            "total_questions": len(pack["questions"]),
            "scores": [],
            "started_utc": now,
            "updated_utc": now,
        }

        self._save_session(session_id, session)
        return session

    def get_session(self, session_id: str) -> Optional[Dict]:
        """Load session from disk."""
        path = self._sessions_dir / f"{session_id}.json"
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                return json.load(f)
        except Exception as e:
            logger.warning("Failed to read session %s: %s", session_id, e)
            return None

    def advance_session(self, session_id: str) -> Optional[Dict]:
        """Advance to next section/question. Returns updated session or None."""
        session = self.get_session(session_id)
        if not session:
            return None

        pack = self._packs.get(session["pack_id"])
        if not pack:
            return None

        phase = session["phase"]

        if phase == "lesson":
            if session["section_index"] + 1 < session["total_sections"]:
                session["section_index"] += 1
            else:
                # Transition to questions (or complete if no questions)
                if session["total_questions"] > 0:
                    session["phase"] = "questions"
                    session["question_index"] = 0
                else:
                    session["phase"] = "complete"
        elif phase == "questions":
            if session["question_index"] + 1 < session["total_questions"]:
                session["question_index"] += 1
            else:
                session["phase"] = "complete"

        session["updated_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        self._save_session(session_id, session)
        return session

    def reset_session(self, session_id: str) -> Optional[Dict]:
        """Reset session to beginning."""
        session = self.get_session(session_id)
        if not session:
            return None

        session["phase"] = "lesson"
        session["section_index"] = 0
        session["question_index"] = 0
        session["scores"] = []
        session["updated_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        self._save_session(session_id, session)
        return session

    def _save_session(self, session_id: str, session: Dict) -> None:
        """Persist session state to disk."""
        path = self._sessions_dir / f"{session_id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(session, f, indent=2)

    # ── Current content (for session response) ───────────────

    def get_current_content(self, session_id: str) -> Optional[Dict[str, str]]:
        """Return {title, body} for the current section or question."""
        session = self.get_session(session_id)
        if not session:
            return None

        pack = self._packs.get(session["pack_id"])
        if not pack:
            return None

        phase = session["phase"]

        if phase == "lesson":
            idx = session["section_index"]
            if idx < len(pack["sections"]):
                s = pack["sections"][idx]
                return {"title": s["title"], "body": s["content"]}
        elif phase == "questions":
            idx = session["question_index"]
            if idx < len(pack["questions"]):
                q = pack["questions"][idx]
                return {"title": f"Question {q['id']}", "body": q["question"]}
        elif phase == "complete":
            return {"title": "Complete", "body": "Lesson complete."}

        return None

    # ── Message building (for Ollama /api/chat) ──────────────

    def build_messages(self, session_id: str, user_msg: str) -> Optional[List[Dict[str, str]]]:
        """Build Ollama /api/chat messages array from session state.

        Returns:
            [
                {"role": "system", "content": instructor_text},
                {"role": "system", "content": section_or_question_context},
                {"role": "user", "content": user_msg},
            ]
        """
        session = self.get_session(session_id)
        if not session:
            return None

        pack = self._packs.get(session["pack_id"])
        if not pack:
            return None

        # Load instructor.txt
        folder = Path(pack["folder"])
        instructor_path = folder / "instructor.txt"
        instructor_text = ""
        if instructor_path.exists():
            instructor_text = instructor_path.read_text(encoding="utf-8-sig")

        # Build context based on phase
        phase = session["phase"]

        if phase == "lesson":
            idx = session["section_index"]
            if idx < len(pack["sections"]):
                s = pack["sections"][idx]
                context = (
                    f"Present Section {idx + 1} of {session['total_sections']}: "
                    f"{s['title']}\n\n{s['content']}"
                )
            else:
                context = "All sections have been presented."
        elif phase == "questions":
            idx = session["question_index"]
            if idx < len(pack["questions"]):
                q = pack["questions"][idx]
                context = (
                    f"Assessment Question {idx + 1} of {session['total_questions']}:\n\n"
                    f"{q['question']}"
                )
            else:
                context = "All questions have been asked."
        else:
            total_q = session["total_questions"]
            passed = sum(1 for s in session.get("scores", []) if s.get("passed"))
            context = (
                f"The lesson is complete. "
                f"The student answered {passed}/{total_q} questions correctly. "
                f"Provide a brief summary of what was covered."
            )

        return [
            {"role": "system", "content": instructor_text},
            {"role": "system", "content": context},
            {"role": "user", "content": user_msg},
        ]

    # ── Stats ────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        """Return plugin stats."""
        active = 0
        if self._sessions_dir.exists():
            for f in self._sessions_dir.iterdir():
                if f.suffix == ".json":
                    try:
                        data = json.loads(f.read_text(encoding="utf-8-sig"))
                        if data.get("phase") != "complete":
                            active += 1
                    except Exception:
                        pass
        return {
            "installed_count": len(self._packs),
            "active_sessions": active,
        }

    # ── Session listing (for Learning Center dashboard) ───────

    def list_sessions(self) -> List[Dict]:
        """Scan sessions dir, return all saved sessions with pack metadata."""
        results: List[Dict] = []
        if not self._sessions_dir.exists():
            return results
        for f in self._sessions_dir.iterdir():
            if f.suffix != ".json":
                continue
            try:
                data = json.loads(f.read_text(encoding="utf-8-sig"))
                pack_id = data.get("pack_id", "")
                pack = self._packs.get(pack_id)
                results.append({
                    "session_id": data.get("session_id", f.stem),
                    "pack_id": pack_id,
                    "pack_title": pack["title"] if pack else pack_id,
                    "phase": data.get("phase", "lesson"),
                    "section_index": data.get("section_index", 0),
                    "total_sections": data.get("total_sections", 0),
                    "question_index": data.get("question_index", 0),
                    "total_questions": data.get("total_questions", 0),
                    "started_utc": data.get("started_utc", ""),
                    "updated_utc": data.get("updated_utc", ""),
                })
            except Exception:
                pass
        results.sort(key=lambda s: s.get("updated_utc", ""), reverse=True)
        return results

    # ── Lesson view (one-fetch workspace data) ────────────────

    def get_lesson_view(self, session_id: str) -> Optional[Dict]:
        """Full workspace view: session + section outline with status + current content."""
        session = self.get_session(session_id)
        if not session:
            return None
        pack = self._packs.get(session["pack_id"])
        if not pack:
            return None

        phase = session["phase"]
        current_idx = session["section_index"]
        sections_outline = []

        for i, s in enumerate(pack["sections"]):
            if phase in ("questions", "complete"):
                status = "completed"
            elif i < current_idx:
                status = "completed"
            elif i == current_idx:
                status = "current"
            else:
                status = "locked"
            sections_outline.append({
                "index": i,
                "title": s["title"],
                "status": status,
            })

        current_content = self.get_current_content(session_id)

        return {
            "session": session,
            "pack_title": pack["title"],
            "sections": sections_outline,
            "current_content": current_content,
        }

    # ── Section content by index (for reviewing completed) ────

    def get_section_content(self, pack_id: str, index: int) -> Optional[Dict[str, str]]:
        """Return {title, body} for a specific section by index."""
        pack = self._packs.get(pack_id)
        if not pack:
            return None
        if index < 0 or index >= len(pack["sections"]):
            return None
        s = pack["sections"][index]
        return {"title": s["title"], "body": s["content"]}
