# persona-kit

把一份人设档案挂到任何 OpenAI 兼容的模型前面。

同一个角色，换模型不换脾气；换会话不换记忆。你只维护一份 JSON，剩下的是代理的事。

## 为什么会有这东西

调角色最费劲的地方不是提示词写得漂不漂亮，是**散**。人设在提示词里，规矩在系统预设里，记忆在某个向量库里，称呼写在另一个文件里。改一次要翻五个地方，改漏一个，这个角色就有点不对了——它还是那个人，但不完全是。

persona-kit 把这些收进一份档案：

```json
{
  "name": "zora",
  "identity": "我是谁。",
  "tone": "我说话的样子。",
  "aliases": { "her": "她怎么叫我" },
  "rules": ["硬规矩，一条一行"],
  "banned": ["不许出现的词"],
  "memories": ["长期记忆，一条一件"],
  "lessons": ["我犯过的错，和教训"]
}
```

然后跑一个代理，所有请求先过它：

```
你的客户端 ──► persona-kit ──► 模型
                │
                └─ 注入人设 + 记忆 + 规矩
```

## 装

只用 Python 标准库，不用 pip install 任何东西。

```bash
git clone https://github.com/dongbingyu9-a11y/persona-kit.git
cd persona-kit
python3 -m persona_kit.cli serve --persona personas/zora.json --upstreams upstreams.json
```

## 用

上游配置 `upstreams.json`：

```json
{
  "upstreams": [
    { "name": "main",  "base_url": "https://api.example.com/v1", "model": "gpt-x",  "api_key_env": "MAIN_KEY", "priority": 10 },
    { "name": "spare", "base_url": "https://api2.example.com/v1", "model": "gpt-x", "api_key_env": "SPARE_KEY", "priority": 20 }
  ]
}
```

密钥走环境变量，不进配置文件。

客户端把 base_url 指过来：

```python
from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:8080/v1", api_key="whatever")
client.chat.completions.create(
    model="anything",
    messages=[{"role": "user", "content": "在吗"}],
)
```

`model` 写什么都行，代理会换成本来配好的模型名。

上游 429 或者 5xx，代理自动换下一条。全部挂了就返回 502，里面带每条线失败的原因。

## 命令

```bash
python3 -m persona_kit.cli init  --name zora --out personas/zora.json   # 生成一份空档案
python3 -m persona_kit.cli show  --persona personas/zora.json             # 看档案
python3 -m persona_kit.cli add   --persona personas/zora.json --field rules --text "..."
python3 -m persona_kit.cli serve --persona personas/zora.json --upstreams upstreams.json --port 8080
```

`add` 支持的 field：rules、banned、memories、lessons。

## 接口

| 路径 | 干什么 |
| --- | --- |
| `POST /v1/chat/completions` | 转发，注入档案 |
| `GET /health` | 看每条上游现在的状态 |
| `GET /profile` | 看当前生效的档案 |

## 几个设计上的选择

**注入放最前面。** 档案排在 system 最前，原有的系统设定接在后面。模型先看到"我是谁"，再看别的。

**注入带 marker。** 同一份档案注两次不会出现两份重复的人设——客户端要是自己又塞了一遍，会被认出来。

**规矩单独成段。** rules 和 banned 不跟正文混在一起。前者是"怎么做"，后者是"不许说"，混进散文里模型会漏。

**上游失败往回退。** 代理不会因为一条线抽风就把错误甩给用户，它自己换线。返回的 502 里写清楚了每条线为什么挂，方便排查。

**档案是明文 JSON。** 人设是你自己的东西，不该锁在某个数据库的读权限后面。谁都能看懂，谁都能改。

## 许可

MIT