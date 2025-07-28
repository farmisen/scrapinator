"""
Security Patterns for Playwright

This module demonstrates security best practices for web exploration,
including sandboxing, resource limits, and handling untrusted content.
"""

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import psutil
from playwright.async_api import Browser, BrowserContext, Page, async_playwright

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SecurityConfig:
    """Security configuration for browser instances"""

    trust_level: str = "untrusted"  # untrusted, semi-trusted, trusted
    enable_javascript: bool = True
    enable_images: bool = False
    enable_stylesheets: bool = False
    allow_downloads: bool = False
    allow_geolocation: bool = False
    allow_notifications: bool = False
    max_memory_mb: int = 1024
    max_cpu_percent: int = 80
    max_execution_time: int = 30  # seconds
    sandbox_mode: bool = True
    isolate_origins: bool = True


class ResourceMonitor:
    """Monitor and limit resource usage"""

    def __init__(self, config: SecurityConfig):
        self.config = config
        self.process = psutil.Process(os.getpid())
        self.start_time = time.time()
        self.violations = []

    async def check_limits(self) -> dict[str, Any]:
        """Check if resource usage is within limits"""

        # Check memory
        memory_mb = self.process.memory_info().rss / 1024 / 1024
        memory_violation = memory_mb > self.config.max_memory_mb

        # Check CPU
        cpu_percent = self.process.cpu_percent(interval=0.1)
        cpu_violation = cpu_percent > self.config.max_cpu_percent

        # Check execution time
        execution_time = time.time() - self.start_time
        time_violation = execution_time > self.config.max_execution_time

        status = {
            "memory_mb": memory_mb,
            "memory_limit_mb": self.config.max_memory_mb,
            "memory_violation": memory_violation,
            "cpu_percent": cpu_percent,
            "cpu_limit_percent": self.config.max_cpu_percent,
            "cpu_violation": cpu_violation,
            "execution_time": execution_time,
            "time_limit": self.config.max_execution_time,
            "time_violation": time_violation,
            "within_limits": not (memory_violation or cpu_violation or time_violation),
        }

        # Record violations
        if not status["within_limits"]:
            self.violations.append(
                {
                    "timestamp": datetime.now(),
                    "violations": {
                        "memory": memory_violation,
                        "cpu": cpu_violation,
                        "time": time_violation,
                    },
                    "values": {
                        "memory_mb": memory_mb,
                        "cpu_percent": cpu_percent,
                        "execution_time": execution_time,
                    },
                }
            )

        return status

    async def monitor_page_resources(self, page: Page) -> dict[str, Any]:
        """Monitor page-level resource usage"""

        try:
            metrics = await page.evaluate("""
                () => {
                    const getMemoryInfo = () => {
                        if (performance.memory) {
                            return {
                                usedJSHeapSize: performance.memory.usedJSHeapSize,
                                totalJSHeapSize: performance.memory.totalJSHeapSize,
                                jsHeapSizeLimit: performance.memory.jsHeapSizeLimit
                            };
                        }
                        return null;
                    };
                    
                    const getResourceCount = () => {
                        return {
                            domNodes: document.getElementsByTagName('*').length,
                            images: document.images.length,
                            scripts: document.scripts.length,
                            stylesheets: document.styleSheets.length,
                            iframes: document.getElementsByTagName('iframe').length
                        };
                    };
                    
                    const getResourceTimings = () => {
                        const resources = performance.getEntriesByType('resource');
                        return {
                            total: resources.length,
                            byType: resources.reduce((acc, r) => {
                                acc[r.initiatorType] = (acc[r.initiatorType] || 0) + 1;
                                return acc;
                            }, {})
                        };
                    };
                    
                    return {
                        memory: getMemoryInfo(),
                        resources: getResourceCount(),
                        timings: getResourceTimings(),
                        documentSize: document.documentElement.outerHTML.length
                    };
                }
            """)

            # Check for concerning patterns
            warnings = []

            if metrics["resources"]["domNodes"] > 50000:
                warnings.append("Excessive DOM nodes detected")

            if metrics["resources"]["iframes"] > 10:
                warnings.append("Many iframes detected - potential security risk")

            if metrics["documentSize"] > 10 * 1024 * 1024:  # 10MB
                warnings.append("Very large document size")

            metrics["warnings"] = warnings
            metrics["risk_level"] = "high" if warnings else "low"

            return metrics

        except Exception as e:
            logger.error(f"Failed to get page metrics: {e}")
            return {"error": str(e), "risk_level": "unknown"}


