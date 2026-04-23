import json
import os
import re
import requests
import time
import logging
from datetime import datetime, timedelta

# Static pricing for models not yet in the AWS Price List API.
# Prices are per-token (USD). Source: https://aws.amazon.com/bedrock/pricing/
# Keys are lowercase substrings matched against the normalized model identifier.
_STATIC_PRICES = {
    "claude-sonnet-4-6":    {"input": 3.00 / 1_000_000, "output": 15.00 / 1_000_000, "cache_read": 0.30 / 1_000_000, "cache_write": 3.75 / 1_000_000},
    "claude-sonnet-4-5":    {"input": 3.00 / 1_000_000, "output": 15.00 / 1_000_000, "cache_read": 0.30 / 1_000_000, "cache_write": 3.75 / 1_000_000},
    "claude-opus-4-7":      {"input": 15.00 / 1_000_000, "output": 75.00 / 1_000_000, "cache_read": 1.50 / 1_000_000, "cache_write": 18.75 / 1_000_000},
    "claude-haiku-4-5":     {"input": 0.80 / 1_000_000, "output": 4.00 / 1_000_000, "cache_read": 0.08 / 1_000_000, "cache_write": 1.00 / 1_000_000},
    "claude-3-5-sonnet":    {"input": 3.00 / 1_000_000, "output": 15.00 / 1_000_000, "cache_read": 0.30 / 1_000_000, "cache_write": 3.75 / 1_000_000},
    "claude-3-5-haiku":     {"input": 0.80 / 1_000_000, "output": 4.00 / 1_000_000, "cache_read": 0.08 / 1_000_000, "cache_write": 1.00 / 1_000_000},
    "claude-3-7-sonnet":    {"input": 3.00 / 1_000_000, "output": 15.00 / 1_000_000, "cache_read": 0.30 / 1_000_000, "cache_write": 3.75 / 1_000_000},
}


def _normalize_model_id(model_id: str) -> str:
    """
    Reduce any model identifier to a bare lowercase key for price lookups.

    Handles:
      - Full inference profile ARNs:
        arn:aws:bedrock:us-east-1:123:inference-profile/us.anthropic.claude-sonnet-4-6
      - Cross-region prefixed IDs:  us.anthropic.claude-sonnet-4-6
      - Standard model IDs:         anthropic.claude-sonnet-4-6-v1:0
    Returns a lowercase string like "anthropic.claude-sonnet-4-6-v1:0".
    """
    # Strip ARN prefix, keep everything after the last "/"
    if "/" in model_id:
        model_id = model_id.split("/")[-1]
    # Strip cross-region prefix (e.g. "us.", "eu.", "ap.")
    model_id = re.sub(r"^(us|eu|ap)\.", "", model_id)
    return model_id.lower()


def _static_price(model_id: str) -> dict | None:
    """Return a static price dict if the model matches a known key, else None."""
    normalized = _normalize_model_id(model_id)
    for key, prices in _STATIC_PRICES.items():
        if key in normalized:
            return prices
    return None


