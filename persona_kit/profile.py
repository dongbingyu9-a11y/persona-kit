"""人设档案：读取、校验、增补、保存。

档案是一个 JSON 文件。字段都可以缺，只留 name 也能跑。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

LIST_FIELDS = ("rules", "banned", "memories", "lessons")
TEXT_FIELDS = ("identity", "tone", "opening")


@dataclass
class Persona:
    name: str
    path: Path | None = None
    data: dict[str, Any] = field(default_factory=dict)

    @property
    def marker(self) -> str:
        return "<!-- persona-kit:" + self.name + " -->"

    def get(self, key: str, default: Any = "") -> Any:
        return self.data.get(key, default)

    def list(self, key: str) -> list[str]:
        v = self.data.get(key) or []
        if isinstance(v, str):
            return [v]
        return [str(x) for x in v]

    def add(self, key: str, item: str) -> bool:
        item = str(item).strip()
        if not item:
            return False
        items = self.data.setdefault(key, [])
        if isinstance(items, str):
            items = [items]
            self.data[key] = items
        if item in items:
            return False
        items.append(item)
        return True

    def save(self, path: Path | None = None) -> Path:
        target = Path(path) if path else self.path
        if target is None:
            raise ValueError("这份档案没有目标路径")
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(target.suffix + ".tmp")
        tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(target)
        self.path = target
        return target


def load_persona(path: str | Path) -> Persona:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError("找不到档案：" + str(p))
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError("档案不是合法 JSON：" + str(e)) from e
    if not isinstance(data, dict):
        raise ValueError("档案必须是一个 JSON 对象")
    for k in LIST_FIELDS:
        if k in data and not isinstance(data[k], (list, str)):
            raise ValueError("字段 " + k + " 必须是字符串或字符串数组")
    for k in TEXT_FIELDS:
        if k in data and not isinstance(data[k], str):
            raise ValueError("字段 " + k + " 必须是字符串")
    name = str(data.get("name") or p.stem)
    return Persona(name=name, path=p, data=data)


def new_persona(name: str) -> Persona:
    return Persona(
        name=name,
        data={
            "name": name,
            "identity": "",
            "tone": "",
            "rules": [],
            "banned": [],
            "memories": [],
            "lessons": [],
        },
    )