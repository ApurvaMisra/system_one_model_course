"""Small, failure-aware metrics; no provider calls."""
import math
from collections import defaultdict
import numpy as np


def route_team(team: str, confidence: float, threshold: float) -> str:
    if not math.isfinite(confidence) or not 0<=confidence<=1: return 'review'
    return team if confidence>=threshold else 'review'


def classification_metrics(expected: dict[str,str], predictions: dict[str,str|None]) -> dict:
    confusion=defaultdict(lambda:defaultdict(int)); correct=failed=0
    for key,label in expected.items():
        predicted=predictions.get(key)
        failed+=predicted is None
        correct+=predicted==label
        confusion[label][predicted if predicted is not None else '<failed>']+=1
    total=len(expected)
    return dict(total=total,correct=correct,failed=failed,accuracy=correct/total if total else None,
                confusion={k:dict(v) for k,v in confusion.items()})


def selective_metrics(correct: list[bool], accepted: list[bool]) -> dict:
    if len(correct)!=len(accepted): raise ValueError('Mismatched lengths')
    n=len(correct); count=sum(accepted)
    return dict(total=n,accepted=count,coverage=count/n if n else None,
                review_rate=1-count/n if n else None,
                accepted_accuracy=sum(c for c,a in zip(correct,accepted) if a)/count if count else None)


def choose_threshold(correct: list[bool], confidence: list[float], target: float=0.9) -> float | None:
    if len(correct)!=len(confidence): raise ValueError('Mismatched lengths')
    for threshold in (0.5,0.6,0.7,0.8,0.9):
        m=selective_metrics(correct,[math.isfinite(c) and c>=threshold for c in confidence])
        if m['accepted_accuracy'] is not None and m['accepted_accuracy']>=target:
            return threshold
    return None


def estimate_cost(usage: dict|None, rates: dict|None) -> float|None:
    if not usage or not rates or rates.get('input') is None or rates.get('output') is None: return None
    inputs=usage.get('input_tokens'); outputs=usage.get('output_tokens')
    if inputs is None or (outputs is None and rates['output']!=0): return None
    outputs=outputs or 0
    if inputs<0 or outputs<0: return None
    # Decisions/System One use flat input-only billing; Responses may charge cache separately.
    if rates.get('flat_input',False): return (inputs*rates['input']+outputs*rates['output'])/1e6
    detail=usage.get('input_tokens_details') or {}
    cached=detail.get('cached_tokens',0) or 0
    written=detail.get('cache_write_tokens',0) or 0
    if cached+written>inputs or min(cached,written)<0: return None
    if (cached and rates.get('cached_input') is None) or (written and rates.get('cache_write') is None): return None
    return ((inputs-cached-written)*rates['input']+cached*(rates.get('cached_input') or 0)+written*(rates.get('cache_write') or 0)+outputs*rates['output'])/1e6


def latency_summary(records: list) -> dict:
    summary={}
    for label,success in [('success',True),('failure',False)]:
        values=[r.elapsed_ms for r in records if r.mode=='live' and not r.warmup
                and r.elapsed_ms is not None and (r.status=='ok')==success]
        summary[label]={'n':len(values),'p50_ms':float(np.percentile(values,50)) if values else None,
                        'p95_ms':float(np.percentile(values,95)) if values else None}
    return summary


