# Core logic handler

def run():
    print('[Alden] Booting up logic core...')
    from utils.debug import debug_log
    from utils.config import CONFIG
    from core.state import AppState

    state = AppState()
    debug_log('State initialized')

    while CONFIG['debug_mode']:
        debug_log('Main loop tick')
        # Placeholder logic
        print('🧠 Thinking... (stub logic)')
        break  # prevent infinite loop for now
