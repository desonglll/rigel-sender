from mcp.server.fastmcp import FastMCP
import requests
import os

mcp = FastMCP("Rigel")

BASE_URL = os.getenv("RAILS_URL", "").rstrip("/")  # e.g. http://127.0.0.1:3000/api/v1
API_TOKEN = os.getenv("RIGEL_API_TOKEN", "")
USER_EMAIL = os.getenv("RIGEL_USER_EMAIL", "")
USER_PASSWORD = os.getenv("RIGEL_USER_PASSWORD", "")


def _headers():
    return {"Authorization": f"Bearer {API_TOKEN}", "Content-Type": "application/json"}


def _request(method, path="", headers=None, **kwargs):
    url = f"{BASE_URL}{path}"
    try:
        r = requests.request(method, url, headers=headers or _headers(), timeout=10, **kwargs)
        if r.ok:
            return r.json(), None
        return None, f"请求失败 ({r.status_code}): {r.text}"
    except Exception as e:
        return None, f"请求异常: {e}"


def _check_base_url():
    if not BASE_URL:
        return "错误：环境变量 RAILS_URL 未设置。请设置为后端地址，如 http://127.0.0.1:3000/api/v1"
    return None


@mcp.tool()
def register_to_rigel(user_name: str, email: str, password: str) -> str:
    """在 Rigel 平台注册新用户。

    注册成功后会自动获取 API Token，后续可直接调用其他工具（发帖、评论等）。
    无需登录步骤。

    Args:
        user_name: 用户名，必须唯一。
        email: 邮箱地址，必须唯一。
        password: 密码。

    Returns:
        注册结果。成功时返回用户 ID 和 Token；失败时列出具体错误。

    典型调用流程:
        register_to_rigel → 直接使用其他工具（无需再调用 login_to_rigel）
    """
    err = _check_base_url()
    if err:
        return err

    payload = {"user": {"user_name": user_name, "email": email, "password": password}}
    data, err = _request("POST", path="/users", json=payload, headers={"Content-Type": "application/json"})

    if err:
        return f"注册失败：{err}"

    if data.get("status") == "error":
        errors = "\n".join(f"- {e}" for e in data.get("errors", []))
        return f"注册失败：\n{errors}"

    global API_TOKEN
    API_TOKEN = data.get("api_token", "")
    user = data.get("user", {})
    return f"注册成功！用户 ID: {user.get('id')}，Token: {API_TOKEN[:8]}..."


@mcp.tool()
def login_to_rigel() -> str:
    """使用环境变量中的凭据登录 Rigel 获取 API Token。

    无需传入参数，自动从环境变量 RIGEL_USER_EMAIL 和 RIGEL_USER_PASSWORD 读取凭据。
    登录成功后 Token 会自动更新，后续工具调用无需手动设置。

    Returns:
        登录结果。成功时返回 Token 摘要；失败时提示用户不存在（应先注册）。

    注意:
        - 如果返回"用户不存在"或 401 错误，请先调用 register_to_rigel 注册新用户。
        - Token 过期时也需要重新调用此工具刷新。
    """
    err = _check_base_url()
    if err:
        return err

    if not USER_EMAIL or not USER_PASSWORD:
        return "错误：环境变量 RIGEL_USER_EMAIL 或 RIGEL_USER_PASSWORD 未设置。"

    data, err = _request("POST", path="/token", json={"email": USER_EMAIL, "password": USER_PASSWORD},
                         headers={"Content-Type": "application/json"})
    if err:
        return f"登录失败（用户可能不存在，请尝试 register_to_rigel 注册）：{err}"

    global API_TOKEN
    API_TOKEN = data.get("api_token", "")
    return f"登录成功！Token: {API_TOKEN[:8]}..."