class SecureBrowserFactory:
    """Factory for creating secure browser instances"""

    @staticmethod
    def get_browser_args(config: SecurityConfig) -> list[str]:
        """Get browser arguments based on security config"""

        args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
        ]

        if config.trust_level == "untrusted":
            args.extend(
                [
                    "--disable-accelerated-2d-canvas",
                    "--disable-gpu",
                    "--disable-web-security",
                    "--disable-reading-from-canvas",
                    "--disable-webgl",
                    "--disable-plugins",
                    "--disable-popup-blocking",
                ]
            )

            if config.sandbox_mode:
                # Note: In production, avoid --no-sandbox
                args.append("--no-first-run")
            else:
                args.append("--no-sandbox")

        elif config.trust_level == "semi-trusted":
            args.extend(
                [
                    "--disable-plugins",
                ]
            )

            if not config.sandbox_mode:
                args.append("--no-sandbox")

        if config.isolate_origins:
            args.extend(
                [
                    "--disable-features=IsolateOrigins,site-per-process",
                    "--disable-site-isolation-trials",
                ]
            )

        return args

    @staticmethod
    async def create_secure_context(browser: Browser, config: SecurityConfig) -> BrowserContext:
        """Create a secure browser context"""

        # Build context options
        context_options = {
            "accept_downloads": config.allow_downloads,
            "bypass_csp": False,  # Respect Content Security Policy
            "ignore_https_errors": False,  # Don't ignore HTTPS errors
            "java_script_enabled": config.enable_javascript,
        }

        # Set permissions
        permissions = []
        if config.allow_geolocation:
            permissions.append("geolocation")
        if config.allow_notifications:
            permissions.append("notifications")

        context_options["permissions"] = permissions

        # Create context
        context = await browser.new_context(**context_options)

        # Add security-enhancing scripts
        await context.add_init_script("""
            // Disable dangerous APIs for untrusted content
            if (window.location.href.includes('untrusted')) {
                delete window.fetch;
                delete window.XMLHttpRequest;
                delete window.WebSocket;
                delete window.EventSource;
            }
            
            // Override console methods to prevent information leakage
            const noop = () => {};
            console.log = noop;
            console.info = noop;
            console.warn = noop;
            console.error = noop;
            
            // Prevent access to local storage
            delete window.localStorage;
            delete window.sessionStorage;
            
            // Disable service workers
            if ('serviceWorker' in navigator) {
                delete navigator.serviceWorker;
            }
        """)

        return context


class ContentSanitizer:
    """Sanitize untrusted content before use"""

    @staticmethod
    def sanitize_selector(selector: str) -> str:
        """Sanitize CSS selector to prevent injection"""

        # Remove potentially dangerous characters
        dangerous_chars = ["<", ">", '"', "'", "&", ";", "(", ")", "{", "}", "\\"]

        sanitized = selector
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, "")

        # Limit length
        max_length = 200
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]

        return sanitized

    @staticmethod
    def sanitize_javascript(script: str, allowed_patterns: list[str] = None) -> str | None:
        """Sanitize JavaScript code before execution"""

        allowed_patterns = allowed_patterns or []

        # Reject if contains dangerous patterns
        dangerous_patterns = [
            "eval(",
            "Function(",
            "setTimeout(",
            "setInterval(",
            "document.write",
            "innerHTML",
            "outerHTML",
            ".cookie",
            "localStorage",
            "sessionStorage",
            "indexedDB",
            "fetch(",
            "XMLHttpRequest",
            "WebSocket",
            "importScripts",
        ]

        script_lower = script.lower()
        for pattern in dangerous_patterns:
            if pattern.lower() in script_lower and pattern not in allowed_patterns:
                logger.warning(f"Rejected script containing: {pattern}")
                return None

        return script

    @staticmethod
    def sanitize_url(url: str) -> str | None:
        """Sanitize URL to prevent malicious protocols"""

        # Only allow http(s) protocols
        allowed_protocols = ["http://", "https://"]

        url_lower = url.lower().strip()

        if not any(url_lower.startswith(proto) for proto in allowed_protocols):
            logger.warning(f"Rejected URL with unsafe protocol: {url}")
            return None

        # Check for suspicious patterns
        suspicious_patterns = [
            "javascript:",
            "data:",
            "vbscript:",
            "file:",
            "about:",
        ]

        for pattern in suspicious_patterns:
            if pattern in url_lower:
                logger.warning(f"Rejected URL with suspicious pattern: {pattern}")
                return None

        return url


