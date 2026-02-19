import os

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

DB_PATH = os.environ.get(
    'PORTFOLIO_DB_PATH',
    os.path.join(_PROJECT_ROOT, 'data', 'portfolio.db')
)

DEFAULT_NUMBERS_FILE = os.environ.get(
    'NUMBERS_FILE_PATH',
    os.path.join(
        os.path.expanduser('~'),
        'Library', 'Mobile Documents',
        'com~apple~Numbers', 'Documents',
        'Investissement.numbers'
    )
)