def task_report(cases: list[dict], records: list, *, kind: str, rates: dict) -> dict:
    """Report one endpoint/model's trial-0 task quality; failed answers stay counted."""
    if kind not in {'text','image'}: raise ValueError('kind must be text or image')
    category,score,binary=('team','frustration','refund_requested') if kind=='text' else ('category','severity','error_present')
    unique={r.example_id:r for r in records if r.trial==0 and not r.warmup}
    predictions={}; errors=[]; briers=[]; binary_correct=0; binary_valid=0; costs=[]
    input_tokens=[]; output_tokens=[]
    for c in cases:
        r=unique.get(c['id'])
        answers=r.answers if r else {}
        cat=answers.get(category,{})
        predictions[c['id']]=cat.get('choice',cat.get('value'))
        s=answers.get(score,{})
        value=s.get('score',s.get('value'))
        if isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value):
            errors.append(abs(value-c[score]))
        b=answers.get(binary,{})
        probability=b.get('noul',b.get('probability'))
        boolean=b.get('value')
        if isinstance(probability,(int,float)) and math.isfinite(probability) and 0<=probability<=1:
            briers.append((probability-int(c[binary]))**2)
            boolean=probability>=0.5
        if isinstance(boolean,bool):
            binary_valid+=1; binary_correct+=boolean==c[binary]
        key=f'{r.provider}/{r.endpoint}/{r.resolved_model}' if r else ''
        costs.append(estimate_cost(r.usage,rates.get(key)) if r else None)
        input_tokens.append((r.usage or {}).get('input_tokens') if r else None)
        output_tokens.append((r.usage or {}).get('output_tokens') if r else None)
    m=classification_metrics({c['id']:c[category] for c in cases},predictions)
    n=len(cases)
    return dict(n=n,category_accuracy=m['accuracy'],category_failed=m['failed'],confusion=m['confusion'],
                score_mae=sum(errors)/len(errors) if errors else None,score_valid=len(errors),
                binary_accuracy=binary_correct/n if n else None,binary_valid=binary_valid,
                brier=sum(briers)/len(briers) if briers else None,brier_valid=len(briers),
                cost_usd=sum(costs) if costs and all(c is not None for c in costs) else None,
                input_tokens=sum(input_tokens) if input_tokens and all(x is not None for x in input_tokens) else None,
                output_tokens=sum(output_tokens) if output_tokens and all(x is not None for x in output_tokens) else None,
                request_failures=sum(r is None or r.status!='ok' for r in (unique.get(c['id']) for c in cases)))


def binary_threshold_metrics(labels, probabilities, threshold):
    """Precision/recall on valid probabilities, with missing-answer coverage explicit."""
    if len(labels) != len(probabilities):
        raise ValueError('Mismatched lengths')
    if not math.isfinite(threshold) or not 0 <= threshold <= 1:
        raise ValueError('Threshold must be between 0 and 1')
    tp = fp = tn = fn = missing = unscored_positives = 0
    for label, probability in zip(labels, probabilities):
        valid = (isinstance(probability, (int, float)) and not isinstance(probability, bool)
                 and math.isfinite(probability) and 0 <= probability <= 1)
        if not valid:
            missing += 1
            unscored_positives += bool(label)
            continue
        flagged = probability >= threshold
        if label and flagged:
            tp += 1
        elif flagged:
            fp += 1
        elif label:
            fn += 1
        else:
            tn += 1
    total = len(labels)
    return {
        'threshold': threshold, 'tp': tp, 'fp': fp, 'tn': tn, 'fn': fn,
        'precision': tp / (tp + fp) if tp + fp else None,
        'recall': tp / (tp + fn) if tp + fn else None,
        'total': total, 'missing': missing, 'unscored_positives': unscored_positives,
        'coverage': (total - missing) / total if total else None,
    }


def select_binary_threshold(rows, *, prioritize, target):
    """Meet a development-set target, then maximize the other metric.

    Require complete scoring before selecting a policy; never hide failed requests.
    Ties prefer the stronger target metric, then the higher threshold.
    """
    if prioritize not in {'precision', 'recall'} or not 0 <= target <= 1:
        raise ValueError('Choose precision or recall and a target between 0 and 1')
    other = 'recall' if prioritize == 'precision' else 'precision'
    candidates = [row for row in rows if row['missing'] == 0
                  and row[prioritize] is not None and row[other] is not None
                  and row[prioritize] >= target]
    if not candidates:
        return None
    best = max(candidates, key=lambda row: (row[other], row[prioritize], row['threshold']))
    return best['threshold']
