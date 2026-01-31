# 🪸 Thought to Table

**Recipe URL → Scaled Ingredients → Walmart Shopping Cart**

Take any recipe, scale it for meal prep, and automatically add ingredients to your Walmart cart.

## Features

- 📖 Extract ingredients from any recipe URL
- 🤖 AI-powered parsing with Claude
- 📊 Scale recipes for meal prep (1-30+ servings)
- 💰 Cost estimation
- 📦 Storage tips for bulk ingredients
- 🛒 **Automated Walmart cart integration**

## Quick Start

### 1. Setup

```bash
# Clone the repo
git clone https://github.com/coralsurfside/thought_to_table.git
cd thought_to_table

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure API key
cp .env.example .env
# Edit .env and add your Anthropic API key
```

### 2. Run

**Interactive mode:**
```bash
python main.py
```

**Direct mode:**
```bash
python main.py "https://www.bonappetit.com/recipe/loaded-scalloped-potatoes" 7
```

## Usage Flow

1. **Enter recipe URL** - Any recipe page (Bon Appétit, AllRecipes, NYT Cooking, etc.)
2. **Choose servings** - How many meals to prep for
3. **Review shopping list** - AI-generated list with estimated costs
4. **Add to Walmart cart** (optional):
   - Browser opens Walmart.com
   - Log in to your account
   - Script searches for each ingredient
   - Preview what will be added
   - Confirm to add items to cart
   - Review cart and checkout manually

## Example Output

```
🍽️  Loaded Scalloped Potatoes
📊 Scaled for 7 servings
══════════════════════════════════════════

📝 SHOPPING LIST:
────────────────────────────────────────
  • russet potatoes: 4 lbs ~$4.00
  • heavy cream: 2 cups ~$5.00
  • gruyere cheese: 8 oz ~$8.00
  • bacon: 1 lb ~$7.00
  • chives: 1 bunch ~$2.00
  • garlic: 1 head ~$0.50
────────────────────────────────────────
💰 Estimated Total: $26.50
```

## Files

| File | Description |
|------|-------------|
| `main.py` | Main recipe processing pipeline |
| `walmart_cart.py` | Walmart browser automation |
| `anthro_test.py` | Standalone Claude API test |
| `recipe_results.json` | Saved recipe analysis |
| `walmart_cart_results.json` | Cart operation results |

## API Reference

```python
from main import RecipeAssistant
from walmart_cart import WalmartCart, interactive_shopping

# Process a recipe
assistant = RecipeAssistant(num_meals=7)
result = assistant.process_recipe("https://example.com/recipe")
assistant.print_summary()

# Get shopping list
shopping_list = assistant.get_shopping_list()

# Add to Walmart (interactive)
interactive_shopping(shopping_list)

# Or use WalmartCart directly
cart = WalmartCart()
cart.login(wait_for_manual=True)
cart.search_and_preview(shopping_list)
print(cart.get_cart_preview())
cart.add_all_to_cart()
```

## Requirements

- Python 3.9+
- Chrome browser (for Walmart automation)
- Anthropic API key

## Environment Variables

```bash
ANTHROPIC_API_KEY=sk-ant-...  # Required
```

## Notes

- Walmart automation uses undetected-chromedriver to avoid bot detection
- Manual login required (script doesn't store credentials)
- Browser stays open after shopping so you can review cart
- Some products may not be found - check cart before checkout

## Roadmap

- [ ] Coral slash command integration (`/recipe <url> [servings]`)
- [ ] Template message preview for chat interfaces
- [ ] Support for other grocery stores (Instacart, Amazon Fresh)
- [ ] Recipe caching to avoid re-parsing

---

*Part of the Coral 🪸 toolkit*
