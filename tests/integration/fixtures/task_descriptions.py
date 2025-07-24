"""Test task descriptions for integration testing."""

# Simple tasks for basic functionality testing
SIMPLE_TASKS = [
    {
        "description": "Click the login button",
        "url": "https://example.com",
        "expected_objectives_count": 1,
        "expected_has_actions": True,
        "expected_has_data": False,
    },
    {
        "description": "Extract all product prices from the page",
        "url": "https://shop.example.com/products",
        "expected_objectives_count": 1,
        "expected_has_actions": False,
        "expected_has_data": True,
    },
    {
        "description": "Find and click the 'Contact Us' link in the footer",
        "url": "https://company.example.com",
        "expected_objectives_count": 2,  # Find link, click it
        "expected_has_actions": True,
        "expected_has_data": False,
    },
]

# Complex multi-step tasks
COMPLEX_TASKS = [
    {
        "description": (
            "Navigate to the electronics section, filter products by price range $50-$100, "
            "sort by customer rating, and extract the top 5 products with their names, "
            "prices, and ratings"
        ),
        "url": "https://ecommerce.example.com",
        "expected_min_objectives": 4,
        "expected_has_actions": True,
        "expected_has_data": True,
    },
    {
        "description": (
            "Log into the account using the provided credentials, navigate to user settings, "
            "change the email notification preferences to weekly digest, update the timezone "
            "to PST, and save all changes"
        ),
        "url": "https://app.example.com/login",
        "expected_min_objectives": 5,
        "expected_has_actions": True,
        "expected_has_data": False,
    },
    {
        "description": (
            "Search for 'wireless headphones', apply filters for brand (Sony or Bose), "
            "price under $200, and 4+ star ratings. Add the first three matching products "
            "to the shopping cart and proceed to checkout"
        ),
        "url": "https://marketplace.example.com",
        "expected_min_objectives": 5,
        "expected_has_actions": True,
        "expected_has_data": True,
    },
]

# Edge cases and challenging scenarios
EDGE_CASES = [
    {
        "description": "",  # Empty description
        "url": "https://example.com",
        "expected_error": False,  # Should still parse, but with minimal objectives
    },
    {
        "description": "Do something on the website",  # Vague description
        "url": "https://example.com",
        "expected_min_objectives": 1,
        "expected_vague": True,
    },
    {
        "description": (
            "This is an extremely long task description that contains multiple objectives "
            "and requirements. First, navigate to the main page and identify all navigation "
            "menu items. Document each menu item's text and URL. Then, for each main category, "
            "click into it and extract the subcategories. For each subcategory, count the number "
            "of products available. Create a hierarchical structure of the entire site navigation. "
            "Additionally, check if there are any promotional banners on each page, and if so, "
            "extract their text content and any associated discount codes. Look for a search bar "
            "and test it with the following queries: 'laptop', 'phone', 'tablet'. For each search, "
            "note how many results are returned. Find the customer service section and extract all "
            "contact methods available (phone, email, chat). Check if there's a FAQ section and "
            "count the number of FAQ items. Look for any social media links and compile a list. "
            "Navigate to the footer and extract all links present there, categorizing them by type "
            "(legal, informational, social). If there's a newsletter signup, locate it and note its "
            "position on the page. Check for accessibility features like font size adjusters or "
            "high contrast modes. Document the overall color scheme used on the website. Finally, "
            "test the site's responsiveness by checking how it appears on different screen sizes."
        ),
        "url": "https://complex.example.com",
        "expected_min_objectives": 10,
        "expected_complex": True,
    },
    {
        "description": (
            "Click the button that says 'Submit' but also don't click it if it's disabled"
        ),  # Contradictory instructions
        "url": "https://form.example.com",
        "expected_has_constraints": True,
    },
]

# Tasks for different categories
TASK_CATEGORIES = {
    "navigation": [
        "Navigate to the about page and then to the team section",
        "Go back to the previous page after clicking on a product",
        "Use the breadcrumb navigation to return to the home page",
    ],
    "data_extraction": [
        "Extract all email addresses from the contact page",
        "Get the business hours from the location page",
        "Collect all testimonial quotes and author names",
    ],
    "form_filling": [
        "Fill out the contact form with test data and submit",
        "Complete the newsletter signup with email test@example.com",
        "Fill the survey form selecting 'Very Satisfied' for all questions",
    ],
    "search": [
        "Search for 'blue widgets' and count the results",
        "Use the advanced search to find products between $10-$50",
        "Search for 'customer service' and click the first result",
    ],
    "interaction": [
        "Click all tabs in the product details section",
        "Expand all FAQ items and count them",
        "Toggle the dark mode switch and verify the theme changes",
    ],
}

# Performance test cases (for benchmarking)
PERFORMANCE_TASKS = [
    {
        "description": "Click the first button on the page",
        "url": "https://simple.example.com",
        "category": "simple",
        "expected_response_time": 2.0,  # seconds
    },
    {
        "description": (
            "Analyze the entire product catalog, categorize products by type, "
            "price range, and availability, then create a summary report"
        ),
        "url": "https://catalog.example.com",
        "category": "complex",
        "expected_response_time": 5.0,  # seconds
    },
]

def get_simple_task():
    """Get a simple task for basic testing."""
    return SIMPLE_TASKS[0]

def get_complex_task():
    """Get a complex task for advanced testing."""
    return COMPLEX_TASKS[0]

def get_all_tasks():
    """Get all test tasks."""
    return {
        "simple": SIMPLE_TASKS,
        "complex": COMPLEX_TASKS,
        "edge_cases": EDGE_CASES,
        "performance": PERFORMANCE_TASKS,
    }

def get_tasks_by_category(category: str):
    """Get tasks for a specific category."""
    return TASK_CATEGORIES.get(category, [])