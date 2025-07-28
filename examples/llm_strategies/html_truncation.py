#!/usr/bin/env python3
"""
Demonstrate different HTML truncation strategies for LLM processing.

This example shows various approaches to truncating large HTML documents
while preserving the most important information for analysis.
"""

import asyncio

from bs4 import BeautifulSoup

from utils.html_utils import count_tokens_approximate


def truncate_by_length(html: str, max_chars: int = 10000) -> str:
    """Simple truncation by character length."""
    if len(html) <= max_chars:
        return html
    return html[:max_chars] + "\n<!-- Truncated -->"


def truncate_middle_out(html: str, max_chars: int = 10000) -> str:
    """Keep beginning and end, remove middle content."""
    if len(html) <= max_chars:
        return html

    keep_each_side = max_chars // 2
    return html[:keep_each_side] + "\n<!-- Middle content removed -->\n" + html[-keep_each_side:]


def truncate_by_dom_depth(html: str, max_depth: int = 3) -> str:
    """Truncate by limiting DOM tree depth."""
    soup = BeautifulSoup(html, "html.parser")

    def limit_depth(element, current_depth=0):
        if current_depth >= max_depth:
            # Replace deep content with placeholder
            element.clear()
            element.string = "[Content truncated]"
            return

        for child in list(element.children):
            if hasattr(child, "children"):
                limit_depth(child, current_depth + 1)

    limit_depth(soup)
    return str(soup)


def truncate_keep_structure(html: str, max_tokens: int = 2000) -> str:
    """Keep document structure but truncate content within elements."""
    soup = BeautifulSoup(html, "html.parser")
    current_tokens = count_tokens_approximate(str(soup))

    if current_tokens <= max_tokens:
        return html

    # Priority elements to keep full content
    priority_tags = ["title", "h1", "h2", "h3", "button", "input", "select", "form"]

    # Truncate text in non-priority elements
    for element in soup.find_all(text=True):
        if element.parent.name not in priority_tags and len(element.strip()) > 100:
            element.replace_with(element[:50] + "...")

            # Check if we've reduced enough
            current_tokens = count_tokens_approximate(str(soup))
            if current_tokens <= max_tokens:
                break

    return str(soup)


def truncate_by_importance(html: str, max_tokens: int = 2000) -> str:
    """Smart truncation based on element importance for web automation."""
    soup = BeautifulSoup(html, "html.parser")

    # Define importance scores
    importance_scores = {
        "form": 10,
        "input": 9,
        "button": 9,
        "select": 9,
        "textarea": 9,
        "a": 7,
        "h1": 8,
        "h2": 7,
        "h3": 6,
        "nav": 8,
        "main": 8,
        "article": 6,
        "section": 5,
        "div": 3,
        "p": 4,
        "span": 2,
        "script": 0,
        "style": 0,
        "meta": 1,
    }

    # Extract and score all elements
    elements = []
    for elem in soup.find_all():
        score = importance_scores.get(elem.name, 1)
        # Boost score for elements with certain attributes
        if elem.get("id"):
            score += 2
        if elem.get("class") and any(
            c in str(elem.get("class")) for c in ["form", "search", "nav", "menu"]
        ):
            score += 2
        if elem.get("type") in ["submit", "button"]:
            score += 3

        elements.append((score, elem))

    # Sort by importance
    elements.sort(key=lambda x: x[0], reverse=True)

    # Build new document with most important elements
    new_soup = BeautifulSoup("<html><body></body></html>", "html.parser")
    body = new_soup.body
    current_tokens = 100  # Base tokens

    for score, elem in elements:
        elem_str = str(elem)
        elem_tokens = count_tokens_approximate(elem_str)

        if current_tokens + elem_tokens <= max_tokens:
            # Clone element to avoid modifying original
            cloned = BeautifulSoup(elem_str, "html.parser").find()
            if cloned:
                body.append(cloned)
                current_tokens += elem_tokens

    return str(new_soup)


