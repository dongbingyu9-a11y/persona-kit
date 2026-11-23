"""把人设档案拼成 system prompt，并注进请求。

两个讲究：

1. 已经存在的 system 内容不丢。档案排在前面，原设定接在后面，
   模型先看到"我是谁"，再看别的。
2. 每次注入带一个 marker。同一份档案注两次不会出现两份重复的人设。
"""

from __future__ import annotations

from typing import Any

from .profile import Persona

LABELS = [
    ("identity", "身份"),
    ("tone", "说话方式"),
    ("opening", "开场"),
    ("rules", "硬规矩"),
    ("banned", "禁用词"),
    ("memories", "长期记忆"),
    ("lessons", "教训"),
]


def build_system_prompt(persona: Persona) -> str:
    parts: list[str] = ["【人设档案】"]
    for key, label in LABELS:
        if key in ("rules", "banned", "memories", "lessons"):
            items = persona.list(key)
            if items:
                parts.append("\n【" + label + "】\n" + "\n".join("- " + x for x in items))
        else:
            v = str(persona.get(key) or "").strip()
            if v:
                parts.append("\n【" + label + "】" + v)
    aliases = persona.get("aliases") or {}
    if isinstance(aliases, dict) and aliases:
        lines = []
        for k, v in aliases.items():
            if isinstance(v, (list, tuple)):
                v = "、".join(str(x) for x in v)
            lines.append(str(k) + " → " + str(v))
        if lines:
            parts.append("\n【称呼】\n" + "\n".join(lines))
    return "\n".join(parts).strip()


def _as_text(content: Any) -> str:
    if isinstance(content, list):
        return "".join(
            str(x.get("text", "")) for x in content if isinstance(x, dict)
        )
    return str(content or "")


def inject_messages(messages: list, system_prompt: str, marker: str) -> list:
    """返回注好人设的新 messages 列表，不改原对象。"""
    msgs = [dict(m) for m in messages]
    head = system_prompt + "\n" + marker
    if msgs and msgs[0].get("role") == "system":
        old = _as_text(msgs[0].get("content"))
        if marker not in old:
            msgs[0] = {"role": "system", "content": head + "\n\n" + old}
    else:
        msgs.insert(0, {"role": "system", "content": head})
    return msgs