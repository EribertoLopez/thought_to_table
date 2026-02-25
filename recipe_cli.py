#!/usr/bin/env python3
"""
Recipe CLI - Scrape recipe URLs, scale ingredients, output to file with Walmart links.

Usage:
    python recipe_cli.py <url> [servings]
    
No API calls - uses recipe-scrapers library for parsing.
"""
import os
import sys
import re
import json
import urllib.parse
from datetime import datetime
from fractions import Fraction
from typing import Optional, Tuple

try:
    from recipe_scrapers import scrape_me
except ImportError:
    print("Error: recipe-scrapers not installed. Run: pip install recipe-scrapers")
    sys.exit(1)


def parse_amount(amount_str: str) -> Tuple[float, str]:
    """Parse amount string like '1 1/2' or '2.5' into float and remaining text."""
    if not amount_str:
        return 0, ""
    
    amount_str = amount_str.strip()
    
    # Handle unicode fractions
    unicode_fractions = {
        '½': 0.5, '⅓': 1/3, '⅔': 2/3, '¼': 0.25, '¾': 0.75,
        '⅕': 0.2, '⅖': 0.4, '⅗': 0.6, '⅘': 0.8,
        '⅙': 1/6, '⅚': 5/6, '⅛': 0.125, '⅜': 0.375, '⅝': 0.625, '⅞': 0.875
    }
    
    for char, val in unicode_fractions.items():
        if char in amount_str:
            # Check for whole number before fraction
            parts = amount_str.split(char)
            whole = 0
            if parts[0].strip():
                try:
                    whole = float(parts[0].strip())
                except ValueError:
                    pass
            return whole + val, parts[1].strip() if len(parts) > 1 else ""
    
    # Try to parse mixed fractions like "1 1/2"
    mixed_match = re.match(r'^(\d+)\s+(\d+)/(\d+)', amount_str)
    if mixed_match:
        whole = int(mixed_match.group(1))
        num = int(mixed_match.group(2))
        denom = int(mixed_match.group(3))
        remainder = amount_str[mixed_match.end():].strip()
        return whole + num / denom, remainder
    
    # Try simple fraction like "1/2"
    frac_match = re.match(r'^(\d+)/(\d+)', amount_str)
    if frac_match:
        num = int(frac_match.group(1))
        denom = int(frac_match.group(2))
        remainder = amount_str[frac_match.end():].strip()
        return num / denom, remainder
    
    # Try decimal or integer
    num_match = re.match(r'^(\d+\.?\d*)', amount_str)
    if num_match:
        remainder = amount_str[num_match.end():].strip()
        return float(num_match.group(1)), remainder
    
    return 0, amount_str


def format_amount(amount: float) -> str:
    """Format amount nicely (fractions for small values, decimals for larger)."""
    if amount == 0:
        return ""
    
    # Common fractions to display nicely
    fraction_map = {
        0.125: "⅛", 0.25: "¼", 0.333: "⅓", 0.375: "⅜",
        0.5: "½", 0.625: "⅝", 0.666: "⅔", 0.75: "¾", 0.875: "⅞"
    }
    
    whole = int(amount)
    frac = amount - whole
    
    # Check for close fraction matches
    for val, symbol in fraction_map.items():
        if abs(frac - val) < 0.05:
            if whole > 0:
                return f"{whole} {symbol}"
            return symbol
    
    # Round to reasonable precision
    if amount == int(amount):
        return str(int(amount))
    elif amount < 10:
        return f"{amount:.2g}"
    else:
        return str(round(amount, 1))


def parse_ingredient(ingredient: str) -> dict:
    """Parse ingredient string into components."""
    original = ingredient.strip()
    
    # Parse amount
    amount, rest = parse_amount(original)
    
    # Common units
    units = [
        'cups?', 'tablespoons?', 'tbsp', 'teaspoons?', 'tsp',
        'pounds?', 'lbs?', 'ounces?', 'oz', 'grams?', 'g',
        'kilograms?', 'kg', 'milliliters?', 'ml', 'liters?', 'l',
        'cloves?', 'heads?', 'bunche?s?', 'pieces?', 'slices?',
        'cans?', 'jars?', 'packages?', 'bags?', 'boxes?',
        'stalks?', 'sprigs?', 'pinch(?:es)?', 'dash(?:es)?',
        'small', 'medium', 'large', 'whole'
    ]
    
    unit = ""
    name = rest
    
    # Try to extract unit
    unit_pattern = r'^(' + '|'.join(units) + r')\.?\s+'
    unit_match = re.match(unit_pattern, rest, re.IGNORECASE)
    if unit_match:
        unit = unit_match.group(1).lower()
        name = rest[unit_match.end():].strip()
    
    # Clean up name - remove parenthetical notes for Walmart search
    search_name = re.sub(r'\([^)]*\)', '', name).strip()
    search_name = re.sub(r',.*$', '', search_name).strip()  # Remove after comma
    
    return {
        "original": original,
        "amount": amount,
        "unit": unit,
        "name": name,
        "search_name": search_name
    }


