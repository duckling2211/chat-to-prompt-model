# processor.py

from typing import Dict, Any, Optional
# Import các models cơ bản
from core.base import CommandResponse, ActionType

# Import TẤT CẢ các Handlers
from handlers.handler import MoneyTransactionHandler, PaymentStatusHandler, InfoAddHandler, InfoFindHandler

# ... (nếu có các handlers khác)

# Danh sách các Handlers được đăng ký (theo thứ tự ưu tiên)
REGISTERED_HANDLERS = [
    MoneyTransactionHandler(),  # Xử lý /tiền
    PaymentStatusHandler(),  # Xử lý /trạng-thái-tiền
    InfoAddHandler(),  # Xử lý /thêm-thông-tin
    InfoFindHandler(),  # Xử lý /tìm-thông-tin
    # Thêm các handlers khác vào đây
]


def process_chat_command(user_input: str, group_id: str) -> CommandResponse:
    """
    Tìm Handler phù hợp với lệnh của người dùng và thực thi.
    """

    # 1. Kiểm tra Fallback (Nếu không phải lệnh)
    if not user_input.startswith('/'):
        return CommandResponse(
            message=f"Xin lỗi, tôi chỉ xử lý các lệnh bắt đầu bằng '/'.",
            objects={"original_message": user_input},
            action_type=ActionType.FALLBACK
        )

    # 2. Duyệt qua các Handlers đã đăng ký
    for handler in REGISTERED_HANDLERS:
        try:
            params = handler.match_and_parse(user_input)

            if params is not None:
                # Nếu khớp, thực thi Handler và trả về kết quả
                print(f"DEBUG: Found handler {handler.__class__.__name__} for '{user_input}'")
                return handler.execute(params, group_id)

        except Exception as e:
            # Ghi nhận lỗi và trả về phản hồi lỗi
            return CommandResponse(
                message=f"Lỗi khi thực thi lệnh {handler.COMMAND_PREFIX}: {e}",
                objects={"error": str(e)},
                action_type=ActionType.ERROR
            )

    # 3. Lệnh không tồn tại
    return CommandResponse(
        message=f"Lệnh '{user_input.split()[0]}' không được hỗ trợ.",
        objects={"command": user_input.split()[0]},
        action_type=ActionType.ERROR
    )