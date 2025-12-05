# api.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any

# Import các thành phần của hệ thống
from chat_project.processor import process_chat_command
from chat_project.core.base import CommandResponse  # Cần thiết cho type hint

# 1. KHỞI TẠO APP
app = FastAPI(
    title="Chat Command Processor API",
    description="API xử lý các lệnh chat cho hệ thống quản lý nhóm (Nợ/Thông tin).",
    version="1.0.0"
)

# 2. CẤU HÌNH CORS (BẮT BUỘC CHO FE)
# Vì đây là môi trường test/bài tập lớp, ta cho phép tất cả các nguồn
origins = [
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],  # Cho phép GET, POST, v.v.
    allow_headers=["*"],  # Cho phép tất cả headers
)


# 3. ĐỊNH NGHĨA MODEL INPUT CHO SWAGGER (Tùy chọn, nhưng giúp tài liệu rõ ràng)
# Vì cấu trúc input đơn giản, ta dùng Dict[str, Any] và chú thích trong hàm
# Cấu trúc JSON dự kiến: {"user_input": "...", "group_id": "..."}

# 4. ENDPOINT CHÍNH
@app.post("/api/process_command", response_model=CommandResponse)
def handle_chat_command(request_data: Dict[str, str]) -> CommandResponse:
    """
    Xử lý lệnh chat từ người dùng, gọi bộ xử lý trung tâm (processor.py).

    - Yêu cầu JSON Body: {"user_input": "string", "group_id": "string"}
    - Phản hồi: CommandResponse (message, objects, action_type)
    """

    # Đảm bảo có đủ dữ liệu
    if 'user_input' not in request_data or 'group_id' not in request_data:
        raise HTTPException(
            status_code=400,
            detail="Thiếu trường 'user_input' hoặc 'group_id' trong yêu cầu."
        )

    user_input = request_data['user_input']
    group_id = request_data['group_id']

    # Gọi hàm xử lý chính
    try:
        response = process_chat_command(user_input, group_id)
        return response
    except Exception as e:
        # Xử lý lỗi hệ thống nếu processor thất bại
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi xử lý nội bộ: {str(e)}"
        )


# 5. ENDPOINT KIỂM TRA SỨC KHỎE (HEALTH CHECK)
@app.get("/")
def read_root():
    """Kiểm tra API có đang hoạt động hay không."""
    return {"status": "ok", "message": "Chat Command API is running!"}