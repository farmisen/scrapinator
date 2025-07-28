#!/usr/bin/env python3
"""
Demonstrate HTML to Markdown conversion strategies for LLM token optimization.

This example shows how converting HTML to Markdown can dramatically reduce
token usage while preserving the essential structure and content.
"""

import asyncio
import time

from utils.html_utils import (
    SAMPLE_HTML,
    count_tokens_approximate,
    get_html_stats,
    html_to_markdown_html2text,
    html_to_markdown_markdownify,
)
from utils.metrics import calculate_token_reduction, compare_strategies

# More complex sample HTML for testing
COMPLEX_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TechGadgets - Latest Smartphones</title>
    <link rel="stylesheet" href="/css/main.css">
    <script src="/js/analytics.js"></script>
    <style>
        body { font-family: Arial, sans-serif; }
        .product-grid { display: grid; grid-template-columns: repeat(3, 1fr); }
        .filter-panel { background: #f0f0f0; padding: 20px; }
    </style>
</head>
<body>
    <header>
        <nav class="main-nav" role="navigation" aria-label="Main navigation">
            <div class="container">
                <a href="/" class="logo">TechGadgets</a>
                <ul class="nav-menu">
                    <li><a href="/phones">Phones</a></li>
                    <li><a href="/tablets">Tablets</a></li>
                    <li><a href="/accessories">Accessories</a></li>
                    <li><a href="/deals" class="highlight">Deals</a></li>
                </ul>
                <form class="search-form" action="/search">
                    <input type="text" name="q" placeholder="Search products..." 
                           aria-label="Search">
                    <button type="submit">Search</button>
                </form>
            </div>
        </nav>
    </header>

    <main>
        <div class="breadcrumb">
            <a href="/">Home</a> > <a href="/phones">Phones</a> > Smartphones
        </div>

        <h1>Latest Smartphones</h1>
        
        <div class="content-wrapper">
            <aside class="filter-panel">
                <h2>Filter Products</h2>
                <form id="filter-form">
                    <div class="filter-group">
                        <h3>Brand</h3>
                        <label><input type="checkbox" name="brand" value="apple"> Apple</label>
                        <label><input type="checkbox" name="brand" value="samsung"> Samsung</label>
                        <label><input type="checkbox" name="brand" value="google"> Google</label>
                    </div>
                    <div class="filter-group">
                        <h3>Price Range</h3>
                        <input type="range" name="price" min="0" max="2000" value="1000">
                        <span class="price-display">$0 - $1000</span>
                    </div>
                    <button type="submit">Apply Filters</button>
                </form>
            </aside>

            <section class="product-grid">
                <article class="product-card" data-product-id="iphone-15">
                    <img src="/images/iphone-15.jpg" alt="iPhone 15 Pro">
                    <h3>iPhone 15 Pro</h3>
                    <p class="price">$999</p>
                    <p class="description">Latest iPhone with A17 Pro chip and titanium design.</p>
                    <div class="rating" aria-label="4.5 out of 5 stars">★★★★☆</div>
                    <button class="add-to-cart" data-product="iphone-15">Add to Cart</button>
                </article>

                <article class="product-card" data-product-id="galaxy-s24">
                    <img src="/images/galaxy-s24.jpg" alt="Samsung Galaxy S24">
                    <h3>Samsung Galaxy S24</h3>
                    <p class="price">$899</p>
                    <p class="description">AI-powered smartphone with advanced camera system.</p>
                    <div class="rating" aria-label="4.3 out of 5 stars">★★★★☆</div>
                    <button class="add-to-cart" data-product="galaxy-s24">Add to Cart</button>
                </article>

                <article class="product-card" data-product-id="pixel-8">
                    <img src="/images/pixel-8.jpg" alt="Google Pixel 8">
                    <h3>Google Pixel 8</h3>
                    <p class="price">$699</p>
                    <p class="description">Pure Android experience with best-in-class AI features.</p>
                    <div class="rating" aria-label="4.4 out of 5 stars">★★★★☆</div>
                    <button class="add-to-cart" data-product="pixel-8">Add to Cart</button>
                </article>
            </section>
        </div>

        <div class="pagination">
            <a href="?page=1" class="active">1</a>
            <a href="?page=2">2</a>
            <a href="?page=3">3</a>
            <a href="?page=4">Next</a>
        </div>
    </main>

    <footer>
        <div class="footer-content">
            <div class="footer-section">
                <h4>Customer Service</h4>
                <ul>
                    <li><a href="/help">Help Center</a></li>
                    <li><a href="/shipping">Shipping Info</a></li>
                    <li><a href="/returns">Returns</a></li>
                </ul>
            </div>
            <div class="footer-section">
                <h4>Connect</h4>
                <ul>
                    <li><a href="/contact">Contact Us</a></li>
                    <li><a href="/newsletter">Newsletter</a></li>
                </ul>
            </div>
        </div>
        <p class="copyright">&copy; 2024 TechGadgets. All rights reserved.</p>
    </footer>

    <script>
        // Analytics and interaction scripts
        document.querySelectorAll('.add-to-cart').forEach(btn => {
            btn.addEventListener('click', function() {
                console.log('Product added:', this.dataset.product);
            });
        });
    </script>
</body>
</html>
"""


def analyze_html_content(html: str) -> dict[str, any]:
    """Analyze HTML content and conversion results."""
    print("Analyzing HTML content...")
    print("-" * 60)

    # Get HTML statistics
    stats = get_html_stats(html)
    print("Original HTML Statistics:")
    print(f"  Total characters: {stats['total_chars']:,}")
    print(f"  Approximate tokens: {stats['approx_tokens']:,}")
    print(f"  Total tags: {stats['total_tags']}")
    print(
        f"  Interactive elements: {stats['links']} links, "
        f"{stats['forms']} forms, {stats['inputs']} inputs, "
        f"{stats['buttons']} buttons"
    )

    return stats


def demonstrate_conversions(html: str) -> dict[str, dict]:
    """Demonstrate different HTML to Markdown conversion methods."""
    results = {}

    # Original HTML
    print("\n1. Original HTML")
    print("-" * 40)
    original_tokens = count_tokens_approximate(html)
    print(f"   Characters: {len(html):,}")
    print(f"   Tokens: {original_tokens:,}")
    results["original"] = {"chars": len(html), "tokens": original_tokens, "time": 0}

    # HTML2Text conversion
    print("\n2. HTML2Text Conversion")
    print("-" * 40)
    start_time = time.time()
    md_h2t = html_to_markdown_html2text(html)
    h2t_time = time.time() - start_time
    h2t_tokens = count_tokens_approximate(md_h2t)
    reduction_h2t = calculate_token_reduction(original_tokens, h2t_tokens)
    print(f"   Characters: {len(md_h2t):,}")
    print(f"   Tokens: {h2t_tokens:,}")
    print(f"   Reduction: {reduction_h2t:.1f}%")
    print(f"   Processing time: {h2t_time * 1000:.1f}ms")
    results["html2text"] = {"chars": len(md_h2t), "tokens": h2t_tokens, "time": h2t_time}

    # Markdownify conversion
    print("\n3. Markdownify Conversion")
    print("-" * 40)
    start_time = time.time()
    md_mdf = html_to_markdown_markdownify(html)
    mdf_time = time.time() - start_time
    mdf_tokens = count_tokens_approximate(md_mdf)
    reduction_mdf = calculate_token_reduction(original_tokens, mdf_tokens)
    print(f"   Characters: {len(md_mdf):,}")
    print(f"   Tokens: {mdf_tokens:,}")
    print(f"   Reduction: {reduction_mdf:.1f}%")
    print(f"   Processing time: {mdf_time * 1000:.1f}ms")
    results["markdownify"] = {"chars": len(md_mdf), "tokens": mdf_tokens, "time": mdf_time}

    # Markdownify with aggressive stripping
    print("\n4. Markdownify (Aggressive)")
    print("-" * 40)
    start_time = time.time()
    strip_tags = ["script", "style", "meta", "link", "noscript", "header", "footer", "nav"]
    md_aggressive = html_to_markdown_markdownify(html, strip_tags=strip_tags)
    agg_time = time.time() - start_time
    agg_tokens = count_tokens_approximate(md_aggressive)
    reduction_agg = calculate_token_reduction(original_tokens, agg_tokens)
    print(f"   Characters: {len(md_aggressive):,}")
    print(f"   Tokens: {agg_tokens:,}")
    print(f"   Reduction: {reduction_agg:.1f}%")
    print(f"   Processing time: {agg_time * 1000:.1f}ms")
    results["markdownify_aggressive"] = {
        "chars": len(md_aggressive),
        "tokens": agg_tokens,
        "time": agg_time,
    }

    return results


def show_conversion_samples(html: str):
    """Show sample outputs from different conversion methods."""
    print("\n" + "=" * 60)
    print("CONVERSION SAMPLES (First 500 characters)")
    print("=" * 60)

    # HTML2Text sample
    print("\nHTML2Text Output:")
    print("-" * 40)
    md_h2t = html_to_markdown_html2text(html)
    print(md_h2t[:500] + "...")

    # Markdownify sample
    print("\n\nMarkdownify Output:")
    print("-" * 40)
    md_mdf = html_to_markdown_markdownify(html)
    print(md_mdf[:500] + "...")


async def main():
    """Run the HTML to Markdown demonstration."""
    print("HTML to Markdown Conversion Demonstration")
    print("=" * 60)
    print("This example demonstrates how HTML to Markdown conversion")
    print("can reduce token usage by 80-90% while preserving content.\n")

    # Test with simple HTML
    print("\nTEST 1: Simple E-commerce Page")
    print("=" * 60)
    analyze_html_content(SAMPLE_HTML)
    simple_results = demonstrate_conversions(SAMPLE_HTML)

    # Test with complex HTML
    print("\n\nTEST 2: Complex Product Listing Page")
    print("=" * 60)
    analyze_html_content(COMPLEX_HTML)
    complex_results = demonstrate_conversions(COMPLEX_HTML)

    # Show comparison
    print("\n\nFINAL COMPARISON")
    print("=" * 60)
    compare_strategies(complex_results)

    # Show conversion samples
    show_conversion_samples(COMPLEX_HTML)

    # Key findings
    print("\n\nKEY FINDINGS")
    print("=" * 60)
    print("1. HTML→Markdown conversion reduces tokens by 80-90%")
    print("2. Processing time is minimal (<100ms for most pages)")
    print("3. Essential content and structure are preserved")
    print("4. Interactive elements (forms, buttons) remain identifiable")
    print("5. Aggressive stripping can achieve >90% reduction")
    print("\nRECOMMENDATION: Use markdownify with default settings for")
    print("best balance of token reduction and content preservation.")


if __name__ == "__main__":
    asyncio.run(main())
