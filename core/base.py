# core/base.py

import re
from abc import ABC, abstractmethod
from typing import List, Any, Dict, Tuple
from dataclasses import dataclass
from enum import Enum


# ==================== DATA MODELS & CONSTANTS ====================

class ActionType(Enum):
    """Phân loại hành động để FE xử lý hiển thị."""
    PAYMENT = "payment"
    INFO = "information"
    ERROR = "error"
    FALLBACK = "fallback"


@dataclass
class CommandResponse:
    """Phản hồi tiêu chuẩn từ mọi Handler."""
    message: str
    objects: List[Any]
    action_type: ActionType


# ==================== ABSTRACT HANDLERS ====================

class BaseCommandHandler(ABC):
    """
    Lớp cơ sở cho mọi Command Handler.
    Mọi Handler mới phải kế thừa lớp này.
    """
    COMMAND_PREFIX: str = None
    REGEX_PATTERN: str = None
    ACTION_TYPE: ActionType = ActionType.FALLBACK

    @abstractmethod
    def execute(self, params: Dict[str, Any], group_id: int) -> CommandResponse:
        """
        Logic nghiệp vụ thực thi lệnh.
        Nhận group_id để đảm bảo tính Group-Specific.
        """
        pass


class PaymentBaseHandler(BaseCommandHandler):
    """Lớp cơ sở cho các lệnh liên quan đến Thanh toán."""
    ACTION_TYPE = ActionType.PAYMENT

    def _parse_amount(self, amount_str: str) -> float:
        """Phân tích chuỗi số tiền sang float, hỗ trợ k, K, nghìn, tr, triệu."""
        clean_amount = amount_str.lower().replace('.', '').replace(',', '')
        multiplier = 1.0

        if 'k' in clean_amount or 'nghìn' in clean_amount:
            multiplier = 1000.0
            clean_amount = clean_amount.replace('k', '').replace('nghìn', '')
        elif 'tr' in clean_amount or 'triệu' in clean_amount:
            multiplier = 1000000.0
            clean_amount = clean_amount.replace('tr', '').replace('triệu', '')

        try:
            amount = float(clean_amount)
            return amount * multiplier
        except ValueError:
            raise ValueError(f"Không thể phân tích số tiền từ chuỗi: {amount_str}")

    def _parse_debt_content(self, raw_text: str) -> Tuple[str, str]:
        """Trích xuất số tiền và nội dung (content)."""
        # Mẫu: [số tiền] [tùy chọn 'tiền'] [nội dung còn lại]
        pattern = r'(\d[\d\.,]*\s*(?:[kK]|nghìn|tr|triệu|))(?:\s+tiền)?\s*(.*)'
        match = re.search(pattern, raw_text, re.IGNORECASE)

        if match:
            amount_str = match.group(1).strip()
            content = match.group(2).strip()
            return amount_str, content

        return "", raw_text