"""Keep provenance and failure coverage without concealing the notebook API call."""
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Literal
import hashlib
import json
import time
from pydantic import BaseModel, Field

class RunRecord(BaseModel):
    provider: str
    endpoint: Literal['systemone','decisions','responses']
    requested_model: str
    resolved_model: str | None = None
    example_id: str
    config_hash: str
    timestamp: str
    mode: Literal['live','recorded'] = 'live'
    trial: int = 0
    warmup: bool = False
    status: Literal['ok','partial','error','refusal','incomplete','unsupported'] = 'ok'
    answers: dict = Field(default_factory=dict)
    answer_statuses: dict[str,str] = Field(default_factory=dict)
    raw_response: dict | None = None
    elapsed_ms: float | None = None
    usage: dict | None = None
    error: str | None = None


def config_hash(config: dict) -> str:
    return hashlib.sha256(json.dumps(config,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def _reject_credentials(value):
    if isinstance(value,dict):
        for key, child in value.items():
            if str(key).lower() in {'authorization','api_key','openai_api_key','typesafe_api_key','x-api-key'}:
                raise ValueError('Refusing to persist credential-bearing data.')
            _reject_credentials(child)
    elif isinstance(value,list):
        for child in value: _reject_credentials(child)


def save_records(records: list[RunRecord], path: Path) -> None:
    payload=[r.model_dump(mode='json') for r in records]
    _reject_credentials(payload)
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text('\n'.join(json.dumps(x,allow_nan=False) for x in payload)+'\n',encoding='utf-8')
    temporary.replace(path)


def load_records(path: Path, expected_hash: str) -> list[RunRecord]:
    records=[RunRecord.model_validate_json(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
    if not records or any(r.config_hash!=expected_hash for r in records):
        raise ValueError('Recording configuration does not match the requested task.')
    return [r.model_copy(update={'mode':'recorded'}) for r in records]


def normalize_answers(endpoint: str, raw: dict, names: list[str]) -> tuple[dict,dict,str]:
    answers={}; statuses={name:'incomplete' for name in names}
    if endpoint=='responses':
        refused=any(part.get('type')=='refusal' for item in raw.get('output',[]) for part in item.get('content',[]))
        if refused:
            return {},dict.fromkeys(names,'refusal'),'refusal'
        if raw.get('status')!='completed':
            return {},statuses,'incomplete'
        text=''.join(part.get('text','') for item in raw.get('output',[]) for part in item.get('content',[]) if part.get('type')=='output_text')
        try: parsed=json.loads(text)
        except (ValueError,TypeError): return {},statuses,'incomplete'
        if not isinstance(parsed,dict): return {},statuses,'incomplete'
        for name in names:
            if name in parsed:
                answers[name]={'value':parsed[name]}; statuses[name]='ok'
    else:
        incoming=raw.get('answers',{})
        if endpoint=='decisions':
            incoming={a.get('name'):a for a in incoming}
        for name in names:
            a=incoming.get(name)
            if not a: continue
            if a.get('type')=='refusal': statuses[name]='refusal'
            else: answers[name]=a; statuses[name]='ok'
    flags=set(statuses.values())
    status='ok' if flags=={'ok'} else 'partial' if 'ok' in flags else 'refusal' if flags=={'refusal'} else 'incomplete'
    return answers,statuses,status


def run_case(call: Callable, *, provider: str, endpoint: str, model: str,
             example_id: str, config: dict, question_names: list[str], mode: str,
             directory: Path, trial: int=0, warmup: bool=False, response_schema: type[BaseModel] | None=None) -> RunRecord:
    """Time one visible notebook callback, record it, or explicitly replay it.

    The configuration must include all request evidence/settings and image digests.
    Exceptions are recorded by class/status only: raw exception strings can contain secrets.
    """
    if mode not in {'live','recorded'}: raise ValueError('Invalid run mode')
    identity={**config,'provider':provider,'endpoint':endpoint,'model':model,
              'example_id':example_id,'question_names':question_names,'trial':trial,'warmup':warmup}
    digest=config_hash(identity)
    path=directory/f'{digest}.jsonl'
    if mode=='recorded': return load_records(path,digest)[0]
    record=RunRecord(provider=provider,endpoint=endpoint,requested_model=model,example_id=example_id,
                     config_hash=digest,timestamp=datetime.now(timezone.utc).isoformat(),trial=trial,warmup=warmup)
    start=time.perf_counter()
    try:
        result=call()
        record.elapsed_ms=(time.perf_counter()-start)*1000
        raw=result.model_dump(mode='json') if hasattr(result,'model_dump') else result
        record.raw_response=raw
        record.resolved_model=raw.get('model')
        record.usage=raw.get('usage')
        record.answers,record.answer_statuses,record.status=normalize_answers(endpoint,raw,question_names)
        if endpoint=='responses' and record.status=='ok' and response_schema is not None:
            response_schema.model_validate({name:answer['value'] for name,answer in record.answers.items()},strict=True)
    except Exception as exc:
        record.elapsed_ms=(time.perf_counter()-start)*1000
        record.status='error'
        record.answers={}
        record.answer_statuses=dict.fromkeys(question_names,'error')
        http_status=getattr(exc,'status_code',None)
        record.error=f'{type(exc).__name__}' + (f' (HTTP {http_status})' if http_status else '')
    save_records([record],path)
    return record