class IsolatedExecutor:
    """Execute untrusted operations in isolation"""

    def __init__(self, security_config: SecurityConfig):
        self.config = security_config
        self.resource_monitor = ResourceMonitor(security_config)
        self.sanitizer = ContentSanitizer()

    @asynccontextmanager
    async def isolated_page(self, browser: Browser):
        """Create an isolated page for untrusted operations"""

        # Create isolated context
        context = await SecureBrowserFactory.create_secure_context(browser, self.config)

        # Set up resource blocking
        page = await context.new_page()

        if not self.config.enable_images:
            await page.route("**/*.{png,jpg,jpeg,gif,webp,svg}", lambda route: route.abort())

        if not self.config.enable_stylesheets:
            await page.route("**/*.css", lambda route: route.abort())

        # Set stricter timeouts for untrusted content
        page.set_default_timeout(10000)  # 10 seconds

        try:
            yield page
        finally:
            await context.close()

    async def safe_evaluate(self, page: Page, script: str, timeout: int = 5000) -> Any | None:
        """Safely evaluate JavaScript with sanitization"""

        # Sanitize script
        safe_script = self.sanitizer.sanitize_javascript(script)
        if not safe_script:
            raise ValueError("Script rejected by sanitizer")

        # Check resources before execution
        resources = await self.resource_monitor.check_limits()
        if not resources["within_limits"]:
            raise RuntimeError(f"Resource limits exceeded: {resources}")

        # Execute with timeout
        try:
            result = await asyncio.wait_for(page.evaluate(safe_script), timeout=timeout / 1000)
            return result
        except TimeoutError:
            raise TimeoutError(f"Script execution timed out after {timeout}ms")

    async def safe_navigation(self, page: Page, url: str, timeout: int = 30000) -> dict[str, Any]:
        """Safely navigate to URL with validation"""

        # Sanitize URL
        safe_url = self.sanitizer.sanitize_url(url)
        if not safe_url:
            raise ValueError(f"URL rejected by sanitizer: {url}")

        # Monitor resources
        start_time = time.time()

        try:
            response = await page.goto(safe_url, timeout=timeout, wait_until="domcontentloaded")

            # Check final URL for redirects
            final_url = page.url
            if final_url != safe_url:
                # Validate redirect
                if not self.sanitizer.sanitize_url(final_url):
                    raise ValueError(f"Unsafe redirect detected: {final_url}")

            # Get page metrics
            metrics = await self.resource_monitor.monitor_page_resources(page)

            return {
                "success": True,
                "original_url": safe_url,
                "final_url": final_url,
                "status": response.status if response else None,
                "load_time": time.time() - start_time,
                "metrics": metrics,
                "risk_level": metrics.get("risk_level", "unknown"),
            }

        except Exception as e:
            return {"success": False, "error": str(e), "load_time": time.time() - start_time}


