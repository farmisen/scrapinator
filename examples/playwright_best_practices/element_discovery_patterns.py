"""
Element Discovery Patterns for Playwright

This module demonstrates best practices for discovering and interacting with
elements, including shadow DOM, iframes, and dynamic content handling.
"""

import asyncio
from dataclasses import dataclass
from typing import Any

from playwright.async_api import Locator, Page, async_playwright


@dataclass
class ElementInfo:
    """Information about a discovered element"""

    selector: str
    text: str
    tag_name: str
    attributes: dict[str, str]
    is_visible: bool
    is_enabled: bool
    bounding_box: dict[str, float] | None


class ElementDiscovery:
    """Advanced element discovery patterns"""

    @staticmethod
    async def discover_interactive_elements(page: Page) -> dict[str, list[ElementInfo]]:
        """Discover all interactive elements on a page"""

        # Define selectors for different element types
        element_queries = {
            "buttons": "button, [role='button'], input[type='submit'], input[type='button']",
            "links": "a[href]",
            "inputs": "input:not([type='hidden']), textarea, select",
            "clickable": "[onclick], [data-click], [data-action]",
            "forms": "form",
        }

        discovered_elements = {}

        for element_type, selector in element_queries.items():
            elements = await page.locator(selector).all()
            element_infos = []

            for element in elements[:10]:  # Limit to first 10 of each type
                try:
                    # Get element information
                    info = await page.evaluate(
                        """
                        (element) => {
                            const rect = element.getBoundingClientRect();
                            return {
                                tagName: element.tagName.toLowerCase(),
                                text: element.textContent?.trim() || '',
                                attributes: Object.fromEntries(
                                    Array.from(element.attributes).map(attr => [attr.name, attr.value])
                                ),
                                isVisible: rect.width > 0 && rect.height > 0,
                                isEnabled: !element.disabled,
                                boundingBox: {
                                    x: rect.x,
                                    y: rect.y,
                                    width: rect.width,
                                    height: rect.height
                                }
                            };
                        }
                    """,
                        element,
                    )

                    element_infos.append(
                        ElementInfo(
                            selector=selector,
                            text=info["text"],
                            tag_name=info["tagName"],
                            attributes=info["attributes"],
                            is_visible=info["isVisible"],
                            is_enabled=info["isEnabled"],
                            bounding_box=info["boundingBox"],
                        )
                    )
                except:
                    continue

            discovered_elements[element_type] = element_infos

        return discovered_elements

    @staticmethod
    async def handle_shadow_dom(page: Page) -> list[str]:
        """Demonstrate shadow DOM handling"""

        # Example: Find all elements inside shadow roots
        shadow_content = await page.evaluate("""
            () => {
                const results = [];
                
                // Function to traverse shadow DOM
                function traverseShadowDOM(root, path = '') {
                    const shadowHosts = root.querySelectorAll('*');
                    
                    shadowHosts.forEach(host => {
                        if (host.shadowRoot) {
                            const shadowPath = path + ' >>> ' + host.tagName.toLowerCase();
                            
                            // Find interactive elements in shadow root
                            const buttons = host.shadowRoot.querySelectorAll('button, [role="button"]');
                            const inputs = host.shadowRoot.querySelectorAll('input, textarea');
                            
                            buttons.forEach(btn => {
                                results.push({
                                    type: 'button',
                                    path: shadowPath + ' >>> button',
                                    text: btn.textContent?.trim() || ''
                                });
                            });
                            
                            inputs.forEach(input => {
                                results.push({
                                    type: 'input',
                                    path: shadowPath + ' >>> ' + input.tagName.toLowerCase(),
                                    placeholder: input.placeholder || ''
                                });
                            });
                            
                            // Recursively traverse nested shadow roots
                            traverseShadowDOM(host.shadowRoot, shadowPath);
                        }
                    });
                }
                
                traverseShadowDOM(document);
                return results;
            }
        """)

        return shadow_content

    @staticmethod
    async def handle_iframes(page: Page) -> list[dict[str, Any]]:
        """Discover and interact with iframe content"""

        # Find all iframes
        iframe_info = []
        iframes = await page.locator("iframe, frame").all()

        for i, iframe in enumerate(iframes):
            try:
                # Get iframe attributes
                attrs = await iframe.evaluate("""
                    (element) => ({
                        src: element.src,
                        id: element.id,
                        name: element.name,
                        width: element.width,
                        height: element.height
                    })
                """)

                # Try to access iframe content
                frame_locator = page.frame_locator(f"iframe >> nth={i}")

                # Count elements inside iframe
                try:
                    button_count = await frame_locator.locator("button").count()
                    link_count = await frame_locator.locator("a").count()

                    attrs["content"] = {"buttons": button_count, "links": link_count}
                except:
                    attrs["content"] = "Could not access iframe content"

                iframe_info.append(attrs)
            except:
                continue

        return iframe_info

    @staticmethod
    async def find_by_multiple_strategies(
        page: Page, strategies: list[dict[str, Any]]
    ) -> Locator | None:
        """Find element using multiple fallback strategies"""

        for strategy in strategies:
            try:
                locator = None

                if strategy["type"] == "css":
                    locator = page.locator(strategy["value"])
                elif strategy["type"] == "text":
                    locator = page.get_by_text(
                        strategy["value"], exact=strategy.get("exact", False)
                    )
                elif strategy["type"] == "role":
                    locator = page.get_by_role(strategy["value"], name=strategy.get("name"))
                elif strategy["type"] == "xpath":
                    locator = page.locator(f"xpath={strategy['value']}")
                elif strategy["type"] == "data-testid":
                    locator = page.get_by_test_id(strategy["value"])

                if locator and await locator.count() > 0:
                    return locator.first

            except:
                continue

        return None

    @staticmethod
    async def handle_dynamic_content(page: Page, options: dict[str, Any] = None) -> dict[str, Any]:
        """Handle dynamically loaded content"""

        options = options or {}
        max_scroll_attempts = options.get("max_scroll_attempts", 5)
        scroll_delay = options.get("scroll_delay", 1000)

        results = {
            "initial_height": await page.evaluate("document.body.scrollHeight"),
            "items_loaded": [],
            "scroll_attempts": 0,
        }

        # Handle infinite scroll
        previous_height = 0
        for attempt in range(max_scroll_attempts):
            current_height = await page.evaluate("document.body.scrollHeight")

            if current_height == previous_height:
                break

            # Scroll to bottom
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(scroll_delay)

            # Check for newly loaded items
            item_count = await page.locator("[data-item], .item, article").count()
            results["items_loaded"].append(
                {"attempt": attempt + 1, "item_count": item_count, "page_height": current_height}
            )

            previous_height = current_height
            results["scroll_attempts"] = attempt + 1

        results["final_height"] = await page.evaluate("document.body.scrollHeight")
        return results

    @staticmethod
    async def smart_element_detection(page: Page) -> dict[str, list[str]]:
        """Detect common UI patterns and their selectors"""

        patterns = await page.evaluate("""
            () => {
                const patterns = {
                    navigation: [],
                    searchBoxes: [],
                    loginForms: [],
                    pagination: [],
                    modals: [],
                    cookieBanners: []
                };
                
                // Navigation patterns
                const navSelectors = ['nav', '[role="navigation"]', '.navigation', '#navigation', '.navbar', '.menu'];
                navSelectors.forEach(selector => {
                    if (document.querySelector(selector)) {
                        patterns.navigation.push(selector);
                    }
                });
                
                // Search box patterns
                const searchSelectors = [
                    'input[type="search"]',
                    'input[placeholder*="search" i]',
                    'input[name*="search" i]',
                    'input[id*="search" i]',
                    '[role="searchbox"]'
                ];
                searchSelectors.forEach(selector => {
                    if (document.querySelector(selector)) {
                        patterns.searchBoxes.push(selector);
                    }
                });
                
                // Login form patterns
                const loginSelectors = [
                    'form[action*="login" i]',
                    'form[action*="signin" i]',
                    '#login-form',
                    '.login-form',
                    '[data-testid*="login" i]'
                ];
                loginSelectors.forEach(selector => {
                    if (document.querySelector(selector)) {
                        patterns.loginForms.push(selector);
                    }
                });
                
                // Pagination patterns
                const paginationSelectors = [
                    '.pagination',
                    '[role="navigation"][aria-label*="pagination" i]',
                    '.page-numbers',
                    'nav[aria-label*="page" i]'
                ];
                paginationSelectors.forEach(selector => {
                    if (document.querySelector(selector)) {
                        patterns.pagination.push(selector);
                    }
                });
                
                // Modal patterns
                const modalSelectors = [
                    '[role="dialog"]',
                    '.modal',
                    '[aria-modal="true"]',
                    '.popup',
                    '.overlay'
                ];
                modalSelectors.forEach(selector => {
                    if (document.querySelector(selector)) {
                        patterns.modals.push(selector);
                    }
                });
                
                // Cookie banner patterns
                const cookieSelectors = [
                    '[class*="cookie" i]',
                    '[id*="cookie" i]',
                    '[class*="consent" i]',
                    '[id*="consent" i]',
                    '[class*="gdpr" i]'
                ];
                cookieSelectors.forEach(selector => {
                    const elements = document.querySelectorAll(selector);
                    elements.forEach(el => {
                        if (el.offsetHeight > 50 && el.textContent.toLowerCase().includes('cookie')) {
                            patterns.cookieBanners.push(selector);
                        }
                    });
                });
                
                return patterns;
            }
        """)

        return patterns


