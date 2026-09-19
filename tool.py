import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from typing import Literal
from langchain.tools import ToolRuntime, tool
from dataclasses import dataclass
import uuid
mcp_client = MultiServerMCPClient({
  "gmail": {
      "command": "npx",
      "args": ["-y", "@gongrzhe/server-gmail-autoauth-mcp"],
      "transport": "stdio",
  },
  "calendar": {
      "command": "npx",
      "args": ["-y", "@gongrzhe/server-calendar-autoauth-mcp"],
      "transport": "stdio",
  },
})


async def get_tools():
  tools = await mcp_client.get_tools()
  return tools


@dataclass
class Context:
    user_id: str
@tool
def get_infomation(runtime: ToolRuntime[Context], content, memory_type: Literal['semantic', 'procedural', 'episodic']) -> str:
  """Tìm kiếm thông tin đã lưu trong long-term memory bằng semantic search.

    Luôn gọi tool này TRƯỚC khi dùng add_infomation hoặc update_infomation,
    để biết thông tin liên quan đã tồn tại chưa và lấy đúng key nếu cần cập nhật.

    Chọn đúng memory_type theo loại thông tin cần tìm:
    - "semantic": Sự thật, kiến thức tĩnh về user (sở thích, thông tin cá nhân).
    - "episodic": Sự kiện/trải nghiệm cụ thể đã xảy ra, gắn với thời gian.
    - "procedural": Quy trình, cách làm, hướng dẫn từng bước đã học được.

    Args:
        content: Câu truy vấn tự nhiên mô tả thông tin cần tìm.
        memory_type: Loại memory cần tìm trong - "semantic", "procedural", hoặc "episodic".

    Returns:
        Danh sách tối đa 3 bản ghi gần nghĩa nhất, kèm key của từng bản ghi.
        Trả về chuỗi rỗng nếu không tìm thấy gì liên quan.
    """
  store = runtime.store
  namespace = ("memories", runtime.context.user_id, memory_type)
  existing_memories = store.search(namespace, query=content, limit=3)
  return "\n".join([
    f"{i+1}: key: {m.key}, content: {m.value.get('content', '')}"
    for i, m in enumerate(existing_memories)
])
  
@tool
def update_infomation(runtime: ToolRuntime[Context], key, content, memory_type: Literal['semantic', 'procedural', 'episodic']) -> str:
  """Cập nhật nội dung của 1 bản ghi đã tồn tại trong long-term memory.

  CHỈ dùng tool này khi đã biết chính xác key của bản ghi cần sửa
  (lấy được từ kết quả gọi get_infomation trước đó). Nếu chưa chắc
  thông tin đã tồn tại hay chưa, gọi get_infomation trước để kiểm tra.
  Nếu là thông tin hoàn toàn mới, dùng add_infomation thay vì tool này.

  Args:
      key: Key chính xác của bản ghi cần cập nhật, lấy từ get_infomation.
      content: Nội dung mới, sẽ ghi đè hoàn toàn nội dung cũ tại key này.
      memory_type: Loại memory chứa bản ghi - "semantic", "procedural", hoặc "episodic".
  Notes:
    - "semantic": Sự thật, kiến thức tĩnh về user (sở thích, thông tin cá nhân).
    - "episodic": Sự kiện/trải nghiệm cụ thể đã xảy ra, gắn với thời gian.
    - "procedural": Quy trình, cách làm, hướng dẫn từng bước đã học được.

  Returns:
      Thông báo xác nhận đã cập nhật thành công.
  """
  store = runtime.store
  namespace = ("memories", runtime.context.user_id, memory_type)
  store.put(namespace=namespace, key=key, value={"content": content})
  return f"Updated memory with key: {key}, content: {content} to {memory_type} memory."

@tool 
def add_infomation(runtime: ToolRuntime[Context], content, memory_type: Literal['semantic', 'procedural', 'episodic']) -> str:
  """Thêm 1 bản ghi hoàn toàn mới vào long-term memory.

    CHỈ dùng tool này khi đã gọi get_infomation và xác nhận chưa có
    thông tin tương tự nào tồn tại. Nếu thông tin tương tự đã có,
    dùng update_infomation thay vì tạo bản ghi trùng lặp.

    Args:
        content: Nội dung cần lưu, viết dạng câu hoàn chỉnh, rõ nghĩa,
            đủ ngữ cảnh để hiểu độc lập (không phụ thuộc câu trước/sau).
        memory_type: Loại memory cần lưu vào - "semantic", "procedural", hoặc "episodic".
    Notes:
        - "semantic": Sự thật, kiến thức tĩnh về user (sở thích, thông tin cá nhân).
        - "episodic": Sự kiện/trải nghiệm cụ thể đã xảy ra, gắn với thời gian.
        - "procedural": Quy trình, cách làm, hướng dẫn từng bước đã học được.
    Returns:
        Thông báo xác nhận đã lưu thành công kèm key mới được tạo.
    """
  store = runtime.store
  key = str(uuid.uuid4())
  namespace = ("memories", runtime.context.user_id, memory_type)
  store.put(namespace=namespace, key=key, value={"content": content})
  return f"Added memory with key: {key}, content: {content} to {memory_type} memory."
