import logging
import random as _random
import math
import warnings
from typing import Union, Optional
from .thread_locals import validate_param, RootMixin

# Initialize a logger for this module
logger = logging.getLogger(__name__)

# Define a custom warning for optional NumPy support
class OptionalNumpyWarning(Warning):
    """Custom warning to indicate that NumPy is not available and a fallback to standard Python is used."""

# Try to import NumPy
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

class BaseSampler(RootMixin):
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

    Attributes:
        distribution (str): The distribution to sample from.
        shape (Union[float, np.float32, np.float64]): Shape parameter for the distribution, controlling the spread and skewness.
                       For log-normal, it represents sigma of the underlying normal distribution.
        scale (Union[float, np.float32, np.float64]): Scale parameter for the distribution, shifting the distribution and determining its median.
                       For log-normal, it represents exp(mu) of the underlying normal distribution.
                       For exponential, it is used directly as the mean of the distribution.
        lower_bound (Optional[Union[float, np.float32, np.float64]]): Lower bound for the sampled value. Default is None (interpreted as unbounded).
        upper_bound (Optional[Union[float, np.float32, np.float64]]): Upper bound for the sampled value. Default is None (interpreted as unbounded).
        max_retries (int): Maximum number of attempts to sample a valid value. Default is 1000.
    """

    def __init__(self, **kwargs):
        """
        Initialize the BaseSampler with required and optional parameters.

        :param kwargs: Keyword arguments for initialization.
        """
        logger.info("__init__()")
        super().__init__(**kwargs)

        self.distribution = kwargs.get('distribution', None)
        validate_param(self.distribution, "distribution")
        self.shape = kwargs.get('shape', None)
        validate_param(self.shape, "shape")
        self.scale = kwargs.get('scale', None)
        validate_param(self.scale, "scale")
        self.lower_bound = kwargs.get('lower_bound', -math.inf)
        self.upper_bound = kwargs.get('upper_bound', math.inf)
        self.max_retries = kwargs.get('max_retries', 1000)

        # Validate distribution
        self.supported_distributions = {
            'lognormvariate', 'normalvariate', 'expovariate', 'vonmisesvariate',
            'gammavariate', 'gauss', 'betavariate', 'paretovariate', 'weibullvariate'
        }

        if self.distribution not in self.supported_distributions:
            raise ValueError(f"Unsupported distribution: {self.distribution}")

    def get_sample(self) -> Union[float, np.float32, np.float64]:
        """
        Get a sample from the specified distribution.

        :return: A sample from the specified distribution within the specified bounds.
        """
        raise NotImplementedError("This method should be implemented by subclasses.")

if USE_NUMPY:
    class Sampler(BaseSampler):
        """
        A class to sample from various statistical distributions using NumPy.
        """

        def __init__(self, **kwargs):
            random_seed = kwargs.pop('random_seed', None)
            random_state = kwargs.pop('random_state', None)
            super().__init__(**kwargs)

            # Use the provided random_state or create a new one
            if random_state is not None:
                self.random_state = random_state
            else:
                self.random_state = np.random.RandomState(random_seed)

        def get_sample(self) -> Union[float, np.float32, np.float64]:
            logger.info("get_sample()")

            # Map distribution names to numpy random methods
            distribution_methods = {
                'lognormvariate': lambda: self.random_state.lognormal(math.log(self.scale), self.shape),
                'normalvariate': lambda: self.random_state.normal(self.scale, self.shape),
                'expovariate': lambda: self.random_state.exponential(self.scale),
                'vonmisesvariate': lambda: self.random_state.vonmises(self.scale, self.shape),
                'gammavariate': lambda: self.random_state.gamma(self.shape, self.scale),
                'gauss': lambda: self.random_state.normal(self.scale, self.shape),
                'betavariate': lambda: self.random_state.beta(self.shape, self.scale),
                'paretovariate': lambda: self.random_state.pareto(self.shape),
                'weibullvariate': lambda: self.random_state.weibull(self.shape) * self.scale
            }

            for _ in range(self.max_retries):
                sampled_value = distribution_methods[self.distribution]()
                if self.lower_bound <= sampled_value <= self.upper_bound:
                    return sampled_value
            raise RuntimeError("Failed to sample a valid value within the specified bounds after max retries.")
else:
    class Sampler(BaseSampler):
        """
        A class to sample from various statistical distributions using the standard random module.

        Note: The expovariate method has been adjusted to align with NumPy's exponential function,
        using the scale directly as the mean of the distribution.
        """

        def __init__(self, **kwargs):
            random_seed = kwargs.pop('random_seed', None)
            random_instance = kwargs.pop('random_instance', None)
            super().__init__(**kwargs)

            # Use the provided random_instance or create a new one
            if random_instance is not None:
                self.random_instance = random_instance
            else:
                self.random_instance = _random.Random(random_seed)

        def get_sample(self) -> Union[float, np.float32, np.float64]:
            logger.info("get_sample()")

            # Map distribution names to random instance methods
            distribution_methods = {
                'lognormvariate': lambda: self.random_instance.lognormvariate(math.log(self.scale), self.shape),
                'normalvariate': lambda: self.random_instance.normalvariate(self.scale, self.shape),
                'expovariate': lambda: self.random_instance.expovariate(self.scale),  # Adjusted to use scale as mean
                'vonmisesvariate': lambda: self.random_instance.vonmisesvariate(self.scale, self.shape),
                'gammavariate': lambda: self.random_instance.gammavariate(self.shape, self.scale),
                'gauss': lambda: self.random_instance.gauss(self.scale, self.shape),
                'betavariate': lambda: self.random_instance.betavariate(self.shape, self.scale),
                'paretovariate': lambda: self.random_instance.paretovariate(self.shape),
                'weibullvariate': lambda: self.random_instance.weibullvariate(self.shape, self.scale)
            }

            for _ in range(self.max_retries):
                sampled_value = distribution_methods[self.distribution]()
                if self.lower_bound <= sampled_value <= self.upper_bound:
                    return sampled_value
            raise RuntimeError("Failed to sample a valid value within the specified bounds after max retries.")