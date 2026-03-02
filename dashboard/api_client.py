"""
Hardened API Client with Circuit Breaker and Exponential Backoff
Production-grade reliability patterns for external API calls
"""

import time
import threading
import logging
import re
from typing import Optional, Dict, Any, Callable, TypeVar, Generic
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
import requests
from requests.exceptions import RequestException, Timeout, ConnectionError

# Configure structured logging
logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    failure_threshold: int = 5           # Failures before opening
    recovery_timeout: float = 30.0       # Seconds before half-open
    half_open_max_calls: int = 3         # Test calls in half-open
    success_threshold: int = 2           # Successes to close circuit


@dataclass
class RetryConfig:
    """Configuration for exponential backoff retry"""
    max_retries: int = 3
    base_delay: float = 1.0              # Initial delay in seconds
    max_delay: float = 30.0              # Maximum delay
    exponential_base: float = 2.0        # Backoff multiplier
    retryable_exceptions: tuple = (
        Timeout, ConnectionError, RequestException
    )


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.
    Prevents cascade failures by stopping requests to failing services.
    """
    
    def __init__(self, name: str, config: CircuitBreakerConfig = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.half_open_calls = 0
        self._lock = threading.Lock()
    
    def can_execute(self) -> bool:
        """Check if request can be executed"""
        with self._lock:
            if self.state == CircuitState.CLOSED:
                return True
            
            if self.state == CircuitState.OPEN:
                if time.time() - self.last_failure_time >= self.config.recovery_timeout:
                    logger.info(f"[{self.name}] Circuit entering HALF_OPEN state")
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_calls = 0
                    self.success_count = 0
                    return True
                return False
            
            if self.state == CircuitState.HALF_OPEN:
                if self.half_open_calls < self.config.half_open_max_calls:
                    self.half_open_calls += 1
                    return True
                return False
            
            return True
    
    def record_success(self):
        """Record successful execution"""
        with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.config.success_threshold:
                    logger.info(f"[{self.name}] Circuit CLOSED - service recovered")
                    self._reset()
            else:
                self.failure_count = 0
    
    def record_failure(self):
        """Record failed execution"""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.state == CircuitState.HALF_OPEN:
                logger.warning(f"[{self.name}] Circuit OPEN - recovery failed")
                self.state = CircuitState.OPEN
            elif self.failure_count >= self.config.failure_threshold:
                logger.error(f"[{self.name}] Circuit OPEN - failure threshold reached")
                self.state = CircuitState.OPEN
    
    def _reset(self):
        """Reset circuit to closed state"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.half_open_calls = 0
        self.last_failure_time = None
    
    def get_state(self) -> Dict[str, Any]:
        """Get current circuit state for monitoring"""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure": self.last_failure_time,
            "is_open": self.state == CircuitState.OPEN
        }


class APIClient:
    """
    Hardened HTTP client with circuit breaker and retry logic.
    Production-ready for financial data APIs.
    """
    
    def __init__(
        self,
        name: str = "api_client",
        timeout: float = 15.0,
        circuit_config: CircuitBreakerConfig = None,
        retry_config: RetryConfig = None
    ):
        self.name = name
        self.timeout = timeout
        self.circuit = CircuitBreaker(name, circuit_config or CircuitBreakerConfig())
        self.retry_config = retry_config or RetryConfig()
        self.session = requests.Session()
        self._request_count = 0
        self._error_count = 0
        self._total_latency = 0.0
        self._lock = threading.Lock()
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay"""
        delay = self.retry_config.base_delay * (
            self.retry_config.exponential_base ** attempt
        )
        return min(delay, self.retry_config.max_delay)
    
    def request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> Optional[requests.Response]:
        """
        Make hardened HTTP request with retry and circuit breaker
        
        Args:
            method: HTTP method
            url: Request URL
            **kwargs: Additional arguments for requests
        
        Returns:
            Response object or None on failure
        """
        # Check circuit breaker
        if not self.circuit.can_execute():
            logger.warning(f"[{self.name}] Circuit open - rejecting request to {url}")
            return None
        
        # Set timeout
        kwargs['timeout'] = kwargs.get('timeout', self.timeout)
        
        # Attempt request with retry
        for attempt in range(self.retry_config.max_retries):
            start_time = time.time()
            try:
                response = self.session.request(method, url, **kwargs)
                latency = time.time() - start_time
                
                with self._lock:
                    self._request_count += 1
                    self._total_latency += latency
                
                # Check for HTTP errors
                response.raise_for_status()
                
                # Record success
                self.circuit.record_success()
                logger.debug(
                    f"[{self.name}] Request succeeded - {method} {url} "
                    f"(attempt {attempt + 1}, latency: {latency:.2f}s)"
                )
                return response
                
            except self.retry_config.retryable_exceptions as e:
                latency = time.time() - start_time
                with self._lock:
                    self._error_count += 1
                
                if attempt < self.retry_config.max_retries - 1:
                    delay = self._calculate_delay(attempt)
                    logger.warning(
                        f"[{self.name}] Request failed (attempt {attempt + 1}), "
                        f"retrying in {delay:.1f}s: {type(e).__name__}"
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        f"[{self.name}] Request failed after "
                        f"{self.retry_config.max_retries} attempts: {type(e).__name__}"
                    )
                    self.circuit.record_failure()
                    return None
                    
            except Exception as e:
                latency = time.time() - start_time
                with self._lock:
                    self._error_count += 1
                logger.error(f"[{self.name}] Unexpected error: {type(e).__name__}: {str(e)[:100]}")
                self.circuit.record_failure()
                return None
        
        return None
    
    def get(self, url: str, **kwargs) -> Optional[requests.Response]:
        """Make GET request"""
        return self.request("GET", url, **kwargs)
    
    def post(self, url: str, **kwargs) -> Optional[requests.Response]:
        """Make POST request"""
        return self.request("POST", url, **kwargs)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics for monitoring"""
        with self._lock:
            avg_latency = (
                self._total_latency / self._request_count
                if self._request_count > 0 else 0.0
            )
            error_rate = (
                self._error_count / (self._request_count + self._error_count) * 100
                if (self._request_count + self._error_count) > 0 else 0.0
            )
            return {
                "name": self.name,
                "request_count": self._request_count,
                "error_count": self._error_count,
                "error_rate": f"{error_rate:.2f}%",
                "avg_latency": f"{avg_latency:.3f}s",
                "circuit_state": self.circuit.get_state()
            }
    
    def reset_circuit(self):
        """Manually reset circuit breaker"""
        self.circuit._reset()
        logger.info(f"[{self.name}] Circuit breaker manually reset")


