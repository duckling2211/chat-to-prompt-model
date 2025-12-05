# handlers/money_handler.py

import re
from typing import Dict, Any
from chat_project.core.cost import get_payment_system
from chat_project.core.info_hub import get_info_hub
from chat_project.core.base import PaymentBaseHandler, CommandResponse, ActionType, BaseCommandHandler


class MoneyTransactionHandler(PaymentBaseHandler):
    COMMAND_PREFIX = "/tiền"
    REGEX_PATTERN = r'^/tiền\s+(?P<person_a>\w+)\s+(?P<raw_details>.+)'

    def execute(self, params: Dict[str, Any], group_id: str) -> CommandResponse:
        # Lấy hệ thống thanh toán cho group này
        payment_sys = get_payment_system(group_id)  # <--- GỌI SYSTEM

        person_a = params['person_a']
        raw_details = params['raw_details']

        # ... (Logic Regex parse giữ nguyên) ...
        import re
        owe_match = re.match(r'(?:nợ|thiếu|chịu)\s+(?P<person_b>\w+)\s+(?P<debt_details>.*)', raw_details,
                             re.IGNORECASE)
        pay_match = re.match(r'(?:trả|thanh toán)\s+(?P<person_b>\w+)\s+(?P<debt_details>.*)', raw_details,
                             re.IGNORECASE)

        if owe_match:
            left, right = person_a, owe_match.group('person_b')
            details = owe_match.group('debt_details')
            transaction_type = "owe"
            # Logic: left nợ right -> update(left, right, amount)
            multiplier = 1
        elif pay_match:
            left, right = person_a, pay_match.group('person_b')
            details = pay_match.group('debt_details')
            transaction_type = "pay"
            # Logic: left trả right -> update(left, right, -amount) để giảm nợ
            multiplier = -1
        else:
            return CommandResponse(message="Lỗi format...", objects=[], action_type=ActionType.ERROR)

        amount_str, content = self._parse_debt_content(details)
        if not amount_str: return CommandResponse(message="Thiếu số tiền", objects=[], action_type=ActionType.ERROR)

        amount = self._parse_amount(amount_str)
        final_amount = amount * multiplier

        # --- GỌI CORE COST ---
        try:
            # Cập nhật vào hệ thống
            payment_sys.update(left, right, final_amount)

            # (Tùy chọn) Chạy tối ưu hóa ngay lập tức
            payment_sys.optimized_payment_process()

            # Lấy thông tin nợ hiện tại để trả về
            debts = payment_sys.get_member_debts(left)
        except Exception as e:
            return CommandResponse(message=f"Lỗi hệ thống: {e}", objects=[], action_type=ActionType.ERROR)

        # Tạo phản hồi
        msg = f"Ghi nhận: {left} {'nợ' if transaction_type == 'owe' else 'trả'} {right} {amount:,.0f}."
        if content: msg += f" ({content})"

        return CommandResponse(
            message=msg,
            objects=[{'left': left, 'right': right, 'amount': amount, 'current_debts': debts}],
            action_type=ActionType.PAYMENT
        )


class PaymentStatusHandler(PaymentBaseHandler):
    COMMAND_PREFIX = "/trạng-thái-tiền"
    REGEX_PATTERN = r'^/trạng-thái-tiền'

    def execute(self, params: Dict[str, Any], group_id: str) -> CommandResponse:
        payment_sys = get_payment_system(group_id)

        # Lấy nợ gốc và nợ tối ưu
        original = payment_sys.get_total_debts('original')
        optimized = payment_sys.optimized_payment_process()  # Tính toán tối ưu real-time

        return CommandResponse(
            message=f"Đã cập nhật trạng thái nợ cho nhóm {group_id}.",
            objects=[{'original': original, 'optimized': optimized}],
            action_type=ActionType.INFO
        )


class InfoAddHandler(BaseCommandHandler):
    COMMAND_PREFIX = "/thêm-thông-tin"
    ACTION_TYPE = ActionType.INFO
    REGEX_PATTERN = r'^/thêm-thông-tin\s+(?P<title>.+?)\s*\|\s*(?P<content>.+)'

    def execute(self, params: Dict[str, Any], group_id: str) -> CommandResponse:
        info_hub = get_info_hub(group_id)  # <--- GỌI SYSTEM

        title = params['title'].strip()
        content = params['content'].strip()

        # Thêm vào Hub
        doc_id = info_hub.add_document(title, content)

        return CommandResponse(
            message=f"Đã lưu thông tin (ID: {doc_id}): {title}",
            objects=[{'id': doc_id, 'title': title}],
            action_type=ActionType.INFO
        )


class InfoFindHandler(BaseCommandHandler):
    COMMAND_PREFIX = "/tìm-thông-tin"
    ACTION_TYPE = ActionType.INFO
    REGEX_PATTERN = r'^/tìm-thông-tin\s+(?P<search_query>.+)'

    def execute(self, params: Dict[str, Any], group_id: str) -> CommandResponse:
        info_hub = get_info_hub(group_id)  # <--- GỌI SYSTEM

        query = params['search_query']

        # Tìm kiếm
        results = info_hub.search(query)

        # Format kết quả
        if not results:
            msg = f"Không tìm thấy kết quả nào cho '{query}'."
            res_objs = []
        else:
            msg = f"Tìm thấy {len(results)} kết quả cho '{query}':"
            res_objs = [{'id': r.id, 'title': r.title, 'content': r.content} for r in results]

        return CommandResponse(
            message=msg,
            objects=res_objs,
            action_type=ActionType.INFO
        )