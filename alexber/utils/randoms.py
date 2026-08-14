from __future__ import annotations

import random as _random
import math
import warnings
from .warning import OptionalNumpyWarning


class SamplingError(Exception):
    """Custom exception raised when sampling fails after maximum retries.

    Attributes:
        distribution (str): The distribution from which sampling was attempted.
        retries (int): The number of retries attempted before failure.
        lower_bound (float | None): The lower bound for the sampled value.
        upper_bound (float | None): The upper bound for the sampled value.
    """
    def __init__(self, message, distribution, retries, lower_bound, upper_bound):
        """
        Initialize the SamplingError with a message, distribution, retries, and bounds.

        :param message: The error message.
        :param distribution: The distribution from which sampling was attempted.
        :param retries: The number of retries attempted before failure.
        :param lower_bound: The lower bound for the sampled value.
        :param upper_bound: The upper bound for the sampled value.
        """
        super().__init__(message)
        self.distribution = distribution
        self.retries = retries
        self.lower_bound = lower_bound if lower_bound != -math.inf else None
        self.upper_bound = upper_bound if upper_bound != math.inf else None

    def __str__(self):
        """Return a user-friendly string representation of the error."""
        bounds_info = f"Lower bound: {self.lower_bound}, Upper bound: {self.upper_bound}"
        return (f"{self.args[0]} (Distribution: {self.distribution}, "
                f"Retries: {self.retries}, {bounds_info})")

    def __repr__(self):
        """Return a detailed string representation of the error for debugging."""
        bounds_info = f"lower_bound={self.lower_bound!r}, upper_bound={self.upper_bound!r}"
        return (f"SamplingError(message={self.args[0]!r}, distribution={self.distribution!r}, "
                f"retries={self.retries!r}, {bounds_info})")


# Try to import NumPy for performance boost
try:
    import numpy as np
    USE_NUMPY = True
except ImportError:
    warning_message = (
        "NumPy module wasn't found. Falling back to standard Python. "
        "Using NumPy may lead to a performance boost. "
        "You can install it by running 'python -m pip install alex-ber-utils[numpy]'."
    )
    warnings.warn(warning_message, OptionalNumpyWarning)
    USE_NUMPY = False

class BaseSampler:
    """
    Base class for sampling from various statistical distributions with configurable parameters.

    Supported Distributions:
        - 'lognormvariate': Log-normal distribution.
        - 'normalvariate': Normal distribution.
        - 'expovariate': Exponential distribution.
        - 'vonmisesvariate': Von Mises distribution.
        - 'gammavariate': Gamma distribution.
        - 'gauss': Gaussian distribution.
        - 'betavariate': Beta distribution.
        - 'paretovariate': Pareto distribution.
        - 'weibullvariate': Weibull distribution.
        - 'uniform': Uniform distribution.

    Attributes:
        distribution (str): The distribution to sample from.
        shape (float | np.float32 | np.float64): Shape parameter for the distribution.
                       For log-normal, it represents sigma of the underlying normal distribution.
        scale (float | np.float32 | np.float64): Scale parameter for the distribution.
                       For log-normal, it represents exp(mu) of the underlying normal distribution.
                       For exponential, it is used directly as the mean of the distribution.
        lower_bound (float | np.float32 | np.float64 | None): Lower bound for the sampled value. Default is -inf.
        upper_bound (float | np.float32 | np.float64 | None): Upper bound for the sampled value. Default is inf.
        max_retries (int): Maximum number of attempts to sample a valid value. Default is 1000.
    """

    # Class-level attribute for supported distributions
    supported_distributions = {
        'lognormvariate', 'normalvariate', 'expovariate', 'vonmisesvariate',
        'gammavariate', 'gauss', 'betavariate', 'paretovariate', 'weibullvariate',
        'uniform'
    }

    def __init__(self, **kwargs):
        """
        Initialize the BaseSampler with required and optional parameters.

        :param kwargs: Keyword arguments for initialization.
        """
        self.distribution = kwargs.get('distribution', None)
        self.shape = kwargs.get('shape', None)
        self.scale = kwargs.get('scale', None)
        self.lower_bound = kwargs.get('lower_bound', -math.inf)
        self.upper_bound = kwargs.get('upper_bound', math.inf)
        self.max_retries = kwargs.get('max_retries', 1000)

        self.validate_distribution()
        self.validate_bounds()

        # This attribute will be configured in the subclass
        self._sampling_func = None

    def validate_distribution(self):
        """Validate that the specified distribution is supported."""
        if self.distribution not in self.supported_distributions:
            raise ValueError(f"Unsupported distribution: {self.distribution}")

    def validate_bounds(self):
        """
        Validate that the lower bound is less than the upper bound.
        In adition for 'uniform' distribution, lower_bound and upper_bound must be finite.
        """
        if not (self.lower_bound < self.upper_bound):
            raise ValueError("lower_bound must be less than upper_bound")
        if self.distribution == 'uniform' and (math.isinf(self.lower_bound) or math.isinf(self.upper_bound)):
            raise ValueError("For 'uniform' distribution, bounds must be finite.")

    def validate_random_parameters(self, seed, instance):
        """
        Validate that only one of random_seed or random_state/random_instance is provided.

        :param seed: The random seed.
        :param instance: The random state or instance.
        """
        if seed is not None and instance is not None:
            raise ValueError("Specify only one of random_seed or random_state/random_instance")

    def get_sample(self) -> float | 'np.float32' | 'np.float64':
        """
        Get a sample from the specified distribution using common retry logic.

        :return: A sample from the specified distribution within the specified bounds.
        """
        for _ in range(self.max_retries):
            sampled_value = self._sampling_func()
            if self.lower_bound <= sampled_value <= self.upper_bound:
                return sampled_value

        raise SamplingError(
            "Failed to sample a valid value within the specified bounds after max retries.",
            self.distribution, self.max_retries, self.lower_bound, self.upper_bound
        )