def walmart_link(ingredient_name: str) -> str:
    """Generate Walmart search URL for ingredient."""
    query = urllib.parse.quote(ingredient_name)
    return f"https://www.walmart.com/search?q={query}"


def scrape_recipe(url: str) -> dict:
    """Scrape recipe from URL using recipe-scrapers."""
    try:
        scraper = scrape_me(url)
        
        return {
            "success": True,
            "title": scraper.title(),
            "yields": scraper.yields(),
            "ingredients": scraper.ingredients(),
            "instructions": scraper.instructions(),
            "total_time": scraper.total_time(),
            "image": scraper.image(),
            "host": scraper.host(),
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def extract_servings(yields_str: str) -> int:
    """Extract number of servings from yields string."""
    if not yields_str:
        return 4  # Default
    
    match = re.search(r'(\d+)', yields_str)
    if match:
        return int(match.group(1))
    return 4


def generate_markdown(recipe: dict, scaled_ingredients: list, target_servings: int, url: str) -> str:
    """Generate markdown file content with table and Walmart links."""
    lines = [
        f"# {recipe['title']}",
        "",
        f"**Source:** [{recipe.get('host', 'Recipe')}]({url})",
        f"**Original Servings:** {recipe.get('yields', 'Unknown')}",
        f"**Scaled to:** {target_servings} servings",
    ]
    
    if recipe.get('total_time'):
        lines.append(f"**Total Time:** {recipe['total_time']} minutes")
    
    lines.extend([
        "",
        f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
        "",
        "---",
        "",
        "## Shopping List",
        "",
        "| Qty | Ingredient | Walmart |",
        "|-----|------------|---------|",
    ])
    
    for ing in scaled_ingredients:
        qty = format_amount(ing['scaled_amount'])
        if ing['unit']:
            qty = f"{qty} {ing['unit']}"
        
        name = ing['name']
        link = walmart_link(ing['search_name'])
        
        lines.append(f"| {qty} | {name} | [Buy]({link}) |")
    
    lines.extend([
        "",
        "---",
        "",
        "## Instructions",
        "",
    ])
    
    instructions = recipe.get('instructions', '')
    if instructions:
        # Split into numbered steps if not already
        steps = instructions.split('\n')
        for i, step in enumerate(steps, 1):
            step = step.strip()
            if step:
                # Remove existing numbering
                step = re.sub(r'^\d+[\.\)]\s*', '', step)
                lines.append(f"{i}. {step}")
                lines.append("")
    
    return '\n'.join(lines)


def process_recipe(url: str, servings: int = 7) -> dict:
    """Main function to process recipe URL."""
    
    # Scrape recipe
    recipe = scrape_recipe(url)
    if not recipe['success']:
        return {"success": False, "error": recipe['error']}
    
    # Parse original servings
    original_servings = extract_servings(recipe.get('yields', ''))
    scale_factor = servings / original_servings if original_servings > 0 else 1
    
    # Parse and scale ingredients
    scaled_ingredients = []
    for ing_str in recipe.get('ingredients', []):
        parsed = parse_ingredient(ing_str)
        parsed['scaled_amount'] = parsed['amount'] * scale_factor if parsed['amount'] > 0 else 0
        scaled_ingredients.append(parsed)
    
    # Generate markdown
    markdown = generate_markdown(recipe, scaled_ingredients, servings, url)
    
    # Create output filename
    safe_title = re.sub(r'[^\w\s-]', '', recipe['title']).strip().replace(' ', '_')[:50]
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    filename = f"recipe_{safe_title}_{timestamp}.md"
    output_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(output_dir, "recipes", filename)
    
    # Ensure recipes directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Write file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(markdown)
    
    return {
        "success": True,
        "title": recipe['title'],
        "original_servings": original_servings,
        "scaled_servings": servings,
        "ingredient_count": len(scaled_ingredients),
        "output_path": output_path,
        "filename": filename
    }


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ['-h', '--help']:
        print("Usage: python recipe_cli.py <url> [servings]")
        print("\nExample:")
        print("  python recipe_cli.py https://bonappetit.com/recipe/loaded-scalloped-potatoes 7")
        sys.exit(0 if '--help' in sys.argv else 1)
    
    url = sys.argv[1]
    servings = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 7
    
    result = process_recipe(url, servings)
    
    if result['success']:
        print(f"🍽️ **{result['title']}**")
        print(f"📊 Scaled from {result['original_servings']} → {result['scaled_servings']} servings")
        print(f"🛒 {result['ingredient_count']} ingredients")
        print(f"📄 Saved to: `{result['filename']}`")
        print(f"\nFull path: {result['output_path']}")
    else:
        print(f"❌ Error: {result['error']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
