import logging

class CostEngine:
    def __init__(self, pricing_fetcher):
        self.pricing = pricing_fetcher

    def calculate_cost(self, log_data):
        """
        Calculates the cost for a single invocation based on the model and token counts.
        """
        model_id = log_data['modelId']

        def _rate(price_type):
            r = self.pricing.get_price(model_id, price_type)
            if r is None:
                return None
            return r

        input_rate    = _rate('input')
        output_rate   = _rate('output')
        cr_rate       = _rate('cache_read')
        cw_rate       = _rate('cache_write')

        if input_rate is None and output_rate is None:
            logging.warning(f"No pricing data for model: {model_id}")
            return None

        # Standard Input/Output
        input_cost  = log_data.get('inputTokenCount', 0)           * (input_rate  or 0.0)
        output_cost = log_data.get('outputTokenCount', 0)          * (output_rate or 0.0)

        # Prompt Caching (Read/Write)
        cache_read_cost  = log_data.get('cacheReadInputTokenCount', 0)  * (cr_rate or 0.0)
        cache_write_cost = log_data.get('cacheWriteInputTokenCount', 0) * (cw_rate or 0.0)
        
        total_cost = input_cost + output_cost + cache_read_cost + cache_write_cost
        return total_cost
