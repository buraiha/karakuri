import logging
import re


class OAuthQueryFilter(logging.Filter):
    """OAuthのcode/stateを開発アクセスログへ記録しない。"""
    def filter(self, record):
        message = record.getMessage()
        record.msg = re.sub(r'(/accounts/google/[^?\s"]*)\?[^\s"]*', r'\1?[redacted]', message)
        record.args = ()
        return True
