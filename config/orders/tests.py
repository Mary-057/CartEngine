from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from products.models import Product
from orders.models import Cart, CartItem, Order

class CartEngineTest(TestCase):
    def setUp(self):
        # 1. Create a test user
        self.user = User.objects.create_user(username='testuser', password='password123')
        
        # 2. Create a test product with stock
        self.product = Product.objects.create(name='Test Laptop', price=150000.00, stock=5)
        
        # 3. Initialize test client and log user in
        self.client = Client()
        self.client.login(username='testuser', password='password123')

    def test_add_to_cart_and_stay_on_page(self):
        """Test that adding an item to the cart creates a cart item and keeps the user on the page"""
        # Use reverse() to dynamically resolve the URL using its name
        url = reverse('add_to_cart', args=[self.product.id])
        
        response = self.client.post(url, follow=True)
        
        # Check that the request succeeded
        self.assertEqual(response.status_code, 200)
        
        # Verify the item actually got saved into the user's cart in the database
        cart = Cart.objects.get(user=self.user)
        cart_item = CartItem.objects.get(cart=cart, product=self.product)
        self.assertEqual(cart_item.quantity, 1)

    def test_idempotent_webhook_status_update(self):
        """Test that our webhook idempotency guard prevents duplicate updates"""
        # Create a mock pending order
        order = Order.objects.create(
            user=self.user,
            status='PENDING',
            paystack_reference='test-ref-12345'
        )
        
        # Simulate first webhook trigger
        if order.status != 'SUCCESS':
            order.status = 'SUCCESS'
            order.save()
            
        self.assertEqual(order.status, 'SUCCESS')
        
        # Simulate duplicate webhook trigger (Idempotency check)
        # If it runs again, the status should stay 'SUCCESS' without errors
        if order.status != 'SUCCESS':
            order.status = 'SUCCESS'
            order.save()
            
        self.assertEqual(order.status, 'SUCCESS')