if USE_NUMPY:
    class Sampler(BaseSampler):
        """A class to sample from various statistical distributions using NumPy."""

        def __init__(self, **kwargs):
            """
            Initialize the Sampler with NumPy-specific parameters.

            :param kwargs: Keyword arguments for initialization.
            """
            random_seed = kwargs.pop('random_seed', None)
            random_state = kwargs.pop('random_state', None)
            self.validate_random_parameters(random_seed, random_state)

            super().__init__(**kwargs)
            # Modern standard API: replaces legacy `np.random.RandomState()`
            # with faster/safer `np.random.default_rng()` in NumPy 2.x natively
            self.random_state = random_state or np.random.default_rng(random_seed)

            # Pre-configure the function mapping to improve performance
            rs = self.random_state
            dist_map = {
                'lognormvariate': lambda: rs.lognormal(math.log(self.scale), self.shape),
                'normalvariate': lambda: rs.normal(self.scale, self.shape),
                'expovariate': lambda: rs.exponential(self.scale),
                'vonmisesvariate': lambda: rs.vonmises(self.scale, self.shape),
                'gammavariate': lambda: rs.gamma(self.shape, self.scale),
                'gauss': lambda: rs.normal(self.scale, self.shape),
                'betavariate': lambda: rs.beta(self.shape, self.scale),
                'paretovariate': lambda: rs.pareto(self.shape),
                'weibullvariate': lambda: rs.weibull(self.shape) * self.scale,
                'uniform': lambda: rs.uniform(self.lower_bound, self.upper_bound)
            }
            self._sampling_func = dist_map[self.distribution]

else:
    class Sampler(BaseSampler):
        """
        A class to sample from various statistical distributions using the standard random module.

        Note: The expovariate method has been adjusted to align with NumPy's exponential function,
        using the scale directly as the mean of the distribution.
        """

        def __init__(self, **kwargs):
            """
            Initialize the Sampler with standard random module-specific parameters.

            :param kwargs: Keyword arguments for initialization.
            """
            random_seed = kwargs.pop('random_seed', None)
            random_instance = kwargs.pop('random_instance', None)
            self.validate_random_parameters(random_seed, random_instance)

            super().__init__(**kwargs)
            self.random_instance = random_instance or _random.Random(random_seed)

            ri = self.random_instance
            dist_map = {
                'lognormvariate': lambda: ri.lognormvariate(math.log(self.scale), self.shape),
                'normalvariate': lambda: ri.normalvariate(self.scale, self.shape),
                'expovariate': lambda: ri.expovariate(1.0 / self.scale),
                'vonmisesvariate': lambda: ri.vonmisesvariate(self.scale, self.shape),
                'gammavariate': lambda: ri.gammavariate(self.shape, self.scale),
                'gauss': lambda: ri.gauss(self.scale, self.shape),
                'betavariate': lambda: ri.betavariate(self.shape, self.scale),
                'paretovariate': lambda: ri.paretovariate(self.shape),
                'weibullvariate': lambda: ri.weibullvariate(self.scale, self.shape),
                'uniform': lambda: ri.uniform(self.lower_bound, self.upper_bound)
            }
            self._sampling_func = dist_map[self.distribution]