# Input validation utilities
class InputValidator:
    """Input validation utilities with sanitized error messages"""
    
    # Valid ticker pattern: 1-5 uppercase letters
    TICKER_PATTERN = re.compile(r'^[A-Z]{1,5}$')
    
    # Common injection patterns to block
    DANGEROUS_PATTERNS = [
        re.compile(r'<script', re.IGNORECASE),
        re.compile(r'javascript:', re.IGNORECASE),
        re.compile(r'on\w+=', re.IGNORECASE),  # event handlers
        re.compile(r'[;|&`$]'),  # shell metacharacters
        re.compile(r'\.\./'),  # path traversal
    ]
    
    @classmethod
    def validate_ticker(cls, ticker: str) -> tuple[bool, str]:
        """
        Validate ticker symbol.
        
        Returns:
            (is_valid, error_message or cleaned_ticker)
        """
        if not ticker:
            return False, "Ticker symbol is required"
        
        # Clean input
        ticker = ticker.strip().upper()
        
        # Check against dangerous patterns
        for pattern in cls.DANGEROUS_PATTERNS:
            if pattern.search(ticker):
                logger.warning(f"Rejected ticker with dangerous pattern: {ticker[:20]}")
                return False, "Invalid ticker symbol format"
        
        # Validate format
        if not cls.TICKER_PATTERN.match(ticker):
            return False, "Ticker must be 1-5 uppercase letters (e.g., AAPL, SPY)"
        
        return True, ticker
    
    @classmethod
    def sanitize_string(cls, value: str, max_length: int = 100) -> str:
        """Sanitize string input"""
        if not isinstance(value, str):
            return ""
        
        # Trim and limit length
        value = value.strip()[:max_length]
        
        # Remove dangerous characters
        dangerous = ['<', '>', '"', "'", ';', '|', '&', '`', '$']
        for char in dangerous:
            value = value.replace(char, '')
        
        return value
    
    @classmethod
    def validate_numeric(cls, value: Any, min_val: float = None, max_val: float = None) -> tuple[bool, float]:
        """Validate numeric input"""
        try:
            num = float(value)
            if min_val is not None and num < min_val:
                return False, 0.0
            if max_val is not None and num > max_val:
                return False, 0.0
            return True, num
        except (ValueError, TypeError):
            return False, 0.0


# Global API clients with different configurations
_polygon_client = None
_fallback_client = None


def get_polygon_client() -> APIClient:
    """Get hardened Polygon API client"""
    global _polygon_client
    if _polygon_client is None:
        _polygon_client = APIClient(
            name="polygon_api",
            timeout=15.0,
            circuit_config=CircuitBreakerConfig(
                failure_threshold=5,
                recovery_timeout=60.0  # Wait 60s before retry
            ),
            retry_config=RetryConfig(
                max_retries=3,
                base_delay=1.0,
                max_delay=10.0
            )
        )
    return _polygon_client


def get_fallback_client() -> APIClient:
    """Get fallback API client (yfinance)"""
    global _fallback_client
    if _fallback_client is None:
        _fallback_client = APIClient(
            name="fallback_api",
            timeout=30.0,
            circuit_config=CircuitBreakerConfig(
                failure_threshold=3,
                recovery_timeout=30.0
            ),
            retry_config=RetryConfig(
                max_retries=2,
                base_delay=0.5,
                max_delay=5.0
            )
        )
    return _fallback_client


def get_health_status() -> Dict[str, Any]:
    """Get health status of all API clients"""
    return {
        "polygon": get_polygon_client().get_stats() if _polygon_client else {"status": "not_initialized"},
        "fallback": get_fallback_client().get_stats() if _fallback_client else {"status": "not_initialized"}
    }


def reset_all_circuits():
    """Reset all circuit breakers"""
    if _polygon_client:
        _polygon_client.reset_circuit()
    if _fallback_client:
        _fallback_client.reset_circuit()
    logger.info("All circuit breakers reset")