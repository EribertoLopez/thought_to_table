"""
Walmart Cart Integration
Handles browser automation for searching products and adding to cart.
"""
import os
import time
import json
from typing import Dict, List, Optional
from urllib.parse import quote
from dataclasses import dataclass, asdict

try:
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("Warning: Selenium not available. Install with: pip install undetected-chromedriver selenium")


@dataclass
class WalmartProduct:
    """Represents a Walmart product search result"""
    name: str
    price: str
    url: str
    item_id: Optional[str] = None
    in_stock: bool = True
    
    def to_dict(self):
        return asdict(self)


@dataclass 
class CartItem:
    """Represents an item to add to cart"""
    ingredient_name: str
    search_query: str
    quantity_needed: str
    product: Optional[WalmartProduct] = None
    added_to_cart: bool = False
    error: Optional[str] = None
    
    def to_dict(self):
        result = asdict(self)
        if self.product:
            result['product'] = self.product.to_dict()
        return result


class WalmartCart:
    """Handles Walmart browser automation for cart management"""
    
    def __init__(self, headless: bool = False):
        if not SELENIUM_AVAILABLE:
            raise ImportError("Selenium is required. Install with: pip install undetected-chromedriver selenium")
        
        self.driver = None
        self.headless = headless
        self.logged_in = False
        self.cart_items: List[CartItem] = []
        
    def _init_browser(self):
        """Initialize the browser"""
        if self.driver is not None:
            return
            
        options = uc.ChromeOptions()
        if self.headless:
            options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        self.driver = uc.Chrome(options=options)
        self.driver.maximize_window()
        
    def login(self, wait_for_manual: bool = True) -> bool:
        """
        Navigate to Walmart and optionally wait for manual login.
        
        Args:
            wait_for_manual: If True, pause for user to log in manually
            
        Returns:
            bool: True if login successful
        """
        self._init_browser()
        
        print("\n🛒 Opening Walmart...")
        self.driver.get("https://www.walmart.com")
        time.sleep(3)
        
        if wait_for_manual:
            print("\n" + "="*50)
            print("📱 Please log in to your Walmart account")
            print("   (Sign in button is in the top right)")
            print("="*50)
            input("\nPress ENTER when you're logged in... ")
            
        self.logged_in = True
        print("✅ Ready to shop!")
        return True
        
    def search_product(self, query: str, category: str = "") -> Optional[WalmartProduct]:
        """
        Search for a product on Walmart.
        
        Args:
            query: Search query string
            category: Optional category hint (produce, dairy, meat, etc.)
            
        Returns:
            WalmartProduct or None if not found
        """
        self._init_browser()
        
        # Optimize search query based on category
        if category.lower() == 'produce':
            search_query = f"fresh {query}"
        elif category.lower() == 'dairy':
            search_query = f"{query}"
        elif category.lower() == 'meat':
            search_query = f"fresh {query}"
        elif category.lower() == 'spices':
            search_query = f"{query} spice seasoning"
        else:
            search_query = query
            
        encoded_query = quote(search_query)
        url = f"https://www.walmart.com/search?q={encoded_query}"
        
        print(f"  🔍 Searching: {search_query}")
        self.driver.get(url)
        time.sleep(2)
        
        try:
            # Wait for product grid
            product_container = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-item-id]"))
            )
            
            # Extract product details
            product_name = self._get_text_safe(product_container, [
                "span[data-automation-id='product-title']",
                "[data-automation-id='product-title']",
                "span.normal",
            ])
            
            price = self._get_text_safe(product_container, [
                "[data-automation-id='product-price'] span.f2",
                "[data-automation-id='product-price']",
                "div[data-automation-id='product-price']",
                ".price-main",
            ])
            
            product_url = self._get_link_safe(product_container)
            item_id = product_container.get_attribute('data-item-id')
            
            if product_name:
                return WalmartProduct(
                    name=product_name,
                    price=price or "Price not found",
                    url=product_url or url,
                    item_id=item_id
                )
                
        except TimeoutException:
            print(f"  ⚠️ No results found for: {search_query}")
        except Exception as e:
            print(f"  ❌ Error searching: {e}")
            
        return None
    
    def _get_text_safe(self, element, selectors: List[str]) -> Optional[str]:
        """Try multiple selectors to get text"""
        for selector in selectors:
            try:
                el = element.find_element(By.CSS_SELECTOR, selector)
                text = el.text.strip()
                if text:
                    return text
            except:
                continue
        return None
        
    def _get_link_safe(self, element) -> Optional[str]:
        """Try to get product URL"""
        try:
            link = element.find_element(By.CSS_SELECTOR, "a[href*='/ip/']")
            return link.get_attribute('href')
        except:
            try:
                links = element.find_elements(By.TAG_NAME, "a")
                for link in links:
                    href = link.get_attribute('href')
                    if href and '/ip/' in href:
                        return href
            except:
                pass
        return None
    
    def add_to_cart(self, product: WalmartProduct) -> bool:
        """
        Add a product to the Walmart cart.
        
        Args:
            product: WalmartProduct to add
            
        Returns:
            bool: True if successfully added
        """
        self._init_browser()
        
        if not product.url or product.url == "URL not found":
            print(f"  ❌ No URL for product: {product.name}")
            return False
            
        print(f"  🛒 Adding to cart: {product.name[:50]}...")
        
        try:
            # Navigate to product page
            self.driver.get(product.url)
            time.sleep(2)
            
            # Try multiple Add to Cart button selectors
            add_button_selectors = [
                "button[data-automation-id='add-to-cart-button']",
                "button[data-testid='add-to-cart-btn']",
                "//button[contains(text(), 'Add to cart')]",
                "//button[contains(@aria-label, 'Add to cart')]",
            ]
            
            added = False
            for selector in add_button_selectors:
                try:
                    if selector.startswith("//"):
                        button = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                    else:
                        button = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                    button.click()
                    added = True
                    break
                except:
                    continue
                    
            if added:
                time.sleep(2)  # Wait for cart update
                print(f"  ✅ Added!")
                return True
            else:
                print(f"  ⚠️ Could not find Add to Cart button")
                return False
                
        except Exception as e:
            print(f"  ❌ Error adding to cart: {e}")
            return False
    
    def search_and_preview(self, ingredients: List[Dict]) -> List[CartItem]:
        """
        Search for all ingredients and return preview.
        Does NOT add to cart yet.
        
        Args:
            ingredients: List of ingredient dicts with name, amount, unit, category
            
        Returns:
            List of CartItem objects with search results
        """
        self._init_browser()
        self.cart_items = []
        
        print("\n" + "="*50)
        print("🔍 SEARCHING WALMART FOR INGREDIENTS")
        print("="*50)
        
        for ing in ingredients:
            name = ing.get('name', 'Unknown')
            amount = ing.get('amount', '')
            unit = ing.get('unit', '')
            category = ing.get('category', '')
            
            cart_item = CartItem(
                ingredient_name=name,
                search_query=name,
                quantity_needed=f"{amount} {unit}".strip()
            )
            
            print(f"\n📦 {name} ({cart_item.quantity_needed})")
            
            product = self.search_product(name, category)
            if product:
                cart_item.product = product
                print(f"  ✅ Found: {product.name[:60]}")
                print(f"     💰 {product.price}")
            else:
                cart_item.error = "Product not found"
                print(f"  ❌ Not found")
                
            self.cart_items.append(cart_item)
            time.sleep(1)  # Rate limiting
            
        return self.cart_items
    
    def add_all_to_cart(self, items: Optional[List[CartItem]] = None) -> Dict:
        """
        Add all found products to cart.
        
        Args:
            items: Optional list of CartItems. Uses self.cart_items if not provided.
            
        Returns:
            Summary dict with success/failure counts
        """
        items = items or self.cart_items
        
        if not items:
            return {"error": "No items to add"}
            
        print("\n" + "="*50)
        print("🛒 ADDING ITEMS TO CART")
        print("="*50)
        
        success = 0
        failed = 0
        
        for item in items:
            if not item.product:
                print(f"\n⏭️ Skipping {item.ingredient_name} (no product found)")
                failed += 1
                continue
                
            print(f"\n📦 {item.ingredient_name}")
            
            if self.add_to_cart(item.product):
                item.added_to_cart = True
                success += 1
            else:
                item.error = "Failed to add to cart"
                failed += 1
                
            time.sleep(2)  # Rate limiting
            
        print("\n" + "="*50)
        print(f"✅ Added: {success} items")
        print(f"❌ Failed: {failed} items")
        print("="*50)
        
        return {
            "success": success,
            "failed": failed,
            "items": [item.to_dict() for item in items]
        }
    
    def get_cart_preview(self) -> str:
        """Generate a formatted preview of items to add"""
        if not self.cart_items:
            return "No items searched yet."
            
        lines = [
            "🛒 **Shopping Cart Preview**",
            "",
        ]
        
        total_estimated = 0.0
        found = 0
        not_found = 0
        
        for item in self.cart_items:
            if item.product:
                found += 1
                # Try to parse price
                try:
                    price_str = item.product.price.replace('$', '').replace(',', '').split()[0]
                    price = float(price_str)
                    total_estimated += price
                except:
                    price = None
                    
                price_display = item.product.price if item.product.price else "Price N/A"
                lines.append(f"✅ **{item.ingredient_name}** ({item.quantity_needed})")
                lines.append(f"   → {item.product.name[:50]}")
                lines.append(f"   💰 {price_display}")
            else:
                not_found += 1
                lines.append(f"❌ **{item.ingredient_name}** ({item.quantity_needed})")
                lines.append(f"   → Not found on Walmart")
            lines.append("")
            
        lines.append("─" * 40)
        lines.append(f"📊 Found: {found} | Not found: {not_found}")
        if total_estimated > 0:
            lines.append(f"💰 Estimated total: ${total_estimated:.2f}")
            
        return "\n".join(lines)
    
    def cleanup(self):
        """Close browser and cleanup"""
        if self.driver:
            self.driver.quit()
            self.driver = None


