from trading_utils import *



def populate_global_state(application_state):
    application_state['global_state.symbol_to_conid'] = global_state.symbol_to_conid
    application_state['global_state.conid_to_symbol'] = global_state.conid_to_symbol
    application_state['global_state.quote_cache'] = global_state.quote_cache
    application_state['global_state.contract_cache'] = global_state.contract_cache
    # bcs of this error : 2025-12-23 14:22:11,459 - trading_core.data_saver_manager - ERROR - @@@ [DataSaverManager] Unexpected error keys must be str, int, float, bool or None, not tuple
    # application_state['global_state.option_contract_cache'] = global_state.option_contract_cache
