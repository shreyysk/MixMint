from abc import ABC, abstractmethod

class PaymentGateway(ABC):
    """
    Abstract Base Class for all Payment Gateways in MixMint.
    """

    @abstractmethod
    def create_order(self, amount_paise, currency='INR', order_id=None, metadata=None):
        """
        Creates an order with the gateway.
        Returns: Dict containing redirect_url or order_id.
        """
        pass

    @abstractmethod
    def verify_payment(self, payload, signature):
        """
        Verifies the authenticity of a payment response.
        """
        pass

    @abstractmethod
    def get_payment_status(self, payment_id):
        """
        Checks the current status of a payment.
        """
        pass

    @abstractmethod
    def process_refund(self, transaction_id, amount_paise, reason=''):
        """
        Initiates a refund for a transaction.
        """
        pass

    @abstractmethod
    def create_subscription_order(self, dj_id, plan_type, amount_paise):
        """
        Creates a payment order for Pro Plan renewal.
        """
        pass

    @abstractmethod
    def create_overage_order(self, dj_id, overage_gb, amount_paise):
        """
        Creates a payment order for storage overage.
        """
        pass
