# Holds short-term state, context, flags

class AppState:
    def __init__(self):
        self.context = {}
        self.flags = {'awake': True, 'planning_ready': False}