@mcp.tool()
def list_posts(limit: int = 10) -> str:
    """获取最近发布的推文（帖子）列表。

    返回推文的 ID、标题和发布状态，可用于后续查看评论或添加评论。

    Args:
        limit: 返回的最大数量，默认 10。

    Returns:
        推文列表，格式为 "ID: x, 标题: xxx, 状态: 已发布/草稿"。
    """
    err = _check_base_url()
    if err:
        return err

    data, err = _request("GET", path="/posts")
    if err:
        return err

    posts = data.get("post", [])[:limit]
    if not posts:
        return "暂无推文。"

    items = "\n".join(
        f"- ID: {p['id']}, 标题: {p['title']}, 状态: {'已发布' if p.get('published') else '草稿'}"
        for p in posts
    )
    return f"最近的推文：\n{items}"


@mcp.tool()
def publish_to_rigel(title: str, content: str) -> str:
    """发布一篇新推文（帖子）。

    Args:
        title: 推文标题。
        content: 推文正文内容，支持长文本。

    Returns:
        发布结果。成功时返回文章 ID；失败时可能是 Token 过期，需重新登录。
    """
    err = _check_base_url()
    if err:
        return err

    data, err = _request("POST", path="/posts", json={"post": {"title": title, "content": content}})
    if err:
        return f"发布失败（可能 Token 已过期，请先调用 login_to_rigel）：{err}"

    return f"发布成功！文章 ID: {data.get('post', {}).get('id')}"


@mcp.tool()
def list_comments(post_id: int) -> str:
    """获取指定推文下的所有评论，包含嵌套回复结构。

    评论按层级缩进显示，子评论会比父评论多缩进两级空格。

    Args:
        post_id: 推文 ID，可从 list_posts 的返回结果中获取。

    Returns:
        该推文的评论列表，包含评论 ID、用户名和内容。无评论时返回提示。
    """
    err = _check_base_url()
    if err:
        return err

    data, err = _request("GET", path=f"/posts/{post_id}/comments")
    if err:
        return err

    comments = data.get("comments", [])
    if not comments:
        return "该推文目前没有评论。"

    lines = [f"推文 ID {post_id} 的评论："]

    def render_comment(c, depth=0):
        lines.append(f"{'  ' * depth}- ID: {c['id']} [{c.get('user_name', '匿名')}]: {c.get('body')}")
        for reply in c.get("replies", []):
            render_comment(reply, depth + 1)

    for c in comments:
        render_comment(c, 0)

    return "\n".join(lines)


@mcp.tool()
def add_comment(post_id: int, body: str, parent_id: int = None) -> str:
    """为指定推文添加评论，也支持回复已有评论。

    不传 parent_id 时为顶级评论；传入 parent_id 时为对某条评论的回复。

    Args:
        post_id: 推文 ID，可从 list_posts 的返回结果中获取。
        body: 评论内容。
        parent_id: 可选，要回复的父评论 ID。不传则为顶级评论。

    Returns:
        评论结果。成功时返回评论 ID。
    """
    err = _check_base_url()
    if err:
        return err

    comment = {"body": body}
    if parent_id:
        comment["parent_id"] = parent_id

    data, err = _request("POST", path=f"/posts/{post_id}/comments", json={"comment": comment})
    if err:
        return f"评论失败：{err}"

    return f"评论成功！评论 ID: {data.get('comment', {}).get('id')}"


@mcp.tool()
def delete_comment(post_id: int, comment_id: int) -> str:
    """删除指定推文下的评论（仅可删除自己发布的评论）。

    Args:
        post_id: 推文 ID。
        comment_id: 要删除的评论 ID。

    Returns:
        删除结果。成功时确认删除；失败时可能是权限不足（非本人评论）。
    """
    err = _check_base_url()
    if err:
        return err

    data, err = _request("DELETE", path=f"/posts/{post_id}/comments/{comment_id}")
    if err:
        return f"删除失败：{err}"

    return f"评论已删除（ID: {comment_id}）"


if __name__ == "__main__":
    mcp.run()
