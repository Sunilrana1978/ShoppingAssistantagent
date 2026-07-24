import unittest
import sys
from pathlib import Path

# Add root directory to sys.path
root = Path(__file__).parent.parent
sys.path.insert(0, str(root))

from services.user_service import user_service
from services.discount_service import discount_service
from services.catalog_service import catalog_service
from services.cart_service import cart_service
from services.feedback_service import feedback_service
from tools.get_user_profile import get_user_profile
from tools.get_discount import get_discount
from tools.search_catalog import search_catalog
from tools.add_to_cart import add_to_cart
from tools.get_cart import get_cart
from tools.submit_feedback import submit_feedback
from callbacks.after_tool import after_tool_callback

class TestMultiAgentSystem(unittest.TestCase):

    def test_user_and_discount_services(self):
        profile = user_service.get_user_profile("u_1029")
        self.assertEqual(profile["name"], "Alex")
        self.assertEqual(profile["membership_tier"], "gold")

        discount = discount_service.get_discount_percentage("gold")
        self.assertEqual(discount, 15)

    def test_catalog_search(self):
        results = catalog_service.search(query="trail running", category="shoes")
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0]["sku"], "sku_1029")

    def test_cart_service_and_discount_math(self):
        session_id = "test_sess_001"
        cart_service.add_item(session_id, "sku_1029", qty=1, size=10)
        cart = cart_service.update_cart_pricing(session_id, discount_pct=15)
        self.assertEqual(cart["subtotal"], 129.99)
        self.assertEqual(cart["discount_amount"], 19.50)
        self.assertEqual(cart["total"], 110.49)

    def test_feedback_service_and_tool(self):
        res = submit_feedback(user_id="u_1029", rating=5, comments="Excellent service!")
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["rating"], 5)
        self.assertTrue(res["feedback_id"].startswith("fb_"))

        user_fb = feedback_service.get_user_feedback("u_1029")
        self.assertGreaterEqual(len(user_fb), 1)

if __name__ == "__main__":
    unittest.main()
