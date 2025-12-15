"""
VIRTUS Health Aggregator
=========================

Re-export do HealthAggregator para compatibilidade de imports.
"""

from .prometheus_exporter import HealthAggregator

__all__ = ['HealthAggregator']
