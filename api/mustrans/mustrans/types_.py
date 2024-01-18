# -*- coding: utf-8 -*-
# File: types_.py

from typing import Dict, List

NoteDicts = List[Dict[str, float]]
"""
```python
[
    {
        "note": <midi_note>,
        "start_time": <start_time>,
        "duration": <duration>,
        "velocity": <velocity>
    },
    {
        ...
    },
    ...
]
```
"""
