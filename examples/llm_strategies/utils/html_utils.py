"""HTML processing utilities for LLM strategies examples."""

import html2text
from bs4 import BeautifulSoup
from markdownify import markdownify as md


def count_tokens_approximate(text: str) -> int:
    """Approximate token count (1 token ≈ 4 characters)."""
    return len(text) // 4


def html_to_markdown_html2text(html: str) -> str:
    """Convert HTML to Markdown using html2text."""
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = False
    h.ignore_emphasis = False
    h.body_width = 0  # Don't wrap lines
    return h.handle(html)


def html_to_markdown_markdownify(html: str, strip_tags: list[str] | None = None) -> str:
    """Convert HTML to Markdown using markdownify."""
    if strip_tags is None:
        strip_tags = ["script", "style", "meta", "link", "noscript"]
    return md(html, strip=strip_tags)


def remove_attributes(html: str, keep_attrs: list[str] | None = None) -> str:
    """Remove all attributes from HTML except those specified."""
    if keep_attrs is None:
        keep_attrs = ["id", "class", "href", "src", "alt", "title"]

    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all():
        attrs_to_remove = []
        for attr in tag.attrs:
            if attr not in keep_attrs:
                attrs_to_remove.append(attr)
        for attr in attrs_to_remove:
            del tag[attr]

    return str(soup)


def extract_visible_text(html: str) -> str:
    """Extract only visible text from HTML."""
    soup = BeautifulSoup(html, "html.parser")

    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()

    # Get text and clean it
    text = soup.get_text()
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    return " ".join(chunk for chunk in chunks if chunk)


def truncate_html_middle(html: str, max_tokens: int = 4000) -> str:
    """Truncate HTML from the middle, keeping beginning and end."""
    tokens = count_tokens_approximate(html)

    if tokens <= max_tokens:
        return html

    # Calculate how many characters to keep
    chars_to_keep = max_tokens * 4
    keep_each_side = chars_to_keep // 2

    return html[:keep_each_side] + "\n\n[... TRUNCATED ...]\n\n" + html[-keep_each_side:]


def get_html_stats(html: str) -> dict[str, int]:
    """Get statistics about HTML content."""
    soup = BeautifulSoup(html, "html.parser")

    return {
        "total_chars": len(html),
        "approx_tokens": count_tokens_approximate(html),
        "total_tags": len(soup.find_all()),
        "links": len(soup.find_all("a")),
        "forms": len(soup.find_all("form")),
        "inputs": len(soup.find_all("input")),
        "buttons": len(soup.find_all("button")),
        "images": len(soup.find_all("img")),
        "scripts": len(soup.find_all("script")),
        "styles": len(soup.find_all("style")),
    }


def compare_processing_methods(html: str) -> dict[str, dict[str, int]]:
    """Compare different HTML processing methods."""
    results = {}

    # Original
    results["original"] = {"chars": len(html), "tokens": count_tokens_approximate(html)}

    # Plain text
    plain = extract_visible_text(html)
    results["plain_text"] = {"chars": len(plain), "tokens": count_tokens_approximate(plain)}

    # Markdown (html2text)
    md_h2t = html_to_markdown_html2text(html)
    results["markdown_html2text"] = {
        "chars": len(md_h2t),
        "tokens": count_tokens_approximate(md_h2t),
    }

    # Markdown (markdownify)
    md_mdf = html_to_markdown_markdownify(html)
    results["markdown_markdownify"] = {
        "chars": len(md_mdf),
        "tokens": count_tokens_approximate(md_mdf),
    }

    # Attributes removed
    no_attrs = remove_attributes(html)
    results["attributes_removed"] = {
        "chars": len(no_attrs),
        "tokens": count_tokens_approximate(no_attrs),
    }

    return results


# Sample HTML for testing
SAMPLE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Sample E-commerce Page</title>
    <style>
        .product { margin: 20px; }
        .price { color: red; font-weight: bold; }
    </style>
    <script>
        console.log("Analytics script");
    </script>
</head>
<body>
    <nav>
        <ul>
            <li><a href="/">Home</a></li>
            <li><a href="/products">Products</a></li>
            <li><a href="/about">About</a></li>
        </ul>
    </nav>
    
    <main>
        <h1>Premium Wireless Headphones</h1>
        <div class="product" data-product-id="12345">
            <img src="/images/headphones.jpg" alt="Wireless headphones">
            <p class="description">
                Experience crystal-clear audio with our premium wireless headphones.
                Features include active noise cancellation, 30-hour battery life,
                and comfortable over-ear design.
            </p>
            <p class="price">$299.99</p>
            <form action="/cart/add" method="post">
                <input type="hidden" name="product_id" value="12345">
                <label for="quantity">Quantity:</label>
                <input type="number" id="quantity" name="quantity" value="1" min="1">
                <button type="submit">Add to Cart</button>
            </form>
        </div>
    </main>
    
    <footer>
        <p>&copy; 2024 Example Store. All rights reserved.</p>
    </footer>
</body>
</html>
"""
