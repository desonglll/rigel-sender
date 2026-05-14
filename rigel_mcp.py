from mcp.server.fastmcp import FastMCP
import requests
import os

mcp = FastMCP("Rigel")

# 基础 URL 指向 /api/v1/posts
BASE_URL = os.getenv("RAILS_URL") # 应该是 http://127.0.0.1:3000/api/v1/posts
API_TOKEN = os.getenv("RIGEL_API_TOKEN")

def get_headers():
    return {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json"
    }

@mcp.tool()
def list_posts(limit: int = 10) -> str:
    """获取最近发布的推文列表。"""
    try:
        response = requests.get(BASE_URL, headers=get_headers())
        if response.status_code == 200:
            posts = response.json().get('post', [])
            summary = "\n".join([f"- ID: {p['id']}, 标题: {p['title']}" for p in posts[:limit]])
            return f"最近的推文如下：\n{summary}"
        return f"读取失败: {response.text}"
    except Exception as e:
        return f"错误: {str(e)}"

@mcp.tool()
def publish_to_rigel(title: str, content: str) -> str:
    """发布新推文。"""
    data = {"post": {"title": title, "content": content}}
    try:
        response = requests.post(BASE_URL, json=data, headers=get_headers())
        if response.status_code == 201:
            return f"✅ 发布成功！文章 ID: {response.json().get('post', {}).get('id')}"
        return f"❌ 发布失败: {response.text}"
    except Exception as e:
        return f"⚠️ 连接服务器出错: {str(e)}"

@mcp.tool()
def list_comments(post_id: int) -> str:
    """
    获取指定推文下的所有评论。
    在发表评论前，建议先查看已有评论以保持对话连贯性。
    """
    url = f"{BASE_URL}/{post_id}/comments"
    try:
        response = requests.get(url, headers=get_headers())
        if response.status_code == 200:
            comments_data = response.json().get('comments', [])
            if not comments_data:
                return "该推文目前没有评论。"
            
            output = [f"推文 ID {post_id} 的评论列表："]
            for c in comments_data:
                depth_str = "  " * c['depth']
                output.append(f"{depth_str}- ID: {c['id']} [{c['user_name']}]: {c['body']}")
            return "\n".join(output)
        return f"无法获取评论: {response.text}"
    except Exception as e:
        return f"错误: {str(e)}"

@mcp.tool()
def add_comment(post_id: int, body: str, parent_id: int = None) -> str:
    """
    为指定推文添加评论。
    参数:
    - post_id: 推文的 ID
    - body: 评论内容
    - parent_id: 如果是回复某条评论，请提供该评论的 ID（可选）
    """
    url = f"{BASE_URL}/{post_id}/comments"
    data = {
        "comment": {
            "body": body,
            "parent_id": parent_id
        }
    }
    try:
        response = requests.post(url, json=data, headers=get_headers())
        if response.status_code == 201:
            res_json = response.json().get('comment', {})
            return f"✅ 评论成功！评论 ID: {res_json.get('id')}"
        return f"❌ 评论失败: {response.text}"
    except Exception as e:
        return f"⚠️ 连接服务器出错: {str(e)}"

if __name__ == "__main__":
    mcp.run()
