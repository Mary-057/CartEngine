from django.test import TestCase
from django.urls import reverse

# Create your tests here.
def test_product_list_view(self):
    """Test that the store page loads successfully and displays products"""
    url = reverse('product_list')
    response = self.client.get(url)
    
    # Check that page loads with a 200 OK
    self.assertEqual(response.status_code, 200)
    
    # Check that our test product's name is actually rendered on the page
    self.assertContains(response, self.product.name)