def truncate_sliding_window(html: str, window_size: int = 5000, stride: int = 2500) -> list[str]:
    """Create overlapping windows for processing large documents."""
    windows = []

    for i in range(0, len(html), stride):
        window = html[i : i + window_size]
        # Ensure window ends at a tag boundary
        last_close = window.rfind(">")
        if last_close != -1 and last_close != len(window) - 1:
            window = window[: last_close + 1]
        windows.append(window)

        if i + window_size >= len(html):
            break

    return windows


def extract_key_sections(html: str) -> dict[str, str]:
    """Extract key sections separately for focused analysis."""
    soup = BeautifulSoup(html, "html.parser")

    sections = {"navigation": "", "forms": "", "main_content": "", "interactive_elements": ""}

    # Extract navigation
    nav_elements = soup.find_all(["nav", "header"])
    sections["navigation"] = "\n".join(str(elem) for elem in nav_elements)

    # Extract forms
    form_elements = soup.find_all("form")
    sections["forms"] = "\n".join(str(elem) for elem in form_elements)

    # Extract main content
    main = soup.find("main") or soup.find("article") or soup.find("div", class_="content")
    if main:
        sections["main_content"] = str(main)

    # Extract interactive elements
    interactive = soup.find_all(["button", "input", "select", "textarea", "a"])
    sections["interactive_elements"] = "\n".join(
        str(elem) for elem in interactive[:50]
    )  # Limit to 50

    return sections


# Large sample HTML for testing
LARGE_HTML = (
    """
<!DOCTYPE html>
<html lang="en">
<head>
    <title>Large E-commerce Site</title>
    <meta charset="UTF-8">
    """
    "<style>"
    + "body { font-family: Arial; } " * 100
    + "</style>"
    + """
</head>
<body>
    <header>
        <nav>
            <ul>
                """
    + "\n".join(f'<li><a href="/category{i}">Category {i}</a></li>' for i in range(20))
    + """
            </ul>
        </nav>
    </header>
    
    <main>
        <h1>Products</h1>
        """
    + "\n".join(
        f"""
        <div class="product" id="product-{i}">
            <h2>Product {i}</h2>
            <p>Description for product {i}. Lorem ipsum dolor sit amet, consectetur adipiscing elit. 
            Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.</p>
            <span class="price">${i * 10 + 99}</span>
            <button class="add-to-cart" data-product-id="{i}">Add to Cart</button>
        </div>
        """
        for i in range(100)
    )
    + """
        
        <form id="newsletter" action="/subscribe" method="post">
            <h3>Subscribe to Newsletter</h3>
            <input type="email" name="email" placeholder="Enter your email" required>
            <input type="checkbox" name="weekly" id="weekly">
            <label for="weekly">Weekly updates</label>
            <button type="submit">Subscribe</button>
        </form>
    </main>
    
    <footer>
        <p>Contact us at support@example.com</p>
        """
    + "\n".join(f'<a href="/legal/{item}">{item}</a>' for item in ["privacy", "terms", "cookies"])
    + """
    </footer>
</body>
</html>
"""
)


