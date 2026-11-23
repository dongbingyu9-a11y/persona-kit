# 客户端怎么用 persona-kit。

# 1. 起代理
#    python3 -m persona_kit.cli serve --persona personas/zora.json --upstreams upstreams.json --port 8080
#
# 2. 指过去
import os

from openai import OpenAI

# 上游的真实 key 走环境变量，别写进配置文件
os.environ.setdefault("MAIN_KEY", "sk-...")

client = OpenAI(base_url="http://127.0.0.1:8080/v1", api_key="local")

resp = client.chat.completions.create(
    model="whatever",  # 代理会换成上游配好的模型名
    messages=[{"role": "user", "content": "在吗"}],
)
print(resp.choices[0].message.content)

# 3. 看上游现在的状态
import json
import urllib.request

with urllib.request.urlopen("http://127.0.0.1:8080/health") as r:
    print(json.dumps(json.load(r), ensure_ascii=False, indent=2))