#!/usr/bin/env python3
"""persona-kit 命令行。

    init  生成一份空档案
    show  看档案
    add   往档案里加一条
    serve 起代理
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .profile import LIST_FIELDS, load_persona, new_persona
from .server import serve
from .upstream import load_pool


def cmd_init(args):
    p = new_persona(args.name)
    out = Path(args.out)
    p.save(out)
    print("建好了：" + str(p.save(out)))
    return 0


def cmd_show(args):
    p = load_persona(args.persona)
    print(json.dumps(p.data, ensure_ascii=False, indent=2))
    return 0


def cmd_add(args):
    p = load_persona(args.persona)
    if args.field not in LIST_FIELDS:
        print("field 只能是：" + "、".join(LIST_FIELDS), file=sys.stderr)
        return 2
    if not p.add(args.field, args.text):
        print("没加（空内容，或者已经有了）")
        return 0
    p.save()
    print("加进 " + args.field + " 了。")
    return 0


def cmd_serve(args):
    persona = load_persona(args.persona)
    pool = load_pool(args.upstreams)
    serve(persona, pool, host=args.host, port=args.port, verbose=args.verbose)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="persona-kit", description="把一份人设档案挂到任何模型前面")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init", help="生成一份空档案")
    p.add_argument("--name", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("show", help="看档案")
    p.add_argument("--persona", required=True)
    p.set_defaults(func=cmd_show)

    p = sub.add_parser("add", help="往档案里加一条")
    p.add_argument("--persona", required=True)
    p.add_argument("--field", required=True, choices=list(LIST_FIELDS))
    p.add_argument("--text", required=True)
    p.set_defaults(func=cmd_add)

    p = sub.add_parser("serve", help="起代理")
    p.add_argument("--persona", required=True)
    p.add_argument("--upstreams", required=True)
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8080)
    p.add_argument("--verbose", action="store_true")
    p.set_defaults(func=cmd_serve)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())