class PricingFetcher:
    def __init__(self, config):
        self.config = config
        self.cache_file = config['pricing']['cache_file']
        self.url = config['pricing']['url']
        self.refresh_hours = config['pricing']['refresh_hours']
        self.prices = {}

    def _is_cache_valid(self):
        if not os.path.exists(self.cache_file):
            return False
        
        file_time = datetime.fromtimestamp(os.path.getmtime(self.cache_file))
        if datetime.now() - file_time > timedelta(hours=self.refresh_hours):
            return False
        
        return True

    def fetch_prices(self):
        if self._is_cache_valid():
            with open(self.cache_file, 'r') as f:
                self.prices = json.load(f)
            logging.info(f"Loaded {len(self.prices)} models from cache.")
            return self.prices

        # Task 10: Retry logic for network calls
        max_retries = 3
        backoff = 1
        
        for attempt in range(max_retries):
            try:
                logging.info(f"Fetching latest Bedrock pricing from {self.url} (Attempt {attempt+1})...")
                response = requests.get(self.url, timeout=30)
                response.raise_for_status()
                raw_data = response.json()
                self.prices = self._parse_pricing(raw_data)
                
                with open(self.cache_file, 'w') as f:
                    json.dump(self.prices, f, indent=2)
                
                logging.info(f"Successfully fetched and parsed {len(self.prices)} models.")
                return self.prices
            except Exception as e:
                logging.warning(f"Attempt {attempt+1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(backoff)
                    backoff *= 2
                else:
                    if os.path.exists(self.cache_file):
                        logging.error("All retries failed. Falling back to stale cache.")
                        with open(self.cache_file, 'r') as f:
                            self.prices = json.load(f)
                        return self.prices
                    raise

    def _parse_pricing(self, data):
        """
        Parses the AWS Pricing Index JSON for Bedrock.
        Maps normalized model name -> { 'input': X, 'output': Y, 'cache_read': Z, 'cache_write': W }

        Note: the AWS Price List API uses 'model' (display name) + 'usagetype' + 'inferenceType'
        rather than a machine-readable modelId field. Keys are stored as lowercase model display names.
        """
        parsed = {}
        products = data.get('products', {})
        terms = data.get('terms', {}).get('OnDemand', {})

        sku_map = {}
        skipped_skus = 0

        for sku, product in products.items():
            attr = product.get('attributes', {})
            if attr.get('servicecode') != 'AmazonBedrock':
                continue

            model_name = attr.get('model', '').strip()
            if not model_name:
                skipped_skus += 1
                continue

            # Only index us-east-1 to avoid duplicate keys across regions
            region = attr.get('regionCode', '')
            if region and region != 'us-east-1':
                continue

            usage_type = attr.get('usagetype', attr.get('usageType', ''))
            inference_type = attr.get('inferenceType', '').lower()

            price_type = None
            if 'cacheread' in usage_type.lower() or 'cache read' in inference_type:
                price_type = 'cache_read'
            elif 'cachewrite' in usage_type.lower() or 'cache write' in inference_type:
                price_type = 'cache_write'
            elif 'input' in usage_type.lower() or 'input' in inference_type:
                price_type = 'input'
            elif 'output' in usage_type.lower() or 'output' in inference_type:
                price_type = 'output'

            if price_type:
                sku_map[sku] = (model_name.lower(), price_type)
            else:
                skipped_skus += 1
                logging.debug(f"Skipped unclassified SKU {sku}: usagetype='{usage_type}', inferenceType='{inference_type}'")

        logging.info(f"Classified {len(sku_map)} SKUs, skipped {skipped_skus} unclassified or irrelevant entries.")

        for sku, term_data in terms.items():
            if sku not in sku_map:
                continue

            model_key, price_type = sku_map[sku]

            for offer in term_data.values():
                for dimension in offer.get('priceDimensions', {}).values():
                    price_per_unit = float(dimension.get('pricePerUnit', {}).get('USD', 0))
                    unit = dimension.get('unit', '')

                    if model_key not in parsed:
                        parsed[model_key] = {}

                    unit_lower = unit.lower()
                    if '1000' in unit or '1,000' in unit or '1k' in unit_lower:
                        parsed[model_key][price_type] = price_per_unit / 1000.0
                    elif unit_lower in ('tokens', 'token', ''):
                        parsed[model_key][price_type] = price_per_unit
                    else:
                        logging.warning(f"Unexpected unit '{unit}' for model '{model_key}' ({price_type}). Storing raw value.")
                        parsed[model_key][price_type] = price_per_unit

        return parsed

    def get_price(self, model_id: str, price_type: str = 'input') -> float | None:
        """
        Look up price for a model. Handles full ARNs, cross-region prefixes, and
        standard model IDs. Falls back to static table for models missing from the API.
        Returns None if no price is found.
        """
        # Try static table first (covers modern Claude models missing from API)
        static = _static_price(model_id)
        if static:
            return static.get(price_type)

        # Try API-parsed prices by normalized key
        normalized = _normalize_model_id(model_id)
        rates = self.prices.get(normalized)
        if rates:
            return rates.get(price_type)

        return None
