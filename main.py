"""
Thought to Table - Recipe to Walmart Shopping List
Powered by Claude AI

Usage:
    python main.py                          # Interactive mode
    python main.py <recipe_url> [servings]  # Direct mode
"""
import os
import sys
import json
from typing import Dict, Optional
from bs4 import BeautifulSoup
import requests
import anthropic
from dotenv import load_dotenv

from walmart_cart import WalmartCart, interactive_shopping

load_dotenv()

MODELID = "claude-sonnet-4-20250514"


class RecipeAssistant:
    """
    Recipe Assistant that uses Claude to parse recipes and scale ingredients.
    """
    
    def __init__(self, num_meals: int = 7):
        """
        Initialize the Recipe Assistant.
        
        Args:
            num_meals: Number of servings to scale recipe for (default: 7)
        """
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment. Create a .env file with your key.")
            
        self.client = anthropic.Anthropic(api_key=api_key)
        self.servings_needed = num_meals
        self.recipe_data = None
        self.scaled_data = None
        
    def _call_claude(self, prompt: str) -> dict:
        """Make a Claude API call and return parsed JSON response"""
        response = self.client.messages.create(
            model=MODELID,
            max_tokens=4096,
            messages=[
                {
                    "role": "user",
                    "content": prompt + "\n\nRespond with valid JSON only, no markdown formatting or code blocks."
                }
            ]
        )
        
        text = response.content[0].text.strip()
        
        # Clean up potential markdown code blocks
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:])  # Remove first line
            if text.rstrip().endswith("```"):
                text = text.rstrip()[:-3]
        
        return json.loads(text.strip())

    def extract_recipe_text(self, recipe_url: str) -> str:
        """Extract text content from recipe URL"""
        print(f"📖 Fetching recipe from: {recipe_url}")
        
        response = requests.get(recipe_url, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
            
        return soup.get_text(separator='\n', strip=True)

    def parse_recipe(self, recipe_text: str) -> dict:
        """Use Claude to parse recipe ingredients"""
        print("🤖 Analyzing recipe with Claude...")
        
        prompt = f"""Analyze this recipe and extract structured information.

For each ingredient provide:
- name: Standard grocery term (e.g., "chicken breast" not "boneless skinless chicken breast halves")
- amount: Numerical quantity
- unit: Common unit (lb, oz, cup, tbsp, tsp, whole, bunch, head, clove, can)
- category: One of: produce, dairy, meat, seafood, pantry, spices, frozen, bakery
- notes: Any specifics (organic, fresh, canned, etc.)

Also extract:
- Recipe name
- Original servings
- Meal type (breakfast, lunch, dinner, snack, dessert)
- Estimated calories per serving
- Prep time and cook time if available

Recipe text:
{recipe_text[:8000]}

Return JSON with:
{{
    "recipe_name": "string",
    "original_servings": number,
    "meal_type": "string",
    "calories_per_serving": number,
    "prep_time_minutes": number or null,
    "cook_time_minutes": number or null,
    "ingredients": [
        {{"name": "string", "amount": number, "unit": "string", "category": "string", "notes": "string"}}
    ]
}}"""
        
        self.recipe_data = self._call_claude(prompt)
        return self.recipe_data

    def scale_recipe(self, recipe_data: Optional[dict] = None) -> dict:
        """Scale recipe ingredients for desired number of servings"""
        recipe_data = recipe_data or self.recipe_data
        if not recipe_data:
            raise ValueError("No recipe data. Call parse_recipe first.")
            
        print(f"📊 Scaling recipe for {self.servings_needed} servings...")
        
        prompt = f"""Scale this recipe from {recipe_data.get('original_servings', 4)} servings to {self.servings_needed} servings.

Recipe data:
{json.dumps(recipe_data, indent=2)}

Provide:
1. Scaled ingredients with adjusted amounts (rounded to practical quantities)
2. Shopping list optimized for grocery store (combine similar items, use common package sizes)
3. Storage tips for bulk ingredients
4. Estimated total cost (USD)

Return JSON with:
{{
    "recipe_name": "string",
    "scaled_servings": {self.servings_needed},
    "scaled_ingredients": [
        {{"name": "string", "amount": number, "unit": "string", "category": "string", "notes": "string"}}
    ],
    "shopping_list": [
        {{"name": "string", "amount": number, "unit": "string", "category": "string", "notes": "string", "estimated_price": number}}
    ],
    "storage_tips": {{"ingredient_name": "tip"}},
    "estimated_total_cost": number
}}

Round amounts to practical values (e.g., 1.75 lbs → 2 lbs, 0.33 cups → 1/3 cup).
Use common package sizes (1 lb, 16 oz, 1 gallon, etc.)."""

        self.scaled_data = self._call_claude(prompt)
        return self.scaled_data

    def process_recipe(self, recipe_url: str) -> dict:
        """
        Full pipeline: fetch → parse → scale.
        
        Args:
            recipe_url: URL of the recipe
            
        Returns:
            Dict with recipe_data and scaled_data
        """
        # Fetch and parse
        recipe_text = self.extract_recipe_text(recipe_url)
        self.parse_recipe(recipe_text)
        
        print(f"\n✅ Found: {self.recipe_data.get('recipe_name', 'Recipe')}")
        print(f"   Original servings: {self.recipe_data.get('original_servings', 'Unknown')}")
        print(f"   Ingredients: {len(self.recipe_data.get('ingredients', []))}")
        
        # Scale
        self.scale_recipe()
        
        return {
            "recipe_url": recipe_url,
            "recipe_data": self.recipe_data,
            "scaled_data": self.scaled_data
        }
    
    def get_shopping_list(self) -> list:
        """Get the shopping list from scaled data"""
        if not self.scaled_data:
            return []
        return self.scaled_data.get('shopping_list', [])
    
    def print_summary(self):
        """Print a formatted summary of the scaled recipe"""
        if not self.scaled_data:
            print("No recipe processed yet.")
            return
            
        sd = self.scaled_data
        
        print("\n" + "="*50)
        print(f"🍽️  {sd.get('recipe_name', 'Recipe')}")
        print(f"📊 Scaled for {sd.get('scaled_servings', self.servings_needed)} servings")
        print("="*50)
        
        print("\n📝 SHOPPING LIST:")
        print("-"*40)
        
        total = 0
        for item in sd.get('shopping_list', []):
            name = item.get('name', 'Unknown')
            amount = item.get('amount', '')
            unit = item.get('unit', '')
            price = item.get('estimated_price', 0)
            total += price
            
            price_str = f"~${price:.2f}" if price else ""
            print(f"  • {name}: {amount} {unit} {price_str}")
            
        print("-"*40)
        print(f"💰 Estimated Total: ${sd.get('estimated_total_cost', total):.2f}")
        
        if sd.get('storage_tips'):
            print("\n📦 STORAGE TIPS:")
            print("-"*40)
            for ingredient, tip in sd['storage_tips'].items():
                print(f"  • {ingredient}: {tip}")
                
    def save_results(self, filename: str = "recipe_results.json"):
        """Save results to JSON file"""
        results = {
            "recipe_data": self.recipe_data,
            "scaled_data": self.scaled_data
        }
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n💾 Results saved to {filename}")


def main():
    """Main entry point"""
    # Parse arguments
    if len(sys.argv) >= 2:
        recipe_url = sys.argv[1]
        servings = int(sys.argv[2]) if len(sys.argv) >= 3 else 7
    else:
        print("🍽️  THOUGHT TO TABLE")
        print("="*50)
        recipe_url = input("Enter recipe URL: ").strip()
        servings = input("Number of servings [7]: ").strip()
        servings = int(servings) if servings else 7
        
    if not recipe_url:
        print("Error: Recipe URL required")
        sys.exit(1)
        
    # Process recipe
    assistant = RecipeAssistant(num_meals=servings)
    
    try:
        assistant.process_recipe(recipe_url)
        assistant.print_summary()
        assistant.save_results()
        
        # Ask about Walmart shopping
        print("\n" + "="*50)
        response = input("🛒 Add items to Walmart cart? (y/n): ").strip().lower()
        
        if response == 'y':
            shopping_list = assistant.get_shopping_list()
            if shopping_list:
                result = interactive_shopping(shopping_list)
                if result:
                    # Save cart results
                    with open("walmart_cart_results.json", 'w') as f:
                        json.dump(result, f, indent=2)
                    print("\n💾 Cart results saved to walmart_cart_results.json")
            else:
                print("No shopping list available.")
        else:
            print("\n👋 Done! Use the shopping list to shop manually.")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
