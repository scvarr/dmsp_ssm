"""Публичная поверхность API библиотеки dmsp_ssm.

Поддерживаемые пользовательские точки входа:
- `Reader`
- `ParseOptions`
- `ParseResult`

Остальные модули и сущности, включая `dmsp_ssm._internal.*`,
являются деталями реализации и не входят в публичный контракт.
"""

from dmsp_ssm.parse_options import ParseOptions
from dmsp_ssm.parse_result import ParseResult
from dmsp_ssm.reader import Reader

__all__ = ["Reader", "ParseOptions", "ParseResult"]
__version__ = "1.0.0"