class SecurityAuditor:
    """Audit pages for security issues"""

    @staticmethod
    async def audit_page(page: Page) -> dict[str, Any]:
        """Perform security audit on current page"""

        audit_results = await page.evaluate("""
            () => {
                const results = {
                    mixed_content: [],
                    external_resources: [],
                    forms: [],
                    scripts: [],
                    vulnerabilities: []
                };
                
                // Check for mixed content
                const checkMixedContent = () => {
                    const isHttps = window.location.protocol === 'https:';
                    if (isHttps) {
                        // Check images
                        document.querySelectorAll('img[src^="http:"]').forEach(img => {
                            results.mixed_content.push({
                                type: 'image',
                                url: img.src
                            });
                        });
                        
                        // Check scripts
                        document.querySelectorAll('script[src^="http:"]').forEach(script => {
                            results.mixed_content.push({
                                type: 'script',
                                url: script.src
                            });
                        });
                    }
                };
                
                // Check external resources
                const checkExternalResources = () => {
                    const currentHost = window.location.hostname;
                    
                    document.querySelectorAll('[src], [href]').forEach(el => {
                        const url = el.src || el.href;
                        try {
                            const urlObj = new URL(url);
                            if (urlObj.hostname !== currentHost) {
                                results.external_resources.push({
                                    tag: el.tagName.toLowerCase(),
                                    url: url,
                                    host: urlObj.hostname
                                });
                            }
                        } catch {}
                    });
                };
                
                // Check forms
                const checkForms = () => {
                    document.querySelectorAll('form').forEach(form => {
                        const formInfo = {
                            action: form.action,
                            method: form.method,
                            hasFileInput: !!form.querySelector('input[type="file"]'),
                            hasPasswordInput: !!form.querySelector('input[type="password"]'),
                            isSecure: form.action.startsWith('https://') || form.action === ''
                        };
                        
                        if (!formInfo.isSecure && formInfo.hasPasswordInput) {
                            results.vulnerabilities.push({
                                type: 'insecure_form',
                                message: 'Password sent over insecure connection'
                            });
                        }
                        
                        results.forms.push(formInfo);
                    });
                };
                
                // Check inline scripts
                const checkScripts = () => {
                    document.querySelectorAll('script').forEach(script => {
                        if (!script.src) {
                            results.scripts.push({
                                type: 'inline',
                                content: script.textContent.substring(0, 100)
                            });
                            
                            // Check for eval usage
                            if (script.textContent.includes('eval(')) {
                                results.vulnerabilities.push({
                                    type: 'eval_usage',
                                    message: 'Inline script uses eval()'
                                });
                            }
                        }
                    });
                };
                
                // Run all checks
                checkMixedContent();
                checkExternalResources();
                checkForms();
                checkScripts();
                
                // Summary
                results.summary = {
                    hasMixedContent: results.mixed_content.length > 0,
                    externalResourceCount: results.external_resources.length,
                    formCount: results.forms.length,
                    inlineScriptCount: results.scripts.length,
                    vulnerabilityCount: results.vulnerabilities.length,
                    riskLevel: results.vulnerabilities.length > 0 ? 'high' : 
                              results.mixed_content.length > 0 ? 'medium' : 'low'
                };
                
                return results;
            }
        """)

        return audit_results


async def demonstrate_security_patterns():
    """Demonstrate security patterns"""

    async with async_playwright() as p:
        # Create configurations for different trust levels
        configs = {
            "untrusted": SecurityConfig(
                trust_level="untrusted",
                enable_javascript=False,
                sandbox_mode=True,
                max_memory_mb=512,
            ),
            "semi-trusted": SecurityConfig(
                trust_level="semi-trusted",
                enable_javascript=True,
                allow_downloads=False,
                max_memory_mb=1024,
            ),
            "trusted": SecurityConfig(
                trust_level="trusted",
                enable_javascript=True,
                enable_images=True,
                allow_downloads=True,
            ),
        }

        for trust_level, config in configs.items():
            print(f"\n{'=' * 50}")
            print(f"Testing with {trust_level} configuration")
            print(f"{'=' * 50}")

            # Create browser with security settings
            browser_args = SecureBrowserFactory.get_browser_args(config)
            browser = await p.chromium.launch(headless=True, args=browser_args)

            try:
                # Create isolated executor
                executor = IsolatedExecutor(config)

                async with executor.isolated_page(browser) as page:
                    # Test navigation
                    print("\nTesting secure navigation...")
                    nav_result = await executor.safe_navigation(page, "https://example.com")
                    print(f"Navigation result: {nav_result['success']}")
                    if nav_result["success"]:
                        print(f"Risk level: {nav_result['risk_level']}")

                    # Test script execution (if JavaScript enabled)
                    if config.enable_javascript:
                        print("\nTesting safe script execution...")
                        try:
                            result = await executor.safe_evaluate(
                                page, "document.title", timeout=2000
                            )
                            print(f"Page title: {result}")
                        except Exception as e:
                            print(f"Script execution failed: {e}")

                    # Perform security audit
                    print("\nPerforming security audit...")
                    if config.enable_javascript:
                        audit = await SecurityAuditor.audit_page(page)
                        print(f"Audit summary: {audit['summary']}")

                    # Check resource usage
                    print("\nChecking resource usage...")
                    resources = await executor.resource_monitor.check_limits()
                    print(
                        f"Memory: {resources['memory_mb']:.2f}MB / {resources['memory_limit_mb']}MB"
                    )
                    print(
                        f"CPU: {resources['cpu_percent']:.1f}% / {resources['cpu_limit_percent']}%"
                    )
                    print(f"Within limits: {resources['within_limits']}")

            finally:
                await browser.close()


if __name__ == "__main__":
    asyncio.run(demonstrate_security_patterns())
