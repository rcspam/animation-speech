"""Entry point for zipapp and `python -m animation_speech`."""
try:
    from .main import main
except ImportError:
    from animation_speech.main import main
main()
