import os
from redis.retry import Retry
from redis.backoff import NoBackoff
from pathlib import Path
import redis
import json
import hashlib

client = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=6379,
    decode_responses=True,
    socket_connect_timeout=1,
    socket_timeout=1,
    retry=Retry(NoBackoff(), 0)
)

def build_cache_payload(question,temperature,kb_version):
   #  在这里创建并返回一个字典
  result = {
      'question':question,
      'temperature':temperature,
      'kb_version':kb_version,
      'model':'deepseek-chat',
      'top_k':3,
      'pipeline_version':'v1'
  }
  return result


def build_cache_key(question,temperature,kb_version):
    payload = build_cache_payload(question,temperature,kb_version)
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return "personal-rag:answer:v1:" + digest

def get_cached_response(key):
    try:
        text = client.get(key)# 读取缓存
    except redis.exceptions.RedisError:
        return None,'bypass'
    if text is None:
       return None,'miss'
    try:
        data = json.loads(text)# 读到了：还原成字典并返回

    except json.JSONDecodeError:#格式错误的缓存也会被当作未命中，继续原有问答流程
        return None,'miss'

    if not isinstance(data,dict):
        return None,'miss'
    required_fields=['answer', 'sources','generation_tokens_used']
    for field in required_fields:
        if field not in data:
            return None,'miss'

    if not isinstance(data["answer"], str):
        return None,'miss'
    if not isinstance(data["sources"], list):
        return None,'miss'
    for source in data["sources"]:
        if not isinstance(source, str): # 如果 source 不是字符串，返回 None
            return None,'miss'

    tokens=data["generation_tokens_used"]
    if type(tokens) is not int:
        return None,'miss'
    if tokens < 0:
        return None,'miss'
    return data,'hit'




def save_cached_response(key, result, ttl=3600):
    text=json.dumps(result, ensure_ascii=False) # 把结果字典转换成 JSON 文字
    try:
        return client.set(key,text,ex=ttl) # 保存到 Redis，设置有效期，并返回保存结果
    except redis.exceptions.RedisError:
        return False

def get_file_hash(file_path):
    with open(file_path, "rb") as file:
        content = file.read()  # 读取文件内容
    return hashlib.sha256(content).hexdigest()        # 返回内容的 SHA-256 指纹

def get_knowledge_version(knowledge_dir):
    files = []

    for path in sorted(Path(knowledge_dir).iterdir()):
        if path.is_file():
            files.append({
                "name": path.name,
                "hash": get_file_hash(path)
            })

    text = json.dumps(files, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


