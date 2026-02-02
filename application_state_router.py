import logging
logger = logging.getLogger(__name__)

from trading_utils import *



def populate_global_state(application_state):
    application_state['global_state.symbol_to_conid'] = global_state.symbol_to_conid
    application_state['global_state.conid_to_symbol'] = global_state.conid_to_symbol
    application_state['global_state.quote_cache'] = global_state.quote_cache
    application_state['global_state.quote_cache_count'] = len(global_state.quote_cache)
    application_state['global_state.conid_to_symbol_subscribed_for_quotes'] = global_state.conid_to_symbol_subscribed_for_quotes
    application_state['global_state.contract_cache'] = global_state.stringify_option_cache(global_state.contract_cache)
    application_state['global_state.option_contract_cache'] = global_state.stringify_option_cache(global_state.option_contract_cache)
    application_state['global_state.quote_cache_symbols'] = global_state.extract_symbols_from_quote_cache()
    application_state['global_state.subscribed_symbols_count'] = global_state.subscribed_symbols_count
