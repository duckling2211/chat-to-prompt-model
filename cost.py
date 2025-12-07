from collections import defaultdict
import heapq

_payment_system = {}
def get_payment_system(group_id:str):
    global _payment_system
    if group_id not in _payment_system:
        _payment_system[group_id] = FlexiblePaymentSystem(group_id)
    return _payment_system[group_id]

class FlexiblePaymentSystem:
    def __init__(self, group_id:str):
        # Use dictionaries instead of fixed-size matrices
        self.original_debts = defaultdict(lambda: defaultdict(float))
        self.optimized_debts = defaultdict(lambda: defaultdict(float))
        self.members = set()
        self.group_id = group_id
    
    def add_member(self, member_id):
        """Add a new member to the system - O(1)"""
        self.members.add(member_id)
    
    def remove_member(self, member_id):
        """Remove a member after settling their debts - O(n)"""
        if member_id not in self.members:
            return False
        
        # Check if member has zero net balance
        net_balance = self._get_net_balance(member_id, self.original_debts)
        if abs(net_balance) > 1e-9:  # Floating point tolerance
            raise ValueError(f"Cannot remove member {member_id} with non-zero net balance: {net_balance}")
        
        # Remove from members and clear all their debts
        self.members.remove(member_id)
        for other in list(self.original_debts[member_id].keys()):
            del self.original_debts[member_id][other]
            del self.original_debts[other][member_id]
        
        for other in list(self.optimized_debts[member_id].keys()):
            del self.optimized_debts[member_id][other]
            del self.optimized_debts[other][member_id]
        
        # Clean up empty entries
        if not self.original_debts[member_id]:
            del self.original_debts[member_id]
        if not self.optimized_debts[member_id]:
            del self.optimized_debts[member_id]
        
        return True
    
    def update(self, from_member, to_member, amount):
        """Update debt relationship - O(1)"""
        if from_member not in self.members:
            self.add_member(from_member)
        if to_member not in self.members:
            self.add_member(to_member)

        self.original_debts[from_member][to_member] += amount
    
    def _get_net_balance(self, member_id, debt_graph):
        """Calculate net balance for a member - O(n)"""
        net = 0.0
        # Money owed to this member
        for other in self.members:
            net += debt_graph[other].get(member_id, 0)
        # Money this member owes
        for other in self.members:
            net -= debt_graph[member_id].get(other, 0)
        return net
    
    def optimized_payment_process(self):
        """Compute optimized payments for current members - O(n log n)"""
        if not self.members:
            return {}
        
        # Calculate net balances
        net_balances = {}
        for member in self.members:
            net_balances[member] = self._get_net_balance(member, self.original_debts)
        
        # Separate debtors and creditors using max-heaps (negative values for max-heap)
        debtors = []
        creditors = []
        
        for member, balance in net_balances.items():
            if balance < -1e-9:  # Debtor (owes money)
                heapq.heappush(debtors, (balance, member))
            elif balance > 1e-9:  # Creditor (owed money)
                heapq.heappush(creditors, (-balance, member))  # Negative for max-heap
        
        # Clear optimized debts
        self.optimized_debts.clear()
        
        # Greedy settlement: largest debt with largest credit
        while debtors and creditors:
            # Get largest debtor (most negative)
            debt_amt, debtor = heapq.heappop(debtors)
            debt_amt = -debt_amt  # Convert back to positive
            
            # Get largest creditor (most positive)
            credit_amt, creditor = heapq.heappop(creditors)
            credit_amt = -credit_amt  # Convert back to positive
            
            settlement = min(debt_amt, credit_amt)
            
            # Record in optimized graph
            self.optimized_debts[debtor][creditor] = settlement
            
            # Update remaining amounts
            debt_amt -= settlement
            credit_amt -= settlement
            
            if debt_amt > 1e-9:
                heapq.heappush(debtors, (-debt_amt, debtor))
            if credit_amt > 1e-9:
                heapq.heappush(creditors, (-credit_amt, creditor))
        
        return self.optimized_debts
    
    def force_remove_member(self, member_id, settle_first=True):
        """Force remove a member by settling their debts with others"""
        if member_id not in self.members:
            return False
        
        if settle_first:
            # Automatically settle the member's debts before removal
            net_balance = self._get_net_balance(member_id, self.original_debts)
            
            if net_balance > 1e-9:  # Member is owed money
                # Find someone to pay this member
                for other in self.members:
                    if other != member_id:
                        self.original_debts[other][member_id] = net_balance
                        break
            elif net_balance < -1e-9:  # Member owes money
                # Find someone to receive from this member
                for other in self.members:
                    if other != member_id:
                        self.original_debts[member_id][other] = -net_balance
                        break
            
            # Re-optimize
            self.optimized_payment_process()
        
        return self.remove_member(member_id)
    
    def get_member_debts(self, member_id, graph_type='original'):
        """Get all debts for a specific member - O(n)"""
        graph = self.original_debts if graph_type == 'original' else self.optimized_debts
        return dict(graph[member_id])
    
    def get_total_debts(self, graph_type='original'):
        """Get complete debt graph - O(n²)"""
        graph = self.original_debts if graph_type == 'original' else self.optimized_debts
        return {member: dict(graph[member]) for member in self.members}