def demonstrate_truncation_strategies(html: str):
    """Demonstrate different truncation strategies."""
    results = {}
    original_tokens = count_tokens_approximate(html)

    print(f"\nOriginal HTML: {len(html):,} chars, ~{original_tokens:,} tokens")
    print("=" * 60)

    # 1. Simple length truncation
    print("\n1. Simple Length Truncation (10K chars)")
    truncated = truncate_by_length(html, 10000)
    tokens = count_tokens_approximate(truncated)
    print(f"   Result: {len(truncated):,} chars, ~{tokens:,} tokens")
    print("   Preserves: Beginning of document only")
    results["length_truncation"] = {"chars": len(truncated), "tokens": tokens}

    # 2. Middle-out truncation
    print("\n2. Middle-Out Truncation (10K chars)")
    truncated = truncate_middle_out(html, 10000)
    tokens = count_tokens_approximate(truncated)
    print(f"   Result: {len(truncated):,} chars, ~{tokens:,} tokens")
    print("   Preserves: Beginning and end of document")
    results["middle_out"] = {"chars": len(truncated), "tokens": tokens}

    # 3. DOM depth truncation
    print("\n3. DOM Depth Truncation (max depth: 3)")
    truncated = truncate_by_dom_depth(html, max_depth=3)
    tokens = count_tokens_approximate(truncated)
    print(f"   Result: {len(truncated):,} chars, ~{tokens:,} tokens")
    print("   Preserves: Shallow document structure")
    results["dom_depth"] = {"chars": len(truncated), "tokens": tokens}

    # 4. Structure-preserving truncation
    print("\n4. Structure-Preserving Truncation (2K tokens)")
    truncated = truncate_keep_structure(html, max_tokens=2000)
    tokens = count_tokens_approximate(truncated)
    print(f"   Result: {len(truncated):,} chars, ~{tokens:,} tokens")
    print("   Preserves: Document structure, important elements")
    results["keep_structure"] = {"chars": len(truncated), "tokens": tokens}

    # 5. Importance-based truncation
    print("\n5. Importance-Based Truncation (2K tokens)")
    truncated = truncate_by_importance(html, max_tokens=2000)
    tokens = count_tokens_approximate(truncated)
    print(f"   Result: {len(truncated):,} chars, ~{tokens:,} tokens")
    print("   Preserves: Most important elements for automation")
    results["importance_based"] = {"chars": len(truncated), "tokens": tokens}

    # 6. Section extraction
    print("\n6. Key Section Extraction")
    sections = extract_key_sections(html)
    total_chars = sum(len(s) for s in sections.values())
    total_tokens = sum(count_tokens_approximate(s) for s in sections.values())
    print(f"   Result: {total_chars:,} chars, ~{total_tokens:,} tokens")
    print(f"   Sections: {', '.join(sections.keys())}")
    results["section_extraction"] = {"chars": total_chars, "tokens": total_tokens}

    return results


def show_importance_based_sample(html: str):
    """Show what importance-based truncation preserves."""
    print("\n" + "=" * 60)
    print("IMPORTANCE-BASED TRUNCATION SAMPLE")
    print("=" * 60)

    truncated = truncate_by_importance(html, max_tokens=1000)
    soup = BeautifulSoup(truncated, "html.parser")

    print("\nPreserved elements:")
    print("-" * 40)

    # Count preserved elements by type
    element_counts = {}
    for elem in soup.find_all():
        tag = elem.name
        element_counts[tag] = element_counts.get(tag, 0) + 1

    for tag, count in sorted(element_counts.items(), key=lambda x: x[1], reverse=True):
        if tag not in ["html", "body"]:
            print(f"  {tag}: {count}")

    print("\nSample of preserved content:")
    print("-" * 40)
    print(truncated[:500] + "...")


async def main():
    """Run the HTML truncation demonstration."""
    print("HTML Truncation Strategies Demonstration")
    print("=" * 60)
    print("This example demonstrates various strategies for truncating")
    print("large HTML documents while preserving important information.\n")

    # Demonstrate strategies
    results = demonstrate_truncation_strategies(LARGE_HTML)

    # Show importance-based sample
    show_importance_based_sample(LARGE_HTML)

    # Demonstrate sliding window
    print("\n\n7. Sliding Window Approach")
    print("=" * 60)
    windows = truncate_sliding_window(LARGE_HTML, window_size=5000, stride=2500)
    print(f"Created {len(windows)} overlapping windows")
    print("Window size: 5000 chars, Stride: 2500 chars")
    print(f"Total coverage: {len(windows) * 2500 + 2500} chars")

    # Key findings
    print("\n\nKEY FINDINGS")
    print("=" * 60)
    print("1. Simple truncation loses important elements at the end")
    print("2. Middle-out preserves both navigation and footer")
    print("3. DOM depth limiting maintains structure overview")
    print("4. Importance-based truncation best for web automation")
    print("5. Section extraction allows focused analysis")
    print("6. Sliding windows enable processing of very large pages")
    print("\nRECOMMENDATION: Use importance-based truncation for web")
    print("automation tasks, with section extraction as a fallback.")


if __name__ == "__main__":
    asyncio.run(main())