async def demonstrate_element_discovery():
    """Demonstrate various element discovery techniques"""

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            # Navigate to a test page
            await page.goto("https://example.com")

            discovery = ElementDiscovery()

            # 1. Discover interactive elements
            print("Discovering interactive elements...")
            elements = await discovery.discover_interactive_elements(page)
            for element_type, items in elements.items():
                print(f"\n{element_type.upper()}:")
                for item in items[:3]:  # Show first 3 of each type
                    print(f"  - {item.tag_name}: {item.text[:50] if item.text else 'No text'}")

            # 2. Detect common UI patterns
            print("\n\nDetecting UI patterns...")
            patterns = await discovery.smart_element_detection(page)
            for pattern_type, selectors in patterns.items():
                if selectors:
                    print(f"\n{pattern_type}: {', '.join(selectors[:3])}")

            # 3. Try multiple selection strategies
            print("\n\nTrying multiple selection strategies...")
            strategies = [
                {"type": "text", "value": "More information"},
                {"type": "css", "value": "a[href*='about']"},
                {"type": "xpath", "value": "//a[contains(@href, 'info')]"},
            ]

            element = await discovery.find_by_multiple_strategies(page, strategies)
            if element:
                print("Found element using fallback strategies")

        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(demonstrate_element_discovery())