def interactive_shopping(ingredients: List[Dict], auto_add: bool = False):
    """
    Interactive shopping flow with preview and confirmation.
    
    Args:
        ingredients: List of ingredient dicts
        auto_add: If True, skip confirmation and add directly
    """
    cart = WalmartCart()
    
    try:
        # Login first
        cart.login(wait_for_manual=True)
        
        # Search for all ingredients
        cart.search_and_preview(ingredients)
        
        # Show preview
        print("\n" + cart.get_cart_preview())
        
        if not auto_add:
            print("\n" + "="*50)
            response = input("Add these items to cart? (y/n): ").strip().lower()
            if response != 'y':
                print("Cancelled.")
                return None
                
        # Add to cart
        result = cart.add_all_to_cart()
        
        print("\n🎉 Shopping complete!")
        print("Check your Walmart cart to review and checkout.")
        
        return result
        
    finally:
        # Don't close browser so user can review cart
        print("\n💡 Browser left open so you can review your cart.")
        print("   Close it manually when done.")


if __name__ == "__main__":
    # Test with sample ingredients
    test_ingredients = [
        {"name": "chicken breast", "amount": "2", "unit": "lbs", "category": "meat"},
        {"name": "broccoli", "amount": "1", "unit": "head", "category": "produce"},
        {"name": "soy sauce", "amount": "1", "unit": "bottle", "category": "pantry"},
    ]
    
    print("🛒 Walmart Cart Test")
    print("="*50)
    
    result = interactive_shopping(test_ingredients)
    if result:
        print("\nResults:")
        print(json.dumps(result, indent=2))
