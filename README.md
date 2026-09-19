# calendar-deep-agent

> Trợ lý AI cá nhân lên kế hoạch & quản lý lịch tự động, kết hợp **Gmail**, **Google Calendar** (qua MCP servers) và **long-term memory** (Postgres + vector search) để đưa ra kế hoạch phù hợp với thói quen thật sự của từng người dùng — thay vì một lịch chung chung.

Được xây trên [`deepagents`](https://github.com/langchain-ai/deepagents) + LangGraph, agent này không chỉ tạo sự kiện theo yêu cầu, mà còn:

- **Nhớ** thói quen/sở thích của người dùng qua các lần trò chuyện (long-term memory).
- **Tra cứu Gmail** để lấy thông tin thực tế (lời mời họp, deadline, vé máy bay...) thay vì suy đoán.
- **Kiểm tra lịch hiện có** trước khi tạo sự kiện mới để tránh chồng chéo.
- **Hỏi lại** khi thông tin chưa đủ, thay vì tự bịa mặc định.

---

## Mục lục

- [Kiến trúc tổng quan](#kiến-trúc-tổng-quan)
- [Tính năng chính](#tính-năng-chính)
- [Cấu trúc thư mục](#cấu-trúc-thư-mục)
- [Yêu cầu hệ thống](#yêu-cầu-hệ-thống)
- [Cài đặt](#cài-đặt)
- [Cấu hình](#cấu-hình)
- [Chạy thử](#chạy-thử)
- [Cách hoạt động của Memory](#cách-hoạt-động-của-memory)
- [Quy trình xử lý của Agent (System Prompt)](#quy-trình-xử-lý-của-agent-system-prompt)
- [Ví dụ sử dụng](#ví-dụ-sử-dụng)
- [Lưu ý & TODO trước khi deploy](#lưu-ý--todo-trước-khi-deploy)
- [Đóng góp](#đóng-góp)
- [License](#license)

---

## Kiến trúc tổng quan

```
                         ┌────────────────────────┐
                         │        Người dùng       │
                         └───────────┬────────────┘
                                     │ input (CLI)
                                     ▼
                         ┌────────────────────────┐
                         │   Deep Agent (LangGraph) │
                         │  model: Gemini (Google)  │
                         └───────────┬────────────┘
                 ┌───────────────────┼───────────────────┐
                 ▼                   ▼                   ▼
      ┌────────────────┐  ┌────────────────────┐  ┌──────────────────┐
      │  MCP: Gmail      │  │  MCP: Google Calendar│  │  Memory Tools     │
      │  (autoauth)      │  │  (autoauth)          │  │  add/get/update   │
      └────────────────┘  └────────────────────┘  └────────┬──────────┘
                                                             ▼
                                                  ┌────────────────────┐
                                                  │  PostgresStore       │
                                                  │  + HuggingFace       │
                                                  │  embeddings (384d)   │
                                                  │  (long-term memory)  │
                                                  └────────────────────┘

      Short-term memory (hội thoại trong 1 phiên) ─▶ InMemorySaver (checkpointer)
```

- **Short-term memory**: dùng `InMemorySaver` của LangGraph — lưu lịch sử hội thoại theo `thread_id` (1 phiên chạy = 1 thread), mất khi tắt chương trình.
- **Long-term memory**: dùng `PostgresStore` với vector search (embedding model `sentence-transformers/all-MiniLM-L6-v2`, 384 chiều) — lưu bền vững qua nhiều lần chạy, phân loại theo `semantic` / `episodic` / `procedural`.
- **MCP servers**: agent gọi 2 MCP server ngoài qua `npx` (stdio transport) để thao tác Gmail và Google Calendar thật.

---

## Tính năng chính

- 🧠 **Ghi nhớ thói quen người dùng** (giờ họp ưa thích, buffer time, khung giờ làm việc hiệu quả...) và tái sử dụng cho các lần lên lịch sau.
- 📧 **Đọc Gmail** để lấy thông tin liên quan (lời mời họp, xác nhận đặt vé, deadline dự án) trước khi lên lịch, tránh suy diễn sai.
- 📅 **Kiểm tra xung đột lịch** trên Google Calendar trước khi tạo sự kiện mới, tự động chừa buffer time.
- ❓ **Chủ động hỏi lại** khi thiếu thông tin quan trọng (thời gian, thời lượng, địa điểm, mức ưu tiên...) thay vì tự đặt mặc định.
- ✅ **Xác nhận trước khi tạo lịch** với kế hoạch nhiều sự kiện hoặc có khả năng ảnh hưởng lịch hiện có.

---

## Cấu trúc thư mục

```
.
├── index.py       # Entry point: khởi tạo agent, vòng lặp chat CLI
├── tool.py        # Định nghĩa MCP client (Gmail, Calendar) + 3 tool memory
├── memory.py       # Setup PostgresStore + embedding model cho long-term memory
├── prompt.py       # System prompt định nghĩa quy trình & nguyên tắc của agent
├── .env             # Biến môi trường (API key...) — KHÔNG commit lên Git
└── README.md
```

---

## Yêu cầu hệ thống

- Python 3.10+
- Node.js + npm (để `npx` chạy được MCP server `@gongrzhe/server-gmail-autoauth-mcp` và `@gongrzhe/server-calendar-autoauth-mcp`)
- PostgreSQL đang chạy (mặc định kết nối `localhost:5432`)
- Tài khoản Google đã cấu hình OAuth cho Gmail & Calendar (theo hướng dẫn của 2 package MCP trên)
- Google API key cho Gemini (`GOOGLE_API_KEY`)

### Thư viện Python chính

```
deepagents
langchain-google-genai
langchain-mcp-adapters
langgraph
langgraph-checkpoint
langgraph-store-postgres
langchain-huggingface
sentence-transformers
python-dotenv
```

> Repo hiện chưa có sẵn `requirements.txt` — nên thêm file này (xem mục [TODO](#lưu-ý--todo-trước-khi-deploy)) để người khác cài đặt dễ dàng, ví dụ:
>
> ```bash
> pip install deepagents langchain-google-genai langchain-mcp-adapters \
>   langgraph langgraph-checkpoint-postgres langgraph-store-postgres \
>   langchain-huggingface sentence-transformers python-dotenv
> ```

---

## Cài đặt

```bash
# 1. Clone repo
git clone https://github.com/<your-username>/calendar-deep-agent.git
cd calendar-deep-agent

# 2. Tạo virtual environment
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 3. Cài dependencies
pip install -r requirements.txt

# 4. Cài Node.js nếu chưa có (cần cho npx chạy MCP server)
# https://nodejs.org

# 5. Khởi tạo database Postgres
createdb postgres   # hoặc dùng DB có sẵn, chỉnh lại DB_URI trong memory.py/.env
```

---

## Cấu hình

Tạo file `.env` ở thư mục gốc:

```env
GOOGLE_API_KEY=your_google_api_key_here
```

> ⚠️ **Quan trọng**: hiện tại `DB_URI` (bao gồm password Postgres) đang bị **hardcode trực tiếp trong `memory.py`**. Trước khi đẩy lên GitHub, hãy chuyển giá trị này vào `.env` và đọc bằng `os.getenv`, xem chi tiết ở mục [TODO](#lưu-ý--todo-trước-khi-deploy) bên dưới.

Ví dụ sau khi sửa, `.env` nên có thêm:

```env
DATABASE_URL=postgresql://postgres:<password>@localhost:5432/postgres?sslmode=disable
```

Xác thực Gmail/Calendar: 2 package `@gongrzhe/server-gmail-autoauth-mcp` và `@gongrzhe/server-calendar-autoauth-mcp` sẽ tự mở luồng OAuth (autoauth) trong lần chạy đầu tiên — làm theo hướng dẫn trên terminal để cấp quyền cho tài khoản Google của bạn.

---

## Chạy thử

```bash
python index.py
```

Chương trình sẽ hỏi liên tục:

```
Nhập câu hỏi của bạn: <gõ yêu cầu của bạn>
```

Gõ `exit` để thoát.

---

## Cách hoạt động của Memory

### Long-term memory (`memory.py` + `tool.py`)

Lưu trong PostgreSQL, đánh index bằng embedding (`all-MiniLM-L6-v2`, 384 chiều) để hỗ trợ **semantic search** — tìm theo ý nghĩa chứ không chỉ khớp từ khóa.

Namespace lưu theo cấu trúc: `("memories", user_id, memory_type)`

| memory_type   | Dùng để lưu gì                                                        | Ví dụ                                                  |
|---------------|------------------------------------------------------------------------|---------------------------------------------------------|
| `semantic`    | Sự thật/kiến thức tĩnh về người dùng (sở thích, thông tin cá nhân)      | "Người dùng thích họp vào buổi sáng, tránh sau 17h"     |
| `episodic`    | Sự kiện/trải nghiệm cụ thể, gắn với thời điểm                          | "Ngày 10/9 người dùng đã dời lịch họp vì bận đón con"    |
| `procedural`  | Quy trình, thói quen làm việc từng bước                                | "Trước mỗi cuộc họp 15 phút, luôn cần đọc lại tài liệu" |

3 tool tương ứng trong `tool.py`:

- `get_infomation(content, memory_type)` — tìm kiếm semantic, trả về tối đa 3 bản ghi gần nghĩa nhất kèm `key`. **Luôn gọi tool này trước** khi thêm/sửa để tránh trùng lặp.
- `add_infomation(content, memory_type)` — thêm bản ghi mới (key tự sinh bằng `uuid4`).
- `update_infomation(key, content, memory_type)` — ghi đè nội dung bản ghi đã tồn tại (cần `key` lấy từ `get_infomation`).

### Short-term memory (`index.py`)

Dùng `InMemorySaver` của LangGraph làm checkpointer, gắn với `thread_id` sinh ngẫu nhiên mỗi lần chạy chương trình (`config = {"configurable": {"thread_id": thread_id}}`). Nhờ đó agent nhớ được ngữ cảnh hội thoại **trong cùng một phiên chạy**, nhưng sẽ mất khi restart chương trình (vì lưu trong RAM, không persist).

> Nếu muốn giữ lịch sử hội thoại qua nhiều lần chạy, cần đổi sang checkpointer persistent, ví dụ `PostgresSaver` (cùng họ với `PostgresStore` đang dùng cho long-term memory).

---

## Quy trình xử lý của Agent (System Prompt)

Toàn bộ logic điều phối nằm trong `prompt.py`, theo 7 bước bắt buộc mỗi khi nhận yêu cầu lên lịch:

1. **Tra cứu memory trước tiên** — gọi `get_infomation` để lấy thói quen/ràng buộc đã biết.
2. **Hỏi kỹ nếu memory chưa đủ** — không tự suy đoán sở thích/thói quen còn thiếu.
3. **Tra cứu Gmail** nếu yêu cầu phụ thuộc thông tin bên ngoài (lời mời họp, vé, deadline...).
4. **Kiểm tra lịch hiện có** trên Calendar, tránh chồng chéo, chừa buffer time (mặc định 15 phút).
5. **Hỏi lại nếu thông tin về sự kiện chưa đủ** (thời gian, thời lượng, địa điểm, mức ưu tiên, múi giờ) — không tự bịa mặc định.
6. **Xác nhận kế hoạch** trước khi tạo/sửa sự kiện thật (bỏ qua bước xác nhận nếu là 1 sự kiện đơn giản, không xung đột).
7. **Lưu lại thông tin hữu ích** cho lần sau (`add_infomation`/`update_infomation`), tránh lưu thông tin nhạy cảm không cần thiết hoặc chỉ dùng một lần.

Giọng điệu: trả lời ngắn gọn, đi thẳng vào phương án, không kể lể việc "đang gọi tool nào".

---

## Ví dụ sử dụng

```
Nhập câu hỏi của bạn: Xếp cho mình lịch họp với team marketing tuần sau

Agent: Mình thấy bạn thường họp buổi sáng và cần 15p nghỉ trước giờ ăn trưa.
Trong email gần đây có lời mời họp marketing gợi ý thứ 3 tuần sau — mình xếp
9h-10h thứ 3 (28/9), trước lịch gym 11h của bạn, ok không?

Nhập câu hỏi của bạn: ok
Agent: Đã tạo lịch "Họp team Marketing" 9h-10h thứ 3 28/9. Mình cũng đã lưu
lại là bạn ưu tiên họp buổi sáng nhé.
```

---

## Lưu ý & TODO trước khi deploy

Một số điểm nên xử lý trước khi public/production:

- [ ] **Bảo mật**: chuyển `DB_URI` (đang hardcode password trong `memory.py`) sang đọc từ biến môi trường `.env`, và thêm `.env` vào `.gitignore`.
- [ ] **Xác minh tên model**: `"gemini-3.5-flash"` trong `index.py` không khớp với tên model chính thức hiện có của Google (thường là dạng `gemini-x.x-flash`/`-pro` theo phiên bản đang phát hành) — kiểm tra lại tên model hợp lệ trước khi chạy, tránh lỗi runtime.
- [ ] **Thêm `requirements.txt`**: repo hiện chưa liệt kê dependencies, nên "freeze" lại để người khác cài đặt nhất quán.
- [ ] **Checkpointer persistent**: cân nhắc thay `InMemorySaver` bằng `PostgresSaver` nếu muốn giữ lịch sử hội thoại qua nhiều lần chạy chương trình.
- [ ] **Đặt lại tên hàm/tool**: `add_infomation`, `get_infomation`, `update_infomation` đang bị lỗi chính tả ("infomation" → "information") — nên sửa cho chuyên nghiệp, đặc biệt nếu expose ra ngoài như một API/tool công khai.
- [ ] **Xử lý lỗi output**: dòng `result["messages"][-1].content[0]['text']` trong `index.py` giả định cấu trúc response cố định — nên thêm try/except để tránh crash khi model trả về định dạng khác (ví dụ chỉ có tool_call, không có text).
- [ ] **`.gitignore`**: nhớ loại trừ `venv/`, `.env`, `__pycache__/`, và các file credential OAuth mà MCP server Gmail/Calendar sinh ra khi autoauth.

---

## Đóng góp

Pull request/issue đều được hoan nghênh. Nếu muốn mở rộng thêm MCP server khác (Notion, Slack, Todoist...), chỉ cần thêm cấu hình vào `mcp_client` trong `tool.py` và cập nhật `system_prompt` cho phù hợp.

---

## License

MIT License — tự do sử dụng, chỉnh sửa, phân phối. Thêm file `LICENSE` vào repo nếu muốn công bố chính thức.
