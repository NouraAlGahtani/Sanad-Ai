"""Reproducible illustrative benchmark; synthetic examples, not held-out claims."""
import json
import tempfile
from pathlib import Path
from sanad.closed_loop import cycle, metrics

CASES = [
    ([300,390,480], 530),
    ([300,320,340], 360),
    ([480,490,499], 510),
    ([300,420,490], 475),
    ([600,550,450], 410),
    ([100,200,300], 410),
]

def main():
    with tempfile.TemporaryDirectory() as folder:
        db = Path(folder)/'benchmark.db'
        results=[]
        for values, next_value in CASES:
            event={'telemetry':[{'requests_per_min':v,'failed_auth':0} for v in values],
                   'next_observation': {'requests_per_min':next_value,'failed_auth':0}}
            outcome=cycle(event, db)
            results.append({'series':values,'observed_next':next_value,
                            'forecast_next':outcome['forecast']['metrics']['requests_per_min']['predicted_next'],
                            'warning':outcome['forecast']['early_warning'],
                            'correct':outcome['verification']['warning_correct'],
                            'action':outcome['decision']['action']})
        print(json.dumps({'dataset':'six illustrative synthetic sequences', 'results':results, 'metrics':metrics(db)}, indent=2))
if __name__=='__main__': main()
