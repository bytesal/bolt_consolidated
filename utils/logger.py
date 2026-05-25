import logging
import logging.handlers
import os
from datetime import datetime

# Global logger instance
_logger = None

def setup_logging(webhook_url: str = None):
    """Configure logging with file rotation and optional Discord webhook."""
    global _logger
    if _logger:
        return _logger

    # Create logs directory if not exists
    if not os.path.exists("logs"):
        os.makedirs("logs")

    # Root logger
    logger = logging.getLogger("bolt")
    logger.setLevel(logging.INFO)

    # Console handler
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console.setFormatter(console_format)
    logger.addHandler(console)

    # Rotating file handler (10 MB per file, 5 backups)
    file_handler = logging.handlers.RotatingFileHandler(
        "logs/bot.log", maxBytes=10*1024*1024, backupCount=5
    )
    file_handler.setLevel(logging.INFO)
    file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)

    # Optional Discord webhook handler (for errors only)
    if webhook_url:
        try:
            from discord import SyncWebhook
            webhook = SyncWebhook.from_url(webhook_url)
            class WebhookHandler(logging.Handler):
                def emit(self, record):
                    if record.levelno >= logging.ERROR:
                        msg = self.format(record)
                        # Truncate to 2000 chars
                        if len(msg) > 1990:
                            msg = msg[:1990] + "..."
                        webhook.send(f"```\n{msg}\n```")
            webhook_handler = WebhookHandler()
            webhook_handler.setLevel(logging.ERROR)
            webhook_handler.setFormatter(file_format)
            logger.addHandler(webhook_handler)
        except Exception:
            pass

    _logger = logger
    return logger

def get_logger(name: str = None):
    """Return a logger instance. If name is None, returns the root bolt logger."""
    if _logger is None:
        # Fallback: basic config (should not happen if setup_logging called first)
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger(name or "bolt")
    if name:
        return _logger.getChild(name)
    return _logger
