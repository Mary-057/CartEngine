from celery import shared_task
import logging
from orders.models import Order, Cart

logger = logging.getLogger(__name__)

@shared_task
def process_paystack_webhook_async(reference):
    """Background task to safely update order status and clear cart without blocking web traffic"""
    try:
        order = Order.objects.get(paystack_reference=reference)
        if order.status != 'SUCCESS':
            order.status = 'SUCCESS'
            order.save()
            Cart.objects.filter(user=order.user).delete()
            logger.info(f"Celery background worker successfully updated order {order.id} to SUCCESS.")
    except Order.DoesNotExist:
        logger.error(f"Celery background worker received webhook for unknown reference: